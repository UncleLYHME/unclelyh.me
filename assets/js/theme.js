/**
 * Theme management module
 * Handles dark/light mode switching with localStorage persistence
 */

const STORAGE_KEY = 'theme';

/**
 * Set the theme and persist to localStorage
 * @param {boolean} dark - Whether to use dark theme
 */
export function setTheme(dark) {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
    localStorage.setItem(STORAGE_KEY, dark ? 'dark' : 'light');
}

/**
 * Get the current theme preference
 * @returns {boolean} - True if dark theme is active
 */
export function isDarkTheme() {
    return document.documentElement.getAttribute('data-theme') === 'dark';
}

/**
 * Toggle between dark and light theme with smooth transition
 */
export function toggleTheme() {
    // Add transition class for smooth color changes
    document.documentElement.classList.add('theme-transitioning');

    setTheme(!isDarkTheme());

    // Remove transition class after animation completes
    setTimeout(() => {
        document.documentElement.classList.remove('theme-transitioning');
    }, 300);
}

/**
 * Initialize theme based on saved preference or system preference
 */
export function initTheme() {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
    const savedTheme = localStorage.getItem(STORAGE_KEY);

    if (savedTheme) {
        setTheme(savedTheme === 'dark');
    } else {
        setTheme(prefersDark.matches);
    }

    // Listen for system theme changes (only applies if no saved preference)
    prefersDark.addEventListener('change', (e) => {
        if (!localStorage.getItem(STORAGE_KEY)) {
            setTheme(e.matches);
        }
    });
}
