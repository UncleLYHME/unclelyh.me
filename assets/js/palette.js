/**
 * Command palette (⌘K / Ctrl+K / "/").
 * Keyboard-driven navigation across the rack.
 */

const SECTIONS = [
    ['about', 'about'],
    ['now', 'today'],
    ['experience', 'work'],
    ['skills', 'skills'],
    ['projects', 'projects'],
    ['links', 'contact'],
];

const SOCIALS = [
    ['GitHub', 'https://github.com/unclelyhme'],
    ['X (Twitter)', 'https://x.com/unclelyhme'],
    ['YouTube', 'https://youtube.com/c/unclelyhme'],
    ['Instagram', 'https://www.instagram.com/unclelyhme'],
    ['Discord', 'https://discord.gg/deb5PtNr7k'],
];

function scrollToId(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    if (id !== 'top') history.replaceState(null, '', `#${id}`);
}

function buildCommands({ onCopyEmail }) {
    const cmds = SECTIONS.map(([id, name]) => ({
        icon: '§',
        label: `Go to ${name}`,
        hint: `#${id}`,
        run: () => scrollToId(id),
    }));
    cmds.push(
        { icon: '✉', label: 'Copy email', hint: 'clip', run: onCopyEmail },
        { icon: '⎙', label: 'Print / save resume', hint: 'pdf', run: () => window.print() },
        { icon: '💬', label: 'Chat with the assistant', hint: 'bot', run: () => document.getElementById('chat-launcher')?.click() },
        { icon: '↥', label: 'Back to top', hint: '', run: () => scrollToId('top') },
        { icon: '⤓', label: 'View source markdown', hint: 'index.md', run: () => window.open('/index.md', '_blank', 'noopener') },
    );
    SOCIALS.forEach(([label, url]) =>
        cmds.push({ icon: '↗', label: `Open ${label}`, hint: 'link', run: () => window.open(url, '_blank', 'noopener') })
    );
    return cmds;
}

export function initPalette({ onCopyEmail }) {
    const overlay = document.getElementById('palette');
    const input = document.getElementById('palette-input');
    const list = document.getElementById('palette-list');
    const openBtn = document.getElementById('palette-open');
    if (!overlay || !input || !list) return;

    const commands = buildCommands({ onCopyEmail });
    let filtered = commands;
    let active = 0;
    let lastFocus = null;

    const render = () => {
        list.innerHTML = '';
        if (!filtered.length) {
            const empty = document.createElement('li');
            empty.className = 'palette-empty';
            empty.textContent = 'command not found';
            list.appendChild(empty);
            return;
        }
        filtered.forEach((cmd, i) => {
            const li = document.createElement('li');
            li.className = 'palette-item';
            li.setAttribute('role', 'option');
            li.setAttribute('aria-selected', i === active ? 'true' : 'false');
            li.innerHTML =
                `<span class="pi-icon">${cmd.icon}</span><span class="pi-label"></span>` +
                (cmd.hint ? `<span class="pi-hint"></span>` : '');
            li.querySelector('.pi-label').textContent = cmd.label;
            if (cmd.hint) li.querySelector('.pi-hint').textContent = cmd.hint;
            li.addEventListener('click', () => run(i));
            li.addEventListener('mousemove', () => { active = i; sync(); });
            list.appendChild(li);
        });
    };

    const sync = () => {
        Array.from(list.children).forEach((li, i) =>
            li.setAttribute && li.setAttribute('aria-selected', i === active ? 'true' : 'false'));
        const el = list.children[active];
        if (el && el.scrollIntoView) el.scrollIntoView({ block: 'nearest' });
    };

    const filter = () => {
        const q = input.value.trim().toLowerCase();
        filtered = q
            ? commands.filter((c) => (c.label + ' ' + (c.hint || '')).toLowerCase().includes(q))
            : commands;
        active = 0;
        render();
    };

    const open = () => {
        lastFocus = document.activeElement;
        overlay.hidden = false;
        input.value = '';
        filter();
        input.focus();
    };
    const close = () => {
        overlay.hidden = true;
        if (lastFocus && lastFocus.focus) lastFocus.focus();
    };
    const run = (i) => {
        const cmd = filtered[i];
        close();
        if (cmd && cmd.run) cmd.run();
    };

    input.addEventListener('input', filter);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(active + 1, filtered.length - 1); sync(); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(active - 1, 0); sync(); }
        else if (e.key === 'Enter') { e.preventDefault(); run(active); }
        else if (e.key === 'Escape') { e.preventDefault(); close(); }
    });
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
    if (openBtn) openBtn.addEventListener('click', open);

    document.addEventListener('keydown', (e) => {
        const isMod = e.metaKey || e.ctrlKey;
        if (isMod && e.key.toLowerCase() === 'k') { e.preventDefault(); overlay.hidden ? open() : close(); }
        else if (e.key === '/' && overlay.hidden && !/^(input|textarea)$/i.test(document.activeElement?.tagName)) {
            e.preventDefault(); open();
        }
    });
}
