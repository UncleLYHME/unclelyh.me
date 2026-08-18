/**
 * Browser-side WebMCP tools. Registered only when a supporting agent
 * exposes navigator.modelContext. Exposes read-only, public profile data.
 */

function textContent(selector) {
    return document.querySelector(selector)?.textContent?.trim() || '';
}

function listText(selector) {
    return Array.from(document.querySelectorAll(selector))
        .map((item) => item.textContent?.replace(/\s+/g, ' ').trim())
        .filter(Boolean);
}

function getProjectEntries() {
    return Array.from(document.querySelectorAll('#projects .card')).map((card) => {
        const name = card.querySelector('h3')?.textContent?.trim() || '';
        const description = card.querySelector('p')?.textContent?.replace(/\s+/g, ' ').trim() || '';
        const link = card.querySelector('a[href]')?.href || null;
        const status = card.querySelector('.card-status')?.textContent?.trim() || (link ? 'active' : 'listed');
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
        discord: 'https://discord.gg/deb5PtNr7k',
    };
}

export function initWebMcp() {
    const modelContext = navigator.modelContext;
    if (!modelContext?.registerTool) return;

    const controller = new AbortController();
    const emptySchema = { type: 'object', properties: {}, additionalProperties: false };

    try {
        modelContext.registerTool({
            name: 'get-profile-summary',
            description: 'Return the headline, summary, and current focus from unclelyh.me.',
            inputSchema: emptySchema,
            execute: async () => ({
                name: 'Morgan Nuttall (Uncle LYHME)',
                headline: textContent('.hero-tagline'),
                summary: textContent('.hero-about p'),
                currentFocus: listText('#now li'),
            }),
        }, { signal: controller.signal });

        modelContext.registerTool({
            name: 'list-projects',
            description: 'List featured projects from unclelyh.me with descriptions and links.',
            inputSchema: emptySchema,
            execute: async () => ({ projects: getProjectEntries() }),
        }, { signal: controller.signal });

        modelContext.registerTool({
            name: 'focus-section',
            description: 'Scroll to a homepage section and return its title and text content.',
            inputSchema: {
                type: 'object',
                properties: {
                    sectionId: { type: 'string', enum: ['about', 'now', 'experience', 'skills', 'projects', 'links'] },
                },
                required: ['sectionId'],
                additionalProperties: false,
            },
            execute: async ({ sectionId }) => {
                const section = document.getElementById(sectionId);
                if (!section) throw new Error(`Unknown section: ${sectionId}`);
                section.scrollIntoView({ behavior: 'smooth', block: 'start' });
                return {
                    id: sectionId,
                    title: section.querySelector('h2')?.textContent?.trim() || sectionId,
                    text: section.textContent?.replace(/\s+/g, ' ').trim() || '',
                };
            },
        }, { signal: controller.signal });

        modelContext.registerTool({
            name: 'get-contact-methods',
            description: 'Return public contact methods and profile links for Morgan Nuttall (Uncle LYHME).',
            inputSchema: emptySchema,
            execute: async () => getContactMethods(),
        }, { signal: controller.signal });
    } catch (error) {
        console.warn('WebMCP registration failed', error);
        controller.abort();
    }
}
