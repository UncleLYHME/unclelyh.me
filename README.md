# unclelyh.me

Source for Uncle LYHME's personal website: a static HTML/CSS/JavaScript site with a public profile, selected projects, contact links, markdown mirrors, and agent discovery metadata.

## Structure

```text
├── assets/                  # Public static assets
│   ├── css/                 # Site styles
│   ├── img/                 # Images and avatars
│   └── js/                  # Browser JavaScript modules
├── nginx/                   # Nginx runtime configuration
├── .well-known/             # Agent/client discovery metadata
│   └── agent-skills/        # Static AgentSkill discovery files
├── .docs/                   # Maintenance notes and references
│   └── references/          # Operator-facing docs
├── index.html               # Main website
├── index.md                 # Markdown mirror of homepage content
├── 404.html                 # Static not-found page
├── compose.yaml             # Docker Compose deployment
├── Dockerfile               # Nginx container image
├── llms.txt                 # LLM-readable site summary
└── LICENSE                  # MIT license
```

## Commands

| Command | Action |
| :------ | :----- |
| `python3 -m http.server 8080` | Starts a local static server at `localhost:8080` |
| `docker compose up --build` | Builds and runs the nginx container locally |

## Maintenance

- Styles live in `assets/css/{tokens,layout,components}.css` (with `style.css` as an `@import` shim); scripts live in `assets/js/` (`main.js` entry, plus `chat`, `cable`, `palette`, `tooltips`, `webmcp`, `utils`). When editing any CSS/JS, bump the `?v=` query parameter versions in `index.html`.
- The homepage is a single dark "datacenter" theme: sections are rack units fed by per-section SVG patch cables (`assets/js/cable.js`) from the `core-sw01` switch panel, and the intro lives in an Intercom-style chat popup (`assets/js/chat.js`, quick-reply buttons only).
- Keep `llms.txt` and `.well-known/llms.txt` identical.
- Do not commit deployment credentials, private notes, generated auth files, or machine-specific config.

## License

This repository is licensed under the [MIT License](LICENSE).
