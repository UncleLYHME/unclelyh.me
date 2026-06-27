---
summary: 'Agent discovery and markdown negotiation surface for unclelyh.me.'
read_when:
  - Updating well-known discovery files, markdown negotiation, or WebMCP tools.
  - Changing homepage machine-readable metadata or agent discovery files.
---

# Agent Readiness

This site publishes a small, truthful agent surface:

- homepage `Link` headers from `.htaccess`
- markdown negotiation for `/` via `index.md`
- `Content-Signal` preferences in `robots.txt`
- agent skills at `/.well-known/agent-skills/index.json`
- browser-side WebMCP tools in `assets/js/main.js`

## Public machine-readable files

- `llms.txt`
- `.well-known/llms.txt`
- `.well-known/agent-skills/index.json`

## Intentional omissions

- No OAuth or OIDC discovery documents: this repo is a static public website and does not run a protected API.
- No MCP server card: the site exposes browser-side WebMCP tools, not a standalone MCP server transport.

If the site later adds protected APIs or a real MCP server endpoint, publish the matching well-known metadata then.
