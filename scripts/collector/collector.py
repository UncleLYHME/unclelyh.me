#!/usr/bin/env python3
"""GLM usage collector + stats dashboard for spark-1.

Collector: scrapes vLLM prometheus metrics on 127.0.0.1:8888 every 5 minutes,
stores cumulative prompt/generation token counters per snapshot in SQLite.
Dashboard: serves a cached stats page + JSON API on 0.0.0.0:8889. The vLLM API
on :8888 is untouched.

Durability:
  - Lifetime tokens survive vLLM restarts: on counter reset, the pre-restart
    lifetime is loaded from a checkpoint (baseline.json) and carried forward.
  - usage.db is mirrored offsite (Harbor) every scrape via rsync-over-tailscale
    so a dead spark-1 never loses history.

Caching:
  - /api/stats is computed at most every STATS_TTL (300s) and served from an
    in-memory cache between refreshes, so page loads never re-query SQLite and
    data is always up to ~5 minutes delayed by design.

Pricing (per 1M tokens, configurable via /opt/glm53/usage/pricing.json):
  glm    = marginal local cost (default 0)
  claude = Claude Sonnet 4.8 list price: $3 in / $15 out
  codex  = GPT-5.6 (codex) list price: $1.25 in / $10 out
"""
import json
import mimetypes
import sqlite3
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path("/opt/glm53/usage")
DB = BASE / "usage.db"
CHECKPOINT = BASE / "baseline.json"
VLLM_METRICS = "http://127.0.0.1:8888/metrics"
STATS_TTL = 300  # seconds; matches the scrape cadence

# Security headers applied to every response. CSP origins were derived from
# what index.html actually loads (nothing wider than needed):
#   - scripts: Chart.js from https://cdn.jsdelivr.net + the page's own inline
#     <script> block ('unsafe-inline' is required for it)
#   - styles: shared tokens.css/layout.css from https://unclelyh.me + the
#     page's inline <style> block
#   - fonts: 'Archivo' comes via tokens.css on https://unclelyh.me
#   - images: favicon/avatar.png from https://unclelyh.me (widened img-src
#     beyond 'self' data: specifically for that)
#   - fetch/XHR: only /api/stats (same-origin); connect-src keeps
#     https://unclelyh.me allowed in case shared CSS ever adds preconnect/ping
SECURITY_HEADERS = (
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ("X-Frame-Options", "DENY"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
    ("X-Permitted-Cross-Domain-Policies", "none"),
    ("Permissions-Policy",
     "accelerometer=(), autoplay=(), camera=(), geolocation=(), "
     "gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"),
    ("Content-Security-Policy",
     "default-src 'self'; "
     "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
     "style-src 'self' 'unsafe-inline' https://unclelyh.me; "
     "img-src 'self' data: https://unclelyh.me; "
     "connect-src 'self' https://unclelyh.me; "
     "font-src 'self' https://unclelyh.me; "
     "base-uri 'self'; "
     "form-action 'self'; "
     "frame-ancestors 'none'; "
     "object-src 'none'; "
     "upgrade-insecure-requests"),
)

# Themed 404 page for HTML-ish GET routes. Dark #0c0f0d bg with the site's
# phosphor-green #2fdc6e accent, matching the dashboard aesthetic.
NOT_FOUND_HTML = b"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>404 - Uncle LYHME</title>
<style>
  :root { color-scheme: dark; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #0c0f0d;
    color: #e9efe9;
    font-family: ui-monospace, 'SF Mono', 'Cascadia Mono', 'JetBrains Mono', Menlo, Consolas, monospace;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  main { text-align: center; padding: 2rem; }
  .code {
    font-size: clamp(4rem, 16vw, 8rem);
    font-weight: 700;
    letter-spacing: 0.04em;
    color: #2fdc6e;
    text-shadow: 0 0 24px rgba(47, 220, 110, 0.45);
    line-height: 1;
  }
  .msg { margin-top: 1.25rem; font-size: 0.95rem; color: #9fa89f; letter-spacing: 0.02em; }
  .hint { margin-top: 0.5rem; font-size: 0.75rem; color: #656e65; letter-spacing: 0.04em; }
  a.back {
    display: inline-block;
    margin-top: 2rem;
    padding: 0.55rem 1.4rem;
    border: 1px solid #2fdc6e;
    border-radius: 999px;
    color: #2fdc6e;
    text-decoration: none;
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    transition: background 0.2s ease, color 0.2s ease;
  }
  a.back:hover { background: #2fdc6e; color: #0c0f0d; }
</style>
</head>
<body>
<main>
  <div class="code">404</div>
  <p class="msg">That route doesn't exist on this node.</p>
  <p class="hint">request terminated &middot; no such endpoint</p>
  <a class="back" href="/">&larr; back to dashboard</a>
</main>
</body>
</html>"""

ROBOTS_TXT = b"User-agent: *\nDisallow: /\n"  # private dashboard: block all crawlers

BACKUP_HOST = "root@100.76.185.119"  # Harbor over Tailscale
BACKUP_DIR = "/opt/admin-trash/spark-usage-backup"  # Harbor-side holding dir

# GLM-5.3-flash standard (non-discounted) list price; cache read supported too.
GLM_STD = {"input": 0.15, "output": 0.50, "cache_read": 0.03}

# Per-1M-token USD pricing. Fetched live from OpenRouter on each stats refresh;
# these are the fallbacks if the fetch fails.
DEFAULT_PRICING = {
    "glm": dict(GLM_STD),
    "claude": {"input": 3.0, "output": 15.0},  # anthropic/claude-sonnet-4.6 (Sonnet 4.8's price point)
    "codex": {"input": 2.0, "output": 12.0},   # openai/gpt-5.6-terra
}

OPENROUTER_MODELS = {
    "claude": "anthropic/claude-sonnet-4.6",
    "codex": "openai/gpt-5.6-terra",
}
OPENROUTER_LABELS = {
    "glm": "GLM hosted (standard list)",
    "claude": "Claude (OpenRouter)",
    "codex": "GPT 5.6 Terra (OpenRouter)",
}

# Hardware investment the savings pay down (Break Even card).
HARDWARE_COST_USD = 10451.75
OPENROUTER_URL = "https://openrouter.ai/api/v1/models"

# OpenUsage (local agent on Morgan's Mac, tailscale-reachable) - tracks real
# Claude/Codex/Cursor plan usage & spend.
OPENUSAGE_URL = "http://100.85.218.35:6736/v1/usage"

# Electricity benchmark rates ($/kWh) by season/time-of-use tier. Applied to
# measured server power draw. Rates mirror a local utility's EV time-of-use plan.
# Sept = summer (May/Jun/Sep/Oct schedule).
ELECTRIC_RATES = {
    "summer_peak": 0.1885,       # 4-7pm weekdays (May/Jun/Sep/Oct)
    "summer_offpeak": 0.1506,
    "summer_superoffpeak": 0.0395,  # 9pm-5am + weekends/holidays
}
BASELINE_IDLE_WATTS = 20.0  # box idles around this with the GPU resident

def electric_rate(ts=None):
    """Current $/kWh for the given time (Arizona local, EV-style TOU tiers)."""
    from zoneinfo import ZoneInfo
    import datetime as _dt
    t = _dt.datetime.fromtimestamp(ts or time.time(), ZoneInfo("America/Phoenix"))
    weekday = t.weekday() < 5
    hour = t.hour
    if weekday and 16 <= hour < 19:
        return ELECTRIC_RATES["summer_peak"], "peak"
    if (not weekday and 5 <= hour < 16) or (weekday and (5 <= hour < 16 or 19 <= hour < 21)):
        return ELECTRIC_RATES["summer_offpeak"], "off-peak"
    return ELECTRIC_RATES["summer_superoffpeak"], "super off-peak"


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS snapshots (
             ts INTEGER PRIMARY KEY,
             prompt_total INTEGER NOT NULL,
             gen_total INTEGER NOT NULL
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS daily (
             day TEXT PRIMARY KEY,
             prompt_tokens INTEGER NOT NULL,
             gen_tokens INTEGER NOT NULL
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS lifetime (
             id INTEGER PRIMARY KEY CHECK (id = 1),
             prompt_tokens INTEGER NOT NULL,
             gen_tokens INTEGER NOT NULL
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS cloud_daily (
             day TEXT NOT NULL,
             provider TEXT NOT NULL,
             tokens INTEGER NOT NULL DEFAULT 0,
             cost_usd REAL,
             PRIMARY KEY (day, provider)
           )"""
    )
    conn.execute("INSERT OR IGNORE INTO lifetime (id, prompt_tokens, gen_tokens) VALUES (1, 0, 0)")
    return conn


def parse_vllm_counters(text: str):
    prompt = gen = None
    for line in text.splitlines():
        if line.startswith("vllm:prompt_tokens_total{"):
            prompt = int(float(line.rsplit("}", 1)[1].strip()))
        elif line.startswith("vllm:generation_tokens_total{"):
            gen = int(float(line.rsplit("}", 1)[1].strip()))
    return prompt, gen


def load_checkpoint():
    try:
        return json.loads(CHECKPOINT.read_text())
    except Exception:
        return None


def save_checkpoint(data):
    tmp = CHECKPOINT.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(CHECKPOINT)


def sample_host():
    """RAM used/total, CPU %, load, uptime via /proc."""
    try:
        mem = {}
        for line in open("/proc/meminfo"):
            k, v = line.split(":")
            if k in ("MemTotal", "MemAvailable"):
                mem[k] = int(v.strip().split()[0])  # kB
        used_gb = (mem["MemTotal"] - mem["MemAvailable"]) / 1e6
        total_gb = mem["MemTotal"] / 1e6
        with open("/proc/loadavg") as f:
            la = f.read().split()
        load1, load5 = float(la[0]), float(la[1])
        uptime_h = float(open("/proc/uptime").read().split()[0]) / 3600
        def cpu_idle():
            parts = open("/proc/stat").readline().split()[1:]
            idle = int(parts[3]) + int(parts[4])
            total = sum(map(int, parts))
            return idle, total
        i1, t1 = cpu_idle()
        time.sleep(0.25)
        i2, t2 = cpu_idle()
        cpu_pct = round(100 * (1 - (i2 - i1) / max(1, t2 - t1)), 1)
        return {
            "ram_used_gb": round(used_gb, 1), "ram_total_gb": round(total_gb, 1),
            "cpu_pct": cpu_pct, "load1": load1, "load5": load5,
            "uptime_hours": round(uptime_h, 1),
        }
    except Exception as e:
        print(f"host sample failed: {e}", flush=True)
        return None


def sample_gpu():
    """Power draw (W), utilization, temp via nvidia-smi."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=power.draw,utilization.gpu,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip().splitlines()[0]
        w, util, temp = [float(x.strip()) for x in out.split(",")]
        return {"watts": w, "util": util, "temp_c": temp}
    except Exception:
        return None


def scrape_and_store():
    try:
        with urllib.request.urlopen(VLLM_METRICS, timeout=10) as r:
            text = r.read().decode()
    except Exception as e:
        print(f"scrape failed: {e}", flush=True)
        return
    prompt, gen = parse_vllm_counters(text)
    if prompt is None or gen is None:
        print("metrics missing counters", flush=True)
        return
    conn = db()
    now = int(time.time())
    last = conn.execute(
        "SELECT ts, prompt_total, gen_total FROM snapshots ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    restarted = False
    if last is None:
        # First scrape after install (or collector DB reset): seed lifetime with
        # the current counters -- usage already accrued before tracking existed.
        # Daily gets the same seed so 24h/7d/30d windows include it.
        dp, dg = prompt, gen
    else:
        _ts, lp, lg = last
        dp = prompt - lp
        dg = gen - lg
        if dp < 0 or dg < 0:
            # vLLM restarted: counters reset. The pre-restart lifetime is already
            # in the lifetime table. Do NOT add the post-reset snapshot value as
            # new usage (it includes usage already counted pre-restart); just
            # record the reset baseline and let subsequent deltas accrue.
            restarted = True
            dp, dg = 0, 0
    if dp or dg:
        from zoneinfo import ZoneInfo as _ZI
        import datetime as _dtmod
        day = _dtmod.datetime.now(_ZI("America/Phoenix")).strftime("%Y-%m-%d")
        conn.execute(
            """INSERT INTO daily (day, prompt_tokens, gen_tokens) VALUES (?,?,?)
               ON CONFLICT(day) DO UPDATE SET
                 prompt_tokens = prompt_tokens + excluded.prompt_tokens,
                 gen_tokens = gen_tokens + excluded.gen_tokens""",
            (day, dp, dg),
        )
        conn.execute(
            "UPDATE lifetime SET prompt_tokens = prompt_tokens + ?, gen_tokens = gen_tokens + ? WHERE id = 1",
            (dp, dg),
        )
    conn.execute(
        "INSERT OR REPLACE INTO snapshots (ts, prompt_total, gen_total) VALUES (?,?,?)",
        (now, prompt, gen),
    )
    conn.commit()
    lifetime_now = conn.execute("SELECT prompt_tokens, gen_tokens FROM lifetime WHERE id = 1").fetchone()
    conn.close()
    if restarted or not CHECKPOINT.exists():
        save_checkpoint({
            "saved_at": now,
            "lifetime_prompt": lifetime_now[0],
            "lifetime_output": lifetime_now[1],
            "note": "carried across vLLM restarts",
        })
    # hardware + throughput sample
    gpu = sample_gpu()
    host = sample_host()
    if gpu:
        conn = db()
        conn.execute("""CREATE TABLE IF NOT EXISTS hw (
             ts INTEGER PRIMARY KEY, watts REAL, util REAL, temp REAL,
             gen_rate REAL, rate REAL,
             ram_used REAL, cpu_pct REAL, load1 REAL)""")
        for col in ("uptime_h", "ram_used", "cpu_pct", "load1"):
            try:
                conn.execute(f"ALTER TABLE hw ADD COLUMN {col} REAL")
            except Exception:
                pass  # column already exists
        try:
            conn.execute("ALTER TABLE hw ADD COLUMN node TEXT")
            conn.execute("UPDATE hw SET node='spark-1' WHERE node IS NULL")
        except Exception:
            pass
        # tokens/sec since previous snapshot
        rate = 0.0
        if last and not restarted:
            _ts, _lp, _lg = last
            dt = max(1, now - _ts)
            rate = max(0.0, (gen - _lg) / dt)
        conn.execute(
            "INSERT OR REPLACE INTO hw (ts, watts, util, temp, gen_rate, rate, ram_used, cpu_pct, load1, uptime_h, node) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (now, gpu["watts"], gpu["util"], gpu["temp_c"], rate, rate,
             host["ram_used_gb"] if host else None,
             host["cpu_pct"] if host else None,
             host["load1"] if host else None,
             host["uptime_hours"] if host else None,
             "spark-1"),
        )
        conn.commit()
        conn.close()
    print(f"recorded: prompt_total={prompt} gen_total={gen} restarted={restarted}", flush=True)
    record_cloud_usage()
    backup_offsite()


def backup_offsite():
    """Mirror usage.db + baseline.json to Harbor. Best-effort; never blocks scraping."""
    try:
        subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", BACKUP_HOST,
             "mkdir -p", BACKUP_DIR],
            timeout=20, capture_output=True,
        )
        subprocess.run(
            ["rsync", "-az", "--timeout=20", "-e",
             "ssh -o BatchMode=yes -o ConnectTimeout=10",
             str(DB), str(CHECKPOINT), f"{BACKUP_HOST}:{BACKUP_DIR}/"],
            timeout=60, capture_output=True,
        )
    except Exception as e:
        print(f"offsite backup skipped: {e}", flush=True)


def fetch_live_pricing():
    """Pull current per-token prices from OpenRouter. Returns dict or None."""
    try:
        req = urllib.request.Request(OPENROUTER_URL, headers={"User-Agent": "spark-usage/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())["data"]
        by_id = {m["id"]: m.get("pricing", {}) for m in data}
        out = {}
        for key, mid in OPENROUTER_MODELS.items():  # glm uses fixed GLM_STD
            p = by_id.get(mid)
            if p and p.get("prompt") is not None:
                # OpenRouter prices are USD per token -> per 1M
                out[key] = {
                    "input": round(float(p["prompt"]) * 1e6, 4),
                    "output": round(float(p["completion"]) * 1e6, 4),
                    "source": "openrouter",
                    "model_id": mid,
                }
        return out or None
    except Exception as e:
        print(f"openrouter pricing fetch failed: {e}", flush=True)
        return None


def fetch_openusage_raw():
    """Raw provider list from the OpenUsage daemon (None on failure)."""
    try:
        with urllib.request.urlopen(OPENUSAGE_URL, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"openusage fetch failed: {e}", flush=True)
        return None


def _parse_usd(text):
    """'$168.28 · 234.8M tokens' -> 168.28, or None."""
    if not text:
        return None
    try:
        return round(float(text.split("$", 1)[1].split()[0].replace(",", "")), 2)
    except Exception:
        return None


def _parse_tok(text):
    """'$168.28 · 234.8M tokens' -> 234800000, or None."""
    if not text:
        return None
    try:
        tok = text.split("·", 1)[1].strip().split()[0]
        mult = {"K": 1e3, "M": 1e6, "B": 1e9}
        return int(float(tok.replace(",", "")) * mult.get(tok[-1], 1))
    except Exception:
        return None


def record_cloud_usage():
    """Persist OpenUsage daily token history (and daily costs when available)
    into the cloud_daily table. Idempotent: overwrites each day it sees."""
    providers = fetch_openusage_raw()
    if not providers:
        return
    conn = db()
    for p in providers:
        pid = p.get("providerId")
        if pid not in ("claude", "codex"):
            continue
        costs, trend = {}, []
        for l in p.get("lines", []):
            label = l.get("label") or ""
            if l.get("type") == "text" and label in ("Today", "Yesterday"):
                import datetime as _d
                from zoneinfo import ZoneInfo as _Z
                az = _d.datetime.now(_Z("America/Phoenix")).date()
                day = (az - (_d.timedelta(0) if label == "Today" else _d.timedelta(days=1))).isoformat()
                costs[day] = (_parse_usd(l.get("value")), _parse_tok(l.get("value")))
            elif l.get("type") == "barChart" and l.get("points"):
                trend = l["points"]
        for pt in trend:
            label = pt.get("label") or ""
            try:
                import datetime as _d
                from zoneinfo import ZoneInfo as _Z
                day = _d.datetime.strptime(label + " " + str(_d.datetime.now(_Z("America/Phoenix")).year), "%b %d %Y").date()
                # trend labels have no year; a future-dated date means last year (Dec/Jan boundary)
                if day > _d.datetime.now(_Z("America/Phoenix")).date():
                    day = day.replace(year=day.year - 1)
                tokens = int(pt.get("value") or 0)
                cost = costs.get(day.isoformat(), (None, None))[0]
                if tokens or cost is not None:
                    conn.execute(
                        """INSERT INTO cloud_daily (day, provider, tokens, cost_usd) VALUES (?,?,?,?)
                           ON CONFLICT(day, provider) DO UPDATE SET
                             tokens = excluded.tokens,
                             cost_usd = COALESCE(excluded.cost_usd, cost_usd)""",
                        (day.isoformat(), pid, tokens, cost),
                    )
            except Exception:
                continue
    conn.commit()
    conn.close()


def cloud_usage_rollups():
    """Daily/weekly/monthly cloud usage history for claude + codex."""
    conn = db()
    out = {}
    for pid in ("claude", "codex"):
        rows = conn.execute(
            "SELECT day, tokens, cost_usd FROM cloud_daily WHERE provider = ? ORDER BY day", (pid,)
        ).fetchall()
        if not rows:
            continue
        import datetime as _d
        daily = [{"day": day, "tokens": t, "cost_usd": c} for day, t, c in rows]
        def bucket(keyfn, cap=None):
            agg, order = {}, []
            for day, t, c in rows:
                k = keyfn(day)
                if k not in agg:
                    agg[k] = [0, 0.0]
                    order.append(k)
                agg[k][0] += t
                if c is not None:
                    agg[k][1] += c
            items = [{"label": k, "tokens": v[0], "cost_usd": round(v[1], 2)} for k, v in (list(agg.items())[-cap:] if cap else agg.items())]
            return items
        weekly = bucket(lambda day: _d.date.fromisoformat(day).strftime("%G-W%V"), cap=26)
        monthly = bucket(lambda day: day[:7], cap=24)
        out[pid] = {"daily": daily, "weekly": weekly, "monthly": monthly}
    conn.close()
    return out or None


def fetch_openusage():
    """Pull Claude/Codex/Cursor plan usage from the OpenUsage daemon."""
    providers = fetch_openusage_raw()
    if not providers:
        return None
    out = {}
    for p in providers:
        pid = p.get("providerId")
        if pid not in ("claude", "codex"):
            continue
        lines = {}
        for l in p.get("lines", []):
            key = (l.get("label") or "").lower().replace(" ", "_")
            if not key:
                continue
            if l.get("type") == "progress":
                lines[key] = {**l, "value": f"{100 - l.get('used', 0)}% left"}
            elif l.get("type") == "text":
                lines[key] = {"type": "text", "value": l.get("value")}
            elif l.get("value"):
                lines[key] = {"type": "text", "value": l.get("value")}
        out[pid] = {"plan": p.get("plan"), "lines": lines}
    return out


_pricing_cache = {"data": None, "meta": None, "valid_until": 0}


def _next_az_midnight(now_ts):
    import datetime as _d
    from zoneinfo import ZoneInfo as _Z
    az = _d.datetime.now(_Z("America/Phoenix"))
    nxt = (az + _d.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return nxt.timestamp()


def get_pricing():
    """Live OpenRouter pricing overlaid on defaults; manual pricing.json wins.
    Cached until next Arizona midnight (daily refresh); carries provenance meta."""
    now = time.time()
    if _pricing_cache["data"] and now < _pricing_cache["valid_until"]:
        return _pricing_cache["data"], _pricing_cache["meta"]
    meta = {"source": "defaults", "fetched_at": int(now), "models": {}}
    p = BASE / "pricing.json"
    if p.exists():
        try:
            data = json.loads(p.read_text())
            meta = {"source": "pricing.json", "fetched_at": int(now), "models": {}}
            _pricing_cache.update(data=data, meta=meta, valid_until=_next_az_midnight(now))
            return data, meta
        except Exception:
            pass
    pricing = json.loads(json.dumps(DEFAULT_PRICING))  # deep copy
    live = fetch_live_pricing()
    if live:
        for k, v in live.items():
            if k in pricing:
                pricing[k].update(v)
                meta["models"][k] = v.get("model_id", "")
        meta["source"] = "openrouter"
    _pricing_cache.update(data=pricing, meta=meta, valid_until=_next_az_midnight(now))
    return pricing, meta


# ---- 5-minute stats cache -------------------------------------------------
_stats_cache = {"data": None, "computed_at": 0}
_stats_lock = threading.Lock()


def compute_stats():
    conn = db()
    now = int(time.time())
    lifetime = conn.execute(
        "SELECT prompt_tokens, gen_tokens FROM lifetime WHERE id = 1"
    ).fetchone() or (0, 0)
    lp, lg = lifetime

    def window(days):
        cutoff = time.strftime("%Y-%m-%d", time.gmtime(now - days * 86400))
        row = conn.execute(
            "SELECT COALESCE(SUM(prompt_tokens),0), COALESCE(SUM(gen_tokens),0) FROM daily WHERE day >= ?",
            (cutoff,),
        ).fetchone()
        return {"prompt": row[0], "output": row[1], "total": row[0] + row[1]}

    ytd_cutoff = f"{time.gmtime(now).tm_year}-01-01"
    ytd = conn.execute(
        "SELECT COALESCE(SUM(prompt_tokens),0), COALESCE(SUM(gen_tokens),0) FROM daily WHERE day >= ?",
        (ytd_cutoff,),
    ).fetchone()

    series = conn.execute(
        "SELECT day, prompt_tokens, gen_tokens FROM daily WHERE day >= ? ORDER BY day",
        (time.strftime("%Y-%m-%d", time.gmtime(now - 90 * 86400)),),
    ).fetchall()

    import datetime as dt
    from zoneinfo import ZoneInfo
    az = ZoneInfo("America/Phoenix")
    now_az = dt.datetime.now(az)

    def _az_window(days, offset=0):
        """AZ-local calendar windows, 12:01am boundaries.
        24h = today; 7d = this calendar week (starts Sunday); 30d = last 30 days.
        offset=1 -> the matching prior window."""
        today = now_az.date()
        if days == 1:
            start = today - dt.timedelta(days=offset)
            end = start
        elif days == 7:
            anchor = today - dt.timedelta(days=7 * offset)
            start = anchor - dt.timedelta(days=(anchor.weekday() + 1) % 7)  # back to Sunday
            end = start + dt.timedelta(days=6) if offset else today
        else:
            end = today - dt.timedelta(days=days * offset)
            start = end - dt.timedelta(days=days - 1)
            if offset == 0:
                end = today
        row = conn.execute(
            "SELECT COALESCE(SUM(prompt_tokens),0), COALESCE(SUM(gen_tokens),0) FROM daily WHERE day >= ? AND day <= ?",
            (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"),),
        ).fetchone()
        return {"prompt": row[0], "output": row[1], "total": row[0] + row[1]}

    w24, w7, w30 = _az_window(1), _az_window(7), _az_window(30)
    p24, p7, p30 = _az_window(1, 1), _az_window(7, 1), _az_window(30, 1)
    conn.close()

    def with_prev(cur, prev):
        delta = cur["total"] - prev["total"]
        pct = round(100 * delta / prev["total"], 1) if prev["total"] else None
        return {**cur, "prev": prev["total"], "delta": delta, "delta_pct": pct}

    windows = {
        "24h": with_prev(w24, p24),
        "7d": with_prev(w7, p7),
        "30d": with_prev(w30, p30),
        "ytd": {"prompt": ytd[0], "output": ytd[1], "total": ytd[0] + ytd[1]},
        "lifetime": {"prompt": lp, "output": lg, "total": lp + lg},
    }

    pricing, pricing_meta = get_pricing()
    glm_cost = (lp / 1e6) * pricing["glm"]["input"] + (lg / 1e6) * pricing["glm"]["output"]
    savings = {"glm": {"equivalent_cost_usd": round(glm_cost, 2), "label": OPENROUTER_LABELS["glm"]}}
    for provider in ("claude", "codex"):
        p_in, p_out = pricing[provider]["input"], pricing[provider]["output"]
        cost = (lp / 1e6) * p_in + (lg / 1e6) * p_out
        savings[provider] = {
            "equivalent_cost_usd": round(cost, 2),
            "local_cost_usd": round(glm_cost, 2),
            "saved_usd": round(cost - glm_cost, 2),
            "label": OPENROUTER_LABELS[provider],
        }

    # Break-even: hardware investment paid down by what the same usage would
    # have cost at GLM list prices (the running cost we avoid by owning it).
    total_saved = round(glm_cost, 2)
    remaining = round(max(HARDWARE_COST_USD - total_saved, 0.0), 2)
    savings["breakeven"] = {
        "hardware_cost_usd": HARDWARE_COST_USD,
        "saved_toward_usd": total_saved,
        "remaining_usd": remaining,
        "pct_complete": round(100 * min(total_saved / HARDWARE_COST_USD, 1.0), 1),
        "label": "Break Even",
    }

    cumulative, running = [], 0
    for d, p, g in series:
        running += p + g
        cumulative.append({"day": d, "tokens": p + g, "cumulative": running})

    # ---- latency (vLLM histograms) ----
    latency = {"avg_ttft_s": None, "avg_e2e_s": None}
    try:
        with urllib.request.urlopen(VLLM_METRICS, timeout=10) as r:
            mtext = r.read().decode()
        vals = {}
        for line in mtext.splitlines():
            for key in ("vllm:time_to_first_token_seconds_sum", "vllm:time_to_first_token_seconds_count",
                        "vllm:e2e_request_latency_seconds_sum", "vllm:e2e_request_latency_seconds_count"):
                if line.startswith(key + "{"):
                    vals[key] = float(line.rsplit("}", 1)[1].strip())
        if vals.get("vllm:time_to_first_token_seconds_count"):
            latency["avg_ttft_s"] = round(vals["vllm:time_to_first_token_seconds_sum"] / vals["vllm:time_to_first_token_seconds_count"], 2)
        if vals.get("vllm:e2e_request_latency_seconds_count"):
            latency["avg_e2e_s"] = round(vals["vllm:e2e_request_latency_seconds_sum"] / vals["vllm:e2e_request_latency_seconds_count"], 2)
    except Exception as e:
        print(f"latency parse failed: {e}", flush=True)

    # ---- hardware / power / throughput ----
    host = sample_host() or {}
    hw_stats = {}
    try:
        c = db()
        c.execute("CREATE TABLE IF NOT EXISTS hw (ts INTEGER PRIMARY KEY, watts REAL, util REAL, temp REAL, gen_rate REAL, rate REAL)")
        cutoff = now - 24 * 3600
        agg = c.execute(
            """SELECT AVG(watts), MAX(watts), AVG(temp), AVG(gen_rate) FROM hw
               WHERE ts >= ? AND node = 'spark-1'""",
            (cutoff,),
        ).fetchone()
        agg2 = c.execute(
            """SELECT AVG(watts), MAX(watts) FROM hw
               WHERE ts >= ? AND node = 'spark-2'""",
            (cutoff,),
        ).fetchone()
        latest = c.execute(
            "SELECT ts, watts, util, temp, gen_rate, ram_used, cpu_pct, load1 FROM hw WHERE node='spark-1' ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        latest2 = c.execute(
            "SELECT ts, watts, util, temp, ram_used, cpu_pct, load1, uptime_h FROM hw WHERE node='spark-2' ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        all_agg = c.execute("SELECT AVG(watts), MIN(ts), MAX(ts) FROM hw").fetchone()
        hw_series = c.execute(
            "SELECT ts, watts, util, gen_rate, cpu_pct, ram_used FROM hw WHERE ts >= ? AND node='spark-1' ORDER BY ts",
            (now - 48 * 3600,),
        ).fetchall()
        hw_series2 = c.execute(
            "SELECT ts, watts, util, ram_used, cpu_pct FROM hw WHERE ts >= ? AND node='spark-2' ORDER BY ts",
            (now - 48 * 3600,),
        ).fetchall()
        c.close()
        avg_w, max_w, avg_temp, avg_rate = agg
        rate, tier = electric_rate(now)
        cur_w = latest[1] if latest else BASELINE_IDLE_WATTS
        kwh_24h = (avg_w or cur_w) * 24 / 1000
        aw, t0, t1 = all_agg
        kwh_total = (aw * max(1, (t1 - t0)) / 3600 / 1000) if (aw and t0 and t1) else kwh_24h
        hw_stats = {
            "power": {
                "current_watts": round(cur_w, 1),
                "avg_watts_24h": round(avg_w or 0, 1),
                "peak_watts_24h": round(max_w or 0, 1),
                "util_pct": round(latest[2]) if latest else None,
                "temp_c": round(latest[3]) if latest else None,
            },
            "throughput": {
                "tokens_per_sec": round(latest[4], 1) if latest else None,
                "avg_tokens_per_sec_24h": round(avg_rate or 0, 1),
            },
            "efficiency": {
                "tokens_per_watt_24h": round((avg_rate or 0) / max(avg_w or 1, 1), 1),
                "output_tokens_per_kwh_lifetime": round(lg / kwh_total, 0) if kwh_total > 0 else None,
            },
            "energy": {
                "kwh_24h": round(kwh_24h, 3),
                "kwh_total": round(kwh_total, 3),
                "rate_now": rate,
                "tier_now": tier,
                "cost_24h_usd": round(kwh_24h * rate, 4),
                "cost_total_usd": round(kwh_total * rate, 2),
            },
            "latency": latency,
            "nodes": {
                "spark-1": {
                    "watts": round(latest[1], 1) if latest else None,
                    "util_pct": round(latest[2]) if latest else None,
                    "temp_c": round(latest[3]) if latest else None,
                    "ram_used_gb": round(latest[5], 1) if latest and latest[5] is not None else None,
                    "cpu_pct": round(latest[6], 1) if latest and latest[6] is not None else None,
                },
                "spark-2": {
                    "watts": round(latest2[1], 1) if latest2 else None,
                    "util_pct": round(latest2[2]) if latest2 else None,
                    "temp_c": round(latest2[3]) if latest2 else None,
                    "ram_used_gb": round(latest2[4], 1) if latest2 and latest2[4] is not None else None,
                    "cpu_pct": round(latest2[5], 1) if latest2 and latest2[5] is not None else None,
                },
                "combined": {
                    "watts": round((latest[1] or 0) + (latest2[1] or 0), 1) if latest else None,
                    "total_ram_used_gb": round(
                        (latest[5] or 0) + (latest2[4] or 0), 1
                    ) if latest else None,
                    "total_ram_gb": 253.0,
                },
            },
            "spark2": {
                "host": {
                    "ram_used_gb": round(latest2[4], 1) if latest2 and latest2[4] is not None else None,
                    "cpu_pct": round(latest2[5], 1) if latest2 and latest2[5] is not None else None,
                    "load1": round(latest2[6], 2) if latest2 and latest2[6] is not None else None,
                    "uptime_hours": round(latest2[7], 1) if latest2 and latest2[7] is not None else None,
                    "ram_total_gb": 126.0,
                },
                "power": {**{
                    "current_watts": round(latest2[1], 1) if latest2 else None,
                    "util_pct": round(latest2[2]) if latest2 else None,
                    "temp_c": round(latest2[3]) if latest2 else None,
                }, "avg_watts_24h": round(agg2[0], 1) if agg2 and agg2[0] is not None else None,
                   "peak_watts_24h": round(agg2[1], 1) if agg2 and agg2[1] is not None else None},
                "last_seen_age_s": (now - latest2[0]) if latest2 else None,
            },
            "host": {
                "ram_used_gb": round(latest[5], 1) if latest and len(latest) > 5 and latest[5] is not None else None,
                "ram_total_gb": host["ram_total_gb"] if host else None,
                "cpu_pct": round(latest[6], 1) if latest and len(latest) > 6 and latest[6] is not None else None,
                "load1": round(latest[7], 2) if latest and len(latest) > 7 and latest[7] is not None else None,
                "uptime_hours": host["uptime_hours"] if host else None,
            },
            "series": [
                {"ts": t, "watts": w, "util": u, "tok_s": r, "cpu": c_, "ram": m}
                for t, w, u, r, c_, m in hw_series
            ],
            "series2": [
                {"ts": t, "watts": w, "util": u, "ram": m, "cpu": c_}
                for t, w, u, m, c_ in hw_series2
            ],
        }
    except Exception as e:
        print(f"hw stats failed: {e}", flush=True)

    return {
        "openusage": fetch_openusage(),
        "cloud_usage": cloud_usage_rollups(),
        "pricing_meta": {
            **pricing_meta,
            "labels": OPENROUTER_LABELS,
            "rates": {k: {"input": v.get("input"), "output": v.get("output")} for k, v in pricing.items()},
        },
        "updated_at": now,
        "cache_ttl": STATS_TTL,
        "model": "GLM-5.3-Flash-EXL3",
        "comparison_model": "Claude Sonnet 4.8",
        "windows": windows,
        "savings": savings,
        "pricing": pricing,
        "daily_cumulative": cumulative,
        "hardware": hw_stats,
    }


def stats():
    """Return cached stats, recomputing at most once per STATS_TTL."""
    with _stats_lock:
        now = time.time()
        if _stats_cache["data"] is None or now - _stats_cache["computed_at"] >= STATS_TTL:
            _stats_cache["data"] = compute_stats()
            _stats_cache["computed_at"] = now
        return _stats_cache["data"]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype, cacheable=False):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for name, value in SECURITY_HEADERS:
            self.send_header(name, value)
        if cacheable:
            self.send_header("Cache-Control", f"max-age={STATS_TTL}")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path == "/api/ingest":
            length = int(self.headers.get("Content-Length", 0))
            try:
                data = json.loads(self.rfile.read(length))
                node = data.get("node", "")
                assert node in ("spark-1", "spark-2")
                ts = int(data.get("ts") or time.time())
                gpu, host = data.get("gpu") or {}, data.get("host") or {}
                conn = db()
                conn.execute(
                    "INSERT OR REPLACE INTO hw (ts, watts, util, temp, gen_rate, rate, ram_used, cpu_pct, load1, uptime_h, node) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (ts, gpu.get("watts"), gpu.get("util"), gpu.get("temp_c"), 0, 0,
                     host.get("ram_used_gb"), host.get("cpu_pct"), host.get("load1"),
                     host.get("uptime_hours"), node),
                )
                conn.commit()
                conn.close()
                self._send(200, b'{"ok": true}', "application/json")
            except Exception as e:
                self._send(400, json.dumps({"error": str(e)}).encode(), "application/json")
        else:
            self._send(404, b"not found", "text/plain")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            html = (BASE / "index.html").read_bytes()
            self._send(200, html, "text/html; charset=utf-8", cacheable=True)
        elif self.path == "/favicon.ico":
            ico = BASE / "assets" / "img" / "favicon.ico"
            if ico.is_file():
                self._send(200, ico.read_bytes(), "image/x-icon", cacheable=True)
            else:
                self._send(404, NOT_FOUND_HTML, "text/html; charset=utf-8")
        elif self.path.split("?", 1)[0] == "/api/stats":
            body = json.dumps(stats()).encode()
            self._send(200, body, "application/json", cacheable=True)
        elif self.path == "/health":
            self._send(200, b"ok", "text/plain")
        elif self.path == "/robots.txt":
            self._send(200, ROBOTS_TXT, "text/plain", cacheable=True)
        elif self.path.startswith("/assets/"):
            # Nested static assets (assets/img/...) served under BASE/assets.
            f = (BASE / self.path.lstrip("/")).resolve()
            base = (BASE / "assets").resolve()
            if f.is_file() and base in f.parents:
                ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
                self._send(200, f.read_bytes(), ctype, cacheable=True)
            else:
                self._send(404, NOT_FOUND_HTML, "text/html; charset=utf-8")
        else:
            self._send(404, NOT_FOUND_HTML, "text/html; charset=utf-8")


if __name__ == "__main__":
    import sys as _sys
    BASE.mkdir(parents=True, exist_ok=True)
    if "--scrape-only" in _sys.argv:
        scrape_and_store()
    else:
        scrape_and_store()
        srv = ThreadingHTTPServer(("0.0.0.0", 8889), Handler)
        print("dashboard on :8889", flush=True)
        srv.serve_forever()
