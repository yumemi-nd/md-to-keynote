# Security Policy

## Supported versions

Only the latest version of Markdown to Keynote receives security fixes.
To update, run `/plugin marketplace update narawa-design-plugins`.

## Reporting a vulnerability

Please **don't open a public issue** for security problems.

Report it privately instead: open the repository's **Security** tab and
click **Report a vulnerability**. Only the maintainer can see the report.

Please include:

- What the problem is and what an attacker could do with it
- Steps to reproduce (e.g. the `slides.md`, tool call, or file path that
  triggers it)
- Your macOS, Keynote, and plugin versions

This is a personal project, so I can't promise a fixed response time, but
I aim to reply within a week and will keep you updated until it's fixed.
Once a fix is released, I'm happy to credit you unless you'd rather stay
anonymous.

## Scope

The plugin runs a local MCP server that controls Keynote through
AppleScript and reads and writes files on your Mac. Examples of what's in
scope:

- Text, file paths, or `slides.md` content that makes the server run
  AppleScript or shell commands it shouldn't
- Reading, writing, or overwriting files outside the paths you asked for
- Anything in the hidden record file (`.<name>.key.md-to-keynote.json`)
  that leaks or can be abused

Out of scope: bugs in Keynote, macOS, Claude Code, or `uv` themselves.
Please report those to their vendors.
