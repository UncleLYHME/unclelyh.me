/**
 * Main entry point: wires up modules on DOM ready.
 */

import { setCurrentYear } from './utils.js';
import { initTooltips } from './tooltips.js';
import { initWebMcp } from './webmcp.js';
import { initPalette } from './palette.js';
import { initChat } from './chat.js';
import { initCable } from './cable.js';

let toastTimer = null;
function showToast(message, duration = 2000) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('visible'), duration);
}

/** Decode obfuscated email links (spam-resistant for humans; agents use llms.txt). */
function initObfuscatedEmailLinks() {
    let decoded = '';
    document.querySelectorAll('.js-ob-email[data-email-b64]').forEach((link) => {
        const encoded = link.dataset.emailB64 || '';
        if (!encoded) return;
        try {
            const email = atob(encoded);
            link.dataset.email = email;
            link.href = `mailto:${email}`;
            decoded = email;
        } catch {
            link.href = '#';
        }
    });
    // the print resume needs the address as literal text for ATS parsers
    if (decoded) {
        document.querySelectorAll('#resume-email, .resume-email-slot')
            .forEach((el) => { el.textContent = decoded; });
    }
}

async function copyEmail() {
    const link = document.querySelector('.js-ob-email');
    let email = link?.dataset.email || '';
    if (!email && link?.dataset.emailB64) {
        try { email = atob(link.dataset.emailB64); } catch { email = ''; }
    }
    if (!email) return;
    try {
        await navigator.clipboard.writeText(email);
        showToast('email copied to clipboard');
    } catch {
        window.location.href = `mailto:${email}`;
    }
}

function initCopyEmail() {
    document.querySelectorAll('.copy-email').forEach((link) =>
        link.addEventListener('click', (e) => { e.preventDefault(); copyEmail(); }));
}

/** "resume ↓" opens the print dialog; print styles render the ATS resume
 *  (#resume-doc). The title swap gives the saved PDF a sensible filename. */
function initPrintResume() {
    const link = document.getElementById('print-resume');
    if (link) link.addEventListener('click', (e) => { e.preventDefault(); window.print(); });

    const siteTitle = document.title;
    window.addEventListener('beforeprint', () => { document.title = 'Morgan Nuttall - Resume'; });
    window.addEventListener('afterprint', () => { document.title = siteTitle; });
}

document.addEventListener('DOMContentLoaded', () => {
    setCurrentYear('year');

    initObfuscatedEmailLinks();
    initCopyEmail();
    initPrintResume();
    initTooltips();
    initWebMcp();

    initChat({ onCopyEmail: copyEmail });
    initCable();
    initPalette({ onCopyEmail: copyEmail });
});
