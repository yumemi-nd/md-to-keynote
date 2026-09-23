# Keynote Builder

A plugin that lets Claude build Keynote slides for you.

> [!NOTE]
> - **Just write Markdown**
>    - Write your slide content in `slides.md` and tell Claude "Build a Keynote deck from this file" — Claude creates the slides for you.
> - **Works with your theme**
>    - Text goes into the theme's own title and body placeholders, so fonts, colors, and bullet styles stay intact. "Reapply Layout to Slide" works too.
> - **Three ways to write**
>    - Write it all yourself
>    - Write notes per slide and let Claude write from them
>    - Pick a topic and let Claude write the whole deck
> - **Safe to edit afterwards**
>    - If you make changes in Keynote and run it again, you can choose to update the deck while keeping your changes, or rebuild it. Nothing is overwritten without your confirmation.

<br>
Build Keynote (`.key`) decks by chat, using the theme's real registered
title/body placeholders — so slides inherit
the theme's fonts, colors, and bullet styles automatically, with no manual
font-size or position tuning.

## Requirements

- **macOS** with **Keynote.app** installed.
- [`uv`](https://docs.astral.sh/uv/) available on your PATH (used to run
  the bundled MCP server without a separate install step). If Claude's
  desktop app doesn't inherit your shell PATH, install uv with
  `curl -LsSf https://astral.sh/uv/install.sh | sh` and, if the MCP server
  fails to start, point the server's `command` at the full path to `uv`
  (e.g. `~/.local/bin/uv`) in your MCP settings.
- Claude must be linked to a Mac with Keynote and the MCP server running as
  a local process (a Cowork session on the desktop app, or Claude Code with
  local MCP servers enabled). This will not work purely in a cloud sandbox
  with no access to a real Mac.

## Components

| Component  | What it does |
|------------|---------------|
| Skill: `keynote-slide-builder` | Reads a `slides.md`, plans a deck, and drives the MCP server's tools to build and verify it. |
| MCP server: Keynote MCP (`keynote-builder-mcp`) | A bundled Python script (run via `uv run`) that drives Keynote through AppleScript, setting text on the theme's real placeholders (title, body, and subtitle slots) rather than creating freeform text boxes. It can also open and update an existing `.key`, describe each layout's slots, and fix individual slides (change layout, move or delete items, delete slides). |

## Setup

Install this plugin normally. Claude should detect the bundled
Keynote MCP server (`keynote-builder-mcp`) automatically. The first time you use it,
confirm the `keynote-builder-mcp__*` tools are available — if not, check that
`uv` is installed and reachable, per the Requirements section above.

## Usage

Copy `skills/keynote-slide-builder/references/slides-template.md` into
your project folder as `slides.md`. Fill in the deck-wide settings at the
top (`mode`, `theme`, `output`, `layout_policy`, `text_rules`, `assets`,
`color`, `request`), then choose how to provide the content:

- **Write the final text yourself (`mode: verbatim`, the default)**: below
  the settings, write each slide's actual title, bullets, layout, and
  images directly, similar to Marp. Claude uses your text verbatim.
- **Write notes per slide and let Claude write the text
  (`mode: generate`)**: write rough notes, keywords, or drafts for each
  slide. Claude writes each slide's title and body from your notes,
  following `text_rules` and `request`, keeping your slide order, layouts,
  and images. It won't invent facts that aren't in your notes; it leaves
  placeholders like `[TODO: add example]` instead.
- **Let Claude write the whole deck**: delete the example slides and
  describe what you want in `request` (or in chat).

Write layouts as roles that work with any theme — `cover`, `section`,
`body` (title + bullets), `body+image`, `image`, `title-only`, `quote`,
`blank` — e.g. `<!-- layout: body -->`. Claude maps
each role to the matching layout of your theme. A `## line` becomes the
slide's subtitle.

To switch modes for a single slide, put `<!-- mode: generate -->` or
`<!-- mode: verbatim -->` at the top of that slide. You can also tell
Claude the mode in chat, which overrides the `mode` setting in the file.

Full syntax is in
`skills/keynote-slide-builder/references/slides-guide.md`.

Then:

1. Ask Claude to build the deck, e.g. "Build a Keynote deck about X using
   this slides.md."
2. Claude will create the `.key` file at `output` (or next to
   `slides.md`), build each slide using the theme's real placeholders, and
   verify a sample of the slides visually (images go to the system temp
   folder, not your project) before reporting the finished file path.
3. Running it again when the `.key` already exists: Claude asks whether
   to **update** the file in place (keeping the layout changes and image
   moves you made in Keynote) or **rebuild** it from scratch. It never
   overwrites a file without asking. When updating, Claude also finds any
   text you rewrote in Keynote and asks, slide by slide, whether to keep
   your text or replace it with `slides.md`. To tell your edits apart from
   its own, the plugin keeps a small hidden file next to the deck
   (`.<name>.key.keynote-builder.json`); deleting it just turns this check
   off for that deck.

## Notes

- The MCP server never sets font sizes manually — that's the whole point.
  Coordinates are only changed to fix a specific problem, such as moving
  an image off the body text. If a deck still looks cramped, that's a sign the
  theme's placeholder is genuinely too small for the amount of text; trim
  the text rather than asking for a manual size override.
- PDF export (`export_pdf`) has been unreliable for visual verification in
  some environments; the skill prefers `export_slide_images` (per-slide
  JPEG export) instead.

## Support

If this plugin saves you time, you can buy me a coffee.

<a href="https://www.buymeacoffee.com/n__yumemi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" style="height: 40px !important;width: auto !important;" ></a>