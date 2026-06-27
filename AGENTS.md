READ `~/.codex/AGENTS.md` BEFORE ANYTHING (skip if missing).

## Cache Busting

- When you modify `assets/css/style.css` or `assets/js/main.js`, bump the version query parameter in `index.html`.
- Keep the CSS and JS version numbers in sync.

## LLM Metadata

- This site publishes LLM metadata from both `llms.txt` and `.well-known/llms.txt`.
- Keep those two files identical whenever core site positioning, major sections, or key links change.
