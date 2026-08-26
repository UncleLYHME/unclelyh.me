/**
 * Intercom-style chat popup : a launcher bubble bottom-right opens the
 * LYHME assistant. The scripted intro replays on first open, and all
 * interaction is via quick-reply buttons (no free-text input).
 * Transcript lives in the HTML; JS orchestrates the reveal.
 */

const TYPING_MS = 750;
const READ_MS = 600;
const AUTO_OPEN_MS = 1800;

function scrollToId(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    history.replaceState(null, '', `#${id}`);
}

function makeTyping() {
    const el = document.createElement('div');
    el.className = 'msg bot typing';
    el.setAttribute('aria-hidden', 'true');
    el.innerHTML = '<i></i><i></i><i></i>';
    return el;
}

/** Quick replies: the button sends a conversational question, keyed by data-q. */
function buildAnswers({ onCopyEmail }) {
    return {
        today: {
            question: "what's he up to today?",
            run: () => {
                scrollToId('now');
                return 'Family first, building a peptide tracker, and running systems at Creovia. Let me show you more. Scrolling down to the Today section.';
            },
        },
        work: {
            question: 'where has he worked?',
            run: () => {
                scrollToId('experience');
                return 'Systems Administrator at Creovia since 2023, and founder of LYHME, Inc. since 2015, where he hosted 200+ game servers worldwide. Let me show you more. Scrolling down to the Work section.';
            },
        },
        skills: {
            question: 'what are some of his skills?',
            run: () => {
                scrollToId('skills');
                return 'Docker, CI/CD, and Linux on the infra side; Python, Django, and JavaScript for code. He is also a prompt engineer who knows Claude Code and Codex inside out. Let me show you more. Scrolling down to the Skills section.';
            },
        },
        projects: {
            question: 'what has he built?',
            run: () => {
                scrollToId('projects');
                return 'Party Blobs, a couch-and-phone party game for 2–8 players; the Scripture Index, a passage-first reference that organizes reviewed media verse by verse; Creovia Tools, which he has led from design to every module launch; a peptide tracker with 58 users; and this site. Let me show you more. Scrolling down to the Projects section.';
            },
        },
        contact: {
            question: 'how do I contact him?',
            run: () => {
                scrollToId('links');
                onCopyEmail();
                return 'Easiest is email. I just copied it to your clipboard. Scrolling down to the Contact section.';
            },
        },
    };
}

export function initChat({ onCopyEmail }) {
    const pop = document.getElementById('chat-pop');
    const launcher = document.getElementById('chat-launcher');
    const closeBtn = document.getElementById('chat-close');
    const log = document.getElementById('chat-log');
    const quick = document.getElementById('chat-quick');
    if (!pop || !launcher || !log || !quick) return;

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let replayed = reduced; // reduced motion keeps the transcript as-is
    let open = false;

    const scrollLog = () => { log.scrollTop = log.scrollHeight; };

    const replayIntro = () => {
        const msgs = Array.from(log.querySelectorAll('.msg'));
        msgs.forEach((m) => m.classList.add('hidden'));
        let delay = 350;
        msgs.forEach((msg) => {
            const isBot = msg.classList.contains('bot') || msg.classList.contains('sys');
            if (isBot) {
                const typing = makeTyping();
                setTimeout(() => { log.insertBefore(typing, msg); scrollLog(); }, delay);
                delay += TYPING_MS;
                setTimeout(() => { typing.remove(); msg.classList.remove('hidden'); scrollLog(); }, delay);
            } else {
                setTimeout(() => { msg.classList.remove('hidden'); scrollLog(); }, delay);
            }
            delay += READ_MS;
        });
    };

    const setOpen = (next) => {
        open = next;
        pop.classList.toggle('open', open);
        launcher.setAttribute('aria-expanded', String(open));
        if (open) {
            sessionStorage.setItem('chat-opened', '1');
            if (!replayed) { replayed = true; replayIntro(); }
            else scrollLog();
        } else {
            launcher.focus();
        }
    };

    launcher.addEventListener('click', () => setOpen(!open));
    if (closeBtn) closeBtn.addEventListener('click', () => setOpen(false));
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && open) setOpen(false);
    });

    // First visit: pop open once, like a greeter
    if (!sessionStorage.getItem('chat-opened') && !reduced) {
        setTimeout(() => { if (!open) setOpen(true); }, AUTO_OPEN_MS);
    }

    const appendUser = (text) => {
        const el = document.createElement('div');
        el.className = 'msg user';
        const p = document.createElement('p');
        p.textContent = text;
        el.appendChild(p);
        log.appendChild(el);
        scrollLog();
    };

    const appendBot = (html) => {
        const typing = makeTyping();
        log.appendChild(typing);
        scrollLog();
        setTimeout(() => {
            typing.remove();
            const el = document.createElement('div');
            el.className = 'msg bot';
            const p = document.createElement('p');
            p.innerHTML = html;
            el.appendChild(p);
            log.appendChild(el);
            scrollLog();
        }, reduced ? 0 : TYPING_MS);
    };

    const answers = buildAnswers({ onCopyEmail });
    quick.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-q]');
        if (!btn) return;
        const answer = answers[btn.dataset.q];
        if (!answer) return;
        appendUser(answer.question);
        const reply = answer.run();
        if (reply) appendBot(reply);
        // on small screens the popup covers the page : close it so the
        // section the bot scrolled to is actually visible
        if (window.matchMedia('(max-width: 700px)').matches) {
            setTimeout(() => setOpen(false), reduced ? 400 : TYPING_MS + 1400);
        }
    });
}
