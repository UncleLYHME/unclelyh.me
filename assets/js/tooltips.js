/**
 * Tooltips ("explain like I'm five" glossary), positioned with JS for
 * reliable cross-browser / mobile-safe placement.
 */
export function initTooltips() {
    const tooltips = document.querySelectorAll('.tooltip');

    // Pre-measure all tooltips so positioning is instant on first show.
    tooltips.forEach((tooltip) => {
        const tt = tooltip.querySelector('.tooltip-text');
        if (!tt) return;
        tt.style.display = 'block';
        tt.style.visibility = 'hidden';
        tt.style.position = 'fixed';
        tt.style.left = '0';
        tt.style.top = '0';
        tt._cachedWidth = tt.offsetWidth;
        tt.style.display = '';
        tt.style.visibility = '';
        tt.style.position = '';
        tt.style.left = '';
        tt.style.top = '';
    });

    tooltips.forEach((tooltip) => {
        const tt = tooltip.querySelector('.tooltip-text');
        if (!tt) return;

        const show = () => {
            const padding = 12;
            const viewportWidth = window.innerWidth;
            const parentRect = tooltip.getBoundingClientRect();
            const tooltipWidth = tt._cachedWidth || 100;
            const parentCenter = parentRect.left + parentRect.width / 2;

            let left = parentCenter - tooltipWidth / 2;
            if (left < padding) left = padding;
            else if (left + tooltipWidth > viewportWidth - padding) left = viewportWidth - padding - tooltipWidth;

            const arrowLeft = parentCenter - left;
            tt.style.cssText = `
                display: block; position: fixed; bottom: auto;
                top: ${parentRect.top - 8}px; left: ${left}px;
                transform: translateY(-100%);
                --arrow-left: ${arrowLeft}px; opacity: 0;`;

            requestAnimationFrame(() => requestAnimationFrame(() => {
                tt.style.opacity = '';
                tt.classList.add('visible', 'positioned');
            }));
        };

        const hide = () => {
            tt.classList.remove('visible', 'positioned');
            tt.style.cssText = '';
        };

        let usingTouch = false;
        tooltip.addEventListener('touchstart', () => { usingTouch = true; }, { passive: true });
        tooltip.addEventListener('mouseenter', () => { if (!usingTouch) show(); });
        tooltip.addEventListener('mouseleave', () => { if (!usingTouch) hide(); });
        tooltip.addEventListener('focus', () => { if (!usingTouch) show(); });
        tooltip.addEventListener('blur', () => { if (!usingTouch) hide(); });
        tooltip.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            tt.classList.contains('visible') ? hide() : show();
        });
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.tooltip')) {
            document.querySelectorAll('.tooltip-text.visible').forEach((tt) => {
                tt.classList.remove('visible', 'positioned');
                tt.style.cssText = '';
            });
        }
    });
}
