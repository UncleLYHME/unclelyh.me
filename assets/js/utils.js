/**
 * Utility functions
 */

/**
 * Set the current year in an element
 * @param {string} elementId - The ID of the element to update
 */
export function setCurrentYear(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = new Date().getFullYear();
    }
}
