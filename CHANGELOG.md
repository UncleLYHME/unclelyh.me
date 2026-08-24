---
summary: Timeline of notable changes in my-website.
---

# Changelog

## 2026-08-24 — Feature Party Blobs
- Added Party Blobs as the lead project card with a live link and a restrained featured treatment that fits the datacenter theme.
- Updated the project count, assistant reply, print resume, markdown mirror, and both LLM metadata files with the couch-and-phone party game.
- Bumped CSS and JavaScript cache versions to `v=42`.

## 2026-08-18 — Datacenter Redesign: Chat Greeter + Rack Units
- Updated the deployment Compose to build directly from the repository Dockerfile on Coolify's managed network, while keeping the host bind configurable and loopback-safe by default.
- Replaced the terminal aesthetic with a committed single dark "datacenter" theme: phosphor-green accent with amber activity LEDs, Archivo variable display type (self-hosted, `assets/fonts/`), ambient glow + grain backdrop.
- Hero now leads with the big two-row name, real name reveal (Morgan Nuttall), first-person about, "open to new projects" status, and social links; employer un-redacted to Creovia across the site and markdown mirrors.
- Sections are rack units (u-01…u-05: today/work/skills/projects/contact), each fed by its own colored SVG patch cable from a `core-sw01` switch panel whose plugged ports blink in the cable's color (unplugged ports stay dark). Cables energize with scroll and each U flips its PWR LED when its line lands (`assets/js/cable.js`); reduced motion renders everything lit.
- The intro conversation moved into an Intercom-style chat popup bottom-right (`assets/js/chat.js`): auto-opens once per session, replays the scripted transcript with typing indicators, and answers only via conversational quick-reply buttons (no free-text input).
- Mobile/tablet pass: no horizontal overflow, stacked work entries and skills, narrower cable gutter, wordmark-only slim header on small screens. Site copy contains no em dashes.
- Content pass for hiring managers and clients: every work entry leads with a one-line role summary, bullets rewritten around ownership and outcomes, real scale published (LYHME peaked at 200+ game servers across 9+ locations; Peptide Tracker is a Flask app serving 58 users), a contact note stating openness to projects, contract work, and roles. Creovia entry stays qualitative by choice. Chat replies and `index.md` carry the same facts.
- Resume generator rebuilt for ATS: printing now renders a dedicated hidden resume document (`#resume-doc`) instead of restyling the themed page. Classic single-column layout modeled on ambrosino.io: date gutter, ruled uppercase sections, muted per-role stack lines, labeled Contact/Online footer, literal email text (decoded at load), and a "Morgan Nuttall - Resume" PDF filename via a print-time title swap.
- Creovia Tools added as a flagship project (owned from design through every module launch and monthly release updates), with a matching work bullet, chat answer, and markdown mirror entry; odd project-card counts now span the last row instead of leaving a dead cell.
- Prompt engineering added to the public identity: hero tagline and about, a fourth "ai" skills bus (prompt engineering, Claude Code, Codex, agent orchestration, MCP, agent-ready web), chat skills reply, meta description, and the markdown/llms mirrors. Bullet-point hover glow (marker lights up like a server LED in the unit's cable color) and three new skill tooltips (CI/CD, Tailscale, observability).
- Removed: light theme + toggle (`theme.js`), OS-adaptive window chrome, scroll reveal, WebGL rain experiment, footer/header ⌘K affordances (palette still opens via ⌘K or `/`). WebMCP selectors updated for the new DOM; `llms.txt` mirrors and `index.md` synced ("Now" → "Today"). Cache versions bumped to `v=34`.

## 2026-08-13 — Quiet Terminal: Simplify + Platform Chrome
- Decluttered the homepage: one typed `whoami` prompt in the hero (the per-section fake prompts are gone), minimal `❯ section` headings, and a staggered load/scroll reveal as the single big animation moment.
- Removed the violet accent for a terminal-green signature (dark and light retuned); links stay sky, neutrals stay zinc.
- Window chrome now adapts to the visitor's OS: macOS traffic lights, Windows caption buttons (`pwsh` title, Ctrl K), GNOME-style round controls (`bash`), and iOS/Android app bars with a home indicator. Detection runs pre-paint via `data-os`; macOS is the no-JS default.
- Cut noise: tooltips trimmed from ~30 to 4 genuinely obscure terms, 23 skill chips replaced by 3 aligned `infra/code/ops` rows, entry cards flattened to a hover-accent timeline, tmux status line and boot hint removed (⌘K moved into the titlebar, hint into the footer).
- Recruiter-friendly wayfinding: an always-visible `./about ./work ./skills ./projects ./contact` nav row under the hero, plus a `resume ↓` action (and palette command) that opens the print dialog — print styles render a clean one-pager for Save-as-PDF. Anchor scroll offset now clears the sticky titlebar.
- New `assets/js/reveal.js` and `assets/js/os.js`; palette command hints updated. Cache versions bumped to `v=25`. Markdown mirror skills synced to the grouped rows.

## 2026-07-21 — Terminal / Systems Redesign
- Rebuilt the homepage into a committed terminal aesthetic: window chrome, prompt-driven sections (`whoami`, `cat about.txt`, `now`, `history --work`, `ls skills/`, `ls ~/projects`, `cat contacts.txt`), boot line, and blinking cursor.
- Added a ⌘K / Ctrl+K / `/` command palette for keyboard-driven section jumps and actions (copy email, toggle theme, open socials, view markdown), plus a tmux-style status line with live clock and current-section indicator.
- New phosphor palette (amber accent, cyan links, green prompts) off the old GitHub-green; added CRT scanline/vignette depth. Light and dark themes both retuned.
- Split `style.css` into `tokens.css`, `layout.css`, and `components.css` (each under 500 LOC); `style.css` kept as an `@import` shim. Extracted `tooltips.js` and `webmcp.js`; slimmed `main.js`; added `palette.js`.
- Added the `unclelyh.me` (this site) project entry to the homepage and markdown mirror. Bumped asset cache versions to `v=22`.

## 2026-06-27 — Public Repo and Dockhand Layout
- Renamed the public project/repository to `unclelyh.me` and updated README layout.
- Published the site from a clean public Git history under the Uncle LYHME identity.
- Moved browser JavaScript under `assets/js/` and CSS under `assets/css/`.
- Removed retired static API pages and JSON API metadata.
- Added Dockhand deploy files with nginx runtime config under `nginx/`.

## 2026-04-19 — Agent Discovery Surface
- Added homepage agent discovery headers, markdown negotiation, and content-signal preferences.
- Published read-only API discovery files, OpenAPI docs, and an API catalog for automated clients.
- Added agent-skills discovery metadata and browser-side WebMCP tools for supported agents.
