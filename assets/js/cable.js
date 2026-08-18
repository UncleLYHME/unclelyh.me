/**
 * The cable runs : every node gets its own line from the switch,
 * dropping down a parallel riser lane and curving into the node's port.
 * Lines energise as you scroll; a node powers on when its line lands.
 * Reduced motion: everything fully lit.
 */

const LINE_COLORS = ['#2fdc6e', '#ffb224', '#38d6d0', '#b78aff', '#e9efe9'];
const BEND = 26;

const SVG_NS = 'http://www.w3.org/2000/svg';

function makePath(cls) {
    const p = document.createElementNS(SVG_NS, 'path');
    p.setAttribute('class', cls);
    return p;
}

export function initCable() {
    const run = document.getElementById('run');
    const svg = document.getElementById('cable');
    if (!run || !svg) return;
    const nodes = Array.from(run.querySelectorAll('.node'));
    if (!nodes.length) return;

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let cables = [];

    const portCenter = (node, rect) => {
        const p = node.querySelector('.port').getBoundingClientRect();
        return { x: p.left + p.width / 2 - rect.left, y: p.top + p.height / 2 - rect.top };
    };

    function build() {
        const rect = run.getBoundingClientRect();
        svg.setAttribute('viewBox', `0 0 ${Math.max(1, rect.width)} ${Math.max(1, rect.height)}`);
        svg.textContent = '';

        // Lines plug into the bottom of the switch (overflow: visible lets
        // the SVG draw above the run container).
        const sw = document.querySelector('.switch');
        const swRect = sw ? sw.getBoundingClientRect() : null;
        const startY = swRect ? swRect.bottom - rect.top - 2 : 0;
        const swLeft = swRect ? swRect.left - rect.left : 0;
        const swPorts = sw ? Array.from(sw.querySelectorAll('.switch-ports i')) : [];

        const lanes = nodes.length;
        cables = nodes.map((node, i) => {
            const port = portCenter(node, rect);
            const color = LINE_COLORS[i % LINE_COLORS.length];
            node.style.setProperty('--line', color);

            // light up the physical switch port this line is plugged into
            const jack = swPorts[i];
            let jackX = swLeft + 22 + i * 19;
            if (jack) {
                const jr = jack.getBoundingClientRect();
                jackX = jr.left + jr.width / 2 - rect.left;
                jack.classList.add('live');
                jack.style.setProperty('--port', color);
                jack.style.animationDelay = `${(i * 0.37).toFixed(2)}s`;
            }

            // outer lanes belong to deeper nodes, so lines never cross
            const laneGap = Math.min(9, Math.max(5, (port.x - 8) / lanes));
            const laneX = Math.max(3, port.x - 8 - (lanes - 1 - i) * laneGap);
            const dropY = startY + 34;
            const bendY = Math.max(dropY, port.y - BEND);
            const d = `M ${jackX} ${startY}` +
                ` C ${jackX} ${startY + 22}, ${laneX} ${startY + 12}, ${laneX} ${dropY}` +
                ` L ${laneX} ${bendY}` +
                ` Q ${laneX} ${port.y}, ${Math.min(laneX + BEND, port.x)} ${port.y}` +
                ` L ${port.x} ${port.y}`;

            const base = makePath('base');
            const live = makePath('live');
            const pulse = makePath('pulse');
            [base, live, pulse].forEach((p) => { p.setAttribute('d', d); svg.appendChild(p); });

            live.style.stroke = color;
            live.style.filter = `drop-shadow(0 0 6px ${color})`;
            pulse.style.filter = `drop-shadow(0 0 4px ${color})`;

            const total = live.getTotalLength();
            live.style.strokeDasharray = `${total}`;
            live.style.strokeDashoffset = `${total}`;

            return { node, live, pulse, total, portY: port.y, startY, rectH: rect.height };
        });
        update();
    }

    function update() {
        const rect = run.getBoundingClientRect();
        const reachY = reduced ? Infinity : window.innerHeight * 0.82 - rect.top;

        cables.forEach((c) => {
            // approximate: map the reach line's y-progress onto path length
            const progress = Math.max(0, Math.min(1,
                (reachY - c.startY) / Math.max(1, c.portY - c.startY)));
            const len = progress * c.total;
            c.live.style.strokeDashoffset = `${c.total - len}`;

            const cut = Math.max(0, 100 - (Math.min(reachY, c.portY) / Math.max(1, rect.height)) * 100);
            c.pulse.style.clipPath = `inset(-20% 0 ${cut}% 0)`;

            if (len >= c.total - 0.5) c.node.classList.add('powered');
        });
    }

    let ticking = false;
    const onScroll = () => {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(() => { ticking = false; update(); });
    };

    build();
    if (reduced) {
        nodes.forEach((n) => n.classList.add('powered'));
        return;
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    if ('ResizeObserver' in window) {
        let t = null;
        new ResizeObserver(() => { clearTimeout(t); t = setTimeout(build, 120); }).observe(run);
    } else {
        window.addEventListener('resize', () => build(), { passive: true });
    }
}
