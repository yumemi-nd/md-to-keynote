# MD to Keynote

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

## Requirements

- A Mac with **Keynote** installed
- [**uv**](https://docs.astral.sh/uv/), which runs the plugin's bundled server. If you don't have it:

  ```
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

- **Claude Code** running on that Mac. Cloud-only environments can't reach Keynote, so they won't work.

## Installation

1. In Claude Code, run:

   ```
   /plugin marketplace add yumemi-nd/md-to-keynote
   /plugin install md-to-keynote@narawa-design-plugins
   ```

2. Restart Claude Code, or run `/reload-plugins`.
3. Run `/mcp` and check that `md-to-keynote-mcp` is listed as connected.
   If it isn't, see [Troubleshooting](#troubleshooting).

The first time Claude opens Keynote, macOS asks whether to allow it to
control Keynote. Click **Allow** — the plugin can't work without it.

To update to a new version later, run
`/plugin marketplace update narawa-design-plugins`.

## Quick start

1. Download the template [`slides.md`](https://github.com/yumemi-nd/md-to-keynote/blob/main/skills/keynote-slide-builder/references/slides.md)
   and put it in your project folder.
2. Set `theme` at the top to a theme name exactly as it appears in
   Keynote's theme chooser (e.g. `Basic White`, or `ベーシックホワイト` if
   Keynote is in Japanese). Replace the example slides with your own.
3. Ask Claude: "Build a Keynote deck from this slides.md."

Claude saves the `.key` next to `slides.md` (or wherever `output` says),
checks a few slides visually, and tells you the file path.

## Writing `slides.md`

The top of the file holds the settings; below it, a line with only `---`
separates slides. Each slide uses `#` for the title, `##` for the subtitle,
`-` for bullets, and `![description](/path/to/image.png)` for images.

Choose how the text is written with `mode`:

| You want to… | Do this |
|---|---|
| Write the final text yourself | `mode: verbatim` (default). Claude uses your text as written. |
| Write notes and let Claude write the text | `mode: generate`. Claude writes each slide from your notes and never invents facts — gaps get a `[TODO: …]` placeholder. |
| Let Claude write the whole deck | Delete the example slides and describe the deck in `request`. |

To change the mode or layout of a single slide, put `<!-- mode: generate -->`
or `<!-- layout: section -->` at the top of that slide.

For every setting, layout name, and rule, see the
[full guide](https://github.com/yumemi-nd/md-to-keynote/blob/main/skills/keynote-slide-builder/references/slides-guide.md).

## Updating a deck

If the `.key` already exists, Claude asks whether to:

- **Update** it — keeps the layout changes and image moves you made in
  Keynote. If you also rewrote text in Keynote, Claude shows those slides
  and asks, one by one, whether to keep your text or use `slides.md`.
- **Rebuild** it — starts over from the theme. Your Keynote edits are lost.

To tell your edits apart from its own, the plugin keeps a small hidden file
next to the deck (`.<name>.key.md-to-keynote.json`). If you delete it,
Claude can no longer detect text edits for that deck and asks before
overwriting any text.

## Troubleshooting

- **`md-to-keynote-mcp` doesn't connect**: check that `uv --version`
  works in Terminal. If it does but the server still fails, set the
  server's `command` to the full path of `uv` (e.g. `~/.local/bin/uv`) in
  your MCP settings.
- **Claude can't control Keynote**: open System Settings → Privacy &
  Security → Automation, and allow Keynote for the app running Claude.
- **Text looks cramped**: the plugin never shrinks fonts, so the theme's
  placeholder is too small for that much text. Shorten the text, or set a
  limit in `text_rules`.

## Credits & Support

- Inspired by [ByAxe/keynote-mcp](https://github.com/ByAxe/keynote-mcp)
  (a fork of [easychen/keynote-mcp](https://github.com/easychen/keynote-mcp)).
- If this plugin saves you time, you can buy me a coffee.

  <a href="https://www.buymeacoffee.com/n__yumemi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" height="40"></a>
