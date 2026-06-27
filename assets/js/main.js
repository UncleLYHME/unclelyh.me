/**
 * Main entry point
 * Initializes all modules
 */

import { initTheme, toggleTheme } from './theme.js';
import { setCurrentYear } from './utils.js';

/**
 * Show toast notification
 */
function showToast(message, duration = 2000) {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.textContent = message;
    toast.classList.add('visible');

    setTimeout(() => {
        toast.classList.remove('visible');
    }, duration);
}

/**
 * Initialize copy email functionality
 */
function initCopyEmail() {
    const emailLinks = document.querySelectorAll('.copy-email');

    emailLinks.forEach(link => {
        link.addEventListener('click', async (e) => {
            e.preventDefault();
            const encoded = link.dataset.emailB64 || '';
            let email = link.dataset.email || '';
            if (!email && encoded) {
                try {
                    email = atob(encoded);
                    link.dataset.email = email;
                } catch {
                    email = '';
                }
            }
            if (!email) return;

            try {
                await navigator.clipboard.writeText(email);
                showToast('email copied to clipboard');
            } catch (err) {
                // Fallback: open mailto
                window.location.href = `mailto:${email}`;
            }
        });
    });
}

/**
 * Decode and hydrate obfuscated email links at runtime.
 */
function initObfuscatedEmailLinks() {
    const emailLinks = document.querySelectorAll('.js-ob-email[data-email-b64]');
    emailLinks.forEach((link) => {
        const encoded = link.dataset.emailB64 || '';
        if (!encoded) return;
        try {
            const email = atob(encoded);
            link.dataset.email = email;
            link.href = `mailto:${email}`;
        } catch {
            link.href = '#';
        }
    });
}

/**
 * Initialize back to top button
 */
function initBackToTop() {
    const btn = document.getElementById('back-to-top');
    if (!btn) return;

    const showThreshold = 300;

    const toggleVisibility = () => {
        if (window.scrollY > showThreshold) {
            btn.classList.add('visible');
        } else {
            btn.classList.remove('visible');
        }
    };

    window.addEventListener('scroll', toggleVisibility, { passive: true });
    toggleVisibility();

    btn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

/**
 * Initialize easter egg on avatar
 */
function initEasterEgg() {
    const avatar = document.querySelector('.avatar');
    if (!avatar) return;

    let clickCount = 0;
    let clickTimer = null;
    const messages = [
        'hey there!',
        'you found the secret!',
        'thanks for visiting!',
        'have a great day!',
        'you\'re awesome!'
    ];

    avatar.addEventListener('click', () => {
        clickCount++;
        clearTimeout(clickTimer);

        if (clickCount >= 5) {
            const randomMsg = messages[Math.floor(Math.random() * messages.length)];
            showToast(randomMsg);
            clickCount = 0;
        }

        clickTimer = setTimeout(() => {
            clickCount = 0;
        }, 2000);
    });
}

function textContent(selector) {
    return document.querySelector(selector)?.textContent?.trim() || '';
}

function listText(selector) {
    return Array.from(document.querySelectorAll(selector))
        .map((item) => item.textContent?.replace(/\s+/g, ' ').trim())
        .filter(Boolean);
}

function getProjectEntries() {
    return Array.from(document.querySelectorAll('#projects .entry')).map((entry) => {
        const name = entry.querySelector('h3')?.textContent?.trim() || '';
        const description = entry.querySelector('p')?.textContent?.replace(/\s+/g, ' ').trim() || '';
        const link = entry.querySelector('a[href]')?.href || null;
        const status = entry.querySelector('.date')?.textContent?.trim() || (link ? 'active' : 'listed');

        return { name, status, description, link };
    });
}

function getContactMethods() {
    return {
        email: document.querySelector('.js-ob-email')?.dataset.email || 'iamilyhme@gmail.com',
        x: 'https://x.com/unclelyhme',
        github: 'https://github.com/unclelyhme',
        youtube: 'https://youtube.com/c/unclelyhme',
        instagram: 'https://www.instagram.com/unclelyhme',
        discord: 'https://discord.gg/deb5PtNr7k'
    };
}

function initWebMcp() {
    const modelContext = navigator.modelContext;
    if (!modelContext?.registerTool) return;

    const controller = new AbortController();
    const emptySchema = {
        type: 'object',
        properties: {},
        additionalProperties: false
    };

    try {
        modelContext.registerTool({
            name: 'get-profile-summary',
            description: 'Return the headline, summary, and current focus from unclelyh.me.',
            inputSchema: emptySchema,
            execute: async () => ({
                name: textContent('.header-content h1'),
                headline: textContent('.tagline'),
                summary: textContent('#about p'),
                currentFocus: listText('#now li')
            })
        }, { signal: controller.signal });

        modelContext.registerTool({
            name: 'list-projects',
            description: 'List featured projects from unclelyh.me with descriptions and links.',
            inputSchema: emptySchema,
            execute: async () => ({
                projects: getProjectEntries()
            })
        }, { signal: controller.signal });

        modelContext.registerTool({
            name: 'focus-section',
            description: 'Scroll to a homepage section and return its title and text content.',
            inputSchema: {
                type: 'object',
                properties: {
                    sectionId: {
                        type: 'string',
                        enum: ['about', 'now', 'experience', 'skills', 'projects', 'links']
                    }
                },
                required: ['sectionId'],
                additionalProperties: false
            },
            execute: async ({ sectionId }) => {
                const section = document.getElementById(sectionId);
                if (!section) {
                    throw new Error(`Unknown section: ${sectionId}`);
                }

                section.scrollIntoView({ behavior: 'smooth', block: 'start' });
                return {
                    id: sectionId,
                    title: section.querySelector('h2')?.textContent?.trim() || sectionId,
                    text: section.textContent?.replace(/\s+/g, ' ').trim() || ''
                };
            }
        }, { signal: controller.signal });

        modelContext.registerTool({
            name: 'get-contact-methods',
            description: 'Return public contact methods and profile links for Uncle LYHME.',
            inputSchema: emptySchema,
            execute: async () => getContactMethods()
        }, { signal: controller.signal });
    } catch (error) {
        console.warn('WebMCP registration failed', error);
        controller.abort();
    }
}


/**
 * Initialize tooltips with JavaScript for better cross-browser support
 */
function initTooltips() {
    const tooltips = document.querySelectorAll('.tooltip');

    // Pre-measure all tooltips on page load
    tooltips.forEach(tooltip => {
        const tooltipText = tooltip.querySelector('.tooltip-text');
        if (!tooltipText) return;

        // Temporarily show to measure
        tooltipText.style.display = 'block';
        tooltipText.style.visibility = 'hidden';
        tooltipText.style.position = 'fixed';
        tooltipText.style.left = '0';
        tooltipText.style.top = '0';

        // Force layout and cache width
        tooltipText._cachedWidth = tooltipText.offsetWidth;

        // Reset
        tooltipText.style.display = '';
        tooltipText.style.visibility = '';
        tooltipText.style.position = '';
        tooltipText.style.left = '';
        tooltipText.style.top = '';
    });

    tooltips.forEach(tooltip => {
        const tooltipText = tooltip.querySelector('.tooltip-text');
        if (!tooltipText) return;

        // Show tooltip - position first, then make visible
        const show = () => {
            const padding = 12;
            const viewportWidth = window.innerWidth;
            const parentRect = tooltip.getBoundingClientRect();

            // Use cached width
            const tooltipWidth = tooltipText._cachedWidth || 100;
            const parentCenter = parentRect.left + parentRect.width / 2;

            // Calculate ideal left position (centered on parent)
            let left = parentCenter - tooltipWidth / 2;

            // Clamp to viewport bounds
            if (left < padding) {
                left = padding;
            } else if (left + tooltipWidth > viewportWidth - padding) {
                left = viewportWidth - padding - tooltipWidth;
            }

            // Position arrow to point at parent center
            const arrowLeft = parentCenter - left;

            // Apply ALL styles including display in one go, keeping opacity 0
            tooltipText.style.cssText = `
                display: block;
                position: fixed;
                bottom: auto;
                top: ${parentRect.top - 8}px;
                left: ${left}px;
                transform: translateY(-100%);
                --arrow-left: ${arrowLeft}px;
                opacity: 0;
            `;

            // Double rAF needed for mobile Safari to ensure paint before opacity change
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    tooltipText.style.opacity = '';
                    tooltipText.classList.add('visible', 'positioned');
                });
            });
        };

        // Hide tooltip
        const hide = () => {
            tooltipText.classList.remove('visible', 'positioned');
            tooltipText.style.cssText = '';
        };

        // Track if we're using touch (to avoid mouse/focus interference)
        let usingTouch = false;

        tooltip.addEventListener('touchstart', () => {
            usingTouch = true;
        }, { passive: true });

        // Show tooltip on mouseenter/focus (desktop only)
        tooltip.addEventListener('mouseenter', () => {
            if (!usingTouch) show();
        });
        tooltip.addEventListener('mouseleave', () => {
            if (!usingTouch) hide();
        });
        tooltip.addEventListener('focus', () => {
            if (!usingTouch) show();
        });
        tooltip.addEventListener('blur', () => {
            if (!usingTouch) hide();
        });

        // Toggle on click/tap
        tooltip.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();

            const isVisible = tooltipText.classList.contains('visible');
            if (isVisible) {
                hide();
            } else {
                show();
            }
        });
    });

    // Helper to close all tooltips and reset their styles
    const closeAllTooltips = () => {
        document.querySelectorAll('.tooltip-text.visible').forEach(tt => {
            tt.classList.remove('visible', 'positioned');
            tt.style.cssText = '';
        });
    };

    // Close tooltips when clicking/tapping outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.tooltip')) {
            closeAllTooltips();
        }
    });
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Set current year in footer
    setCurrentYear('year');

    // Initialize theme
    initTheme();

    // Set up theme toggle button
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    // Initialize tooltips
    initTooltips();

    // Initialize back to top button
    initBackToTop();

    // Initialize copy email
    initObfuscatedEmailLinks();
    initCopyEmail();

    // Register browser tools for supporting agents when WebMCP is available
    initWebMcp();

    // Initialize easter egg
    initEasterEgg();

});
