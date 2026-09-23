---
name: keynote-slide-builder
description: This skill should be used when the user asks to "build a Keynote deck", "create Keynote slides", "make a .key presentation", "update my Keynote deck", or wants a Keynote deck generated from a Marp-like slides.md file, without manually tuning font sizes or text-box positions. Requires macOS with Keynote.app and the bundled Keynote MCP server (md-to-keynote-mcp).
metadata:
  version: "1"
---

# Keynote Slide Builder

Build Keynote presentations using the Keynote MCP server (`md-to-keynote-mcp`) bundled
with this plugin (tools appear as `mcp__md-to-keynote-mcp__*`), which sets text
on a slide's REAL title/body placeholders (`default title item` / `default
body item`) and the layout's other text slots (e.g. subtitles) via AppleScript.
This means slides automatically inherit the theme's registered font sizes,
colors, and bullet styles — never set font size manually with this skill,
and only move items (`set_item_geometry`) to fix overlaps such as an image
covering the body. Requires macOS with Keynote.app installed; the server
drives Keynote through AppleScript (`osascript`), so it will not work on
other platforms or without Keynote.

This skill is tuned for quality AND for keeping tool-call and token spend
low — batch aggressively wherever a step below says to, and skip steps
whose answer is already known (see the layout map in step 2).

## 0. Load the tools

Call `ToolSearch` with `select:mcp__md-to-keynote-mcp__create_presentation,mcp__md-to-keynote-mcp__open_presentation,mcp__md-to-keynote-mcp__find_text_edits,mcp__md-to-keynote-mcp__accept_text_edits,mcp__md-to-keynote-mcp__list_slides,mcp__md-to-keynote-mcp__list_layouts,mcp__md-to-keynote-mcp__add_slide,mcp__md-to-keynote-mcp__set_title,mcp__md-to-keynote-mcp__set_body,mcp__md-to-keynote-mcp__list_slide_items,mcp__md-to-keynote-mcp__set_text_item,mcp__md-to-keynote-mcp__add_image,mcp__md-to-keynote-mcp__set_item_geometry,mcp__md-to-keynote-mcp__delete_item,mcp__md-to-keynote-mcp__delete_slide,mcp__md-to-keynote-mcp__set_slide_layout,mcp__md-to-keynote-mcp__save_presentation,mcp__md-to-keynote-mcp__export_slide_images` in one call (the exact tool-name prefix may differ slightly depending on how this plugin's MCP server is exposed in the current session — check the available tool list if the names above don't match, and use whatever prefix wraps `md-to-keynote-mcp__*`).

If these tools aren't available, tell the user the Keynote MCP (`md-to-keynote-mcp`)
server from this plugin isn't running (macOS + Keynote.app required) and
stop.

## 1. Find `slides.md`

Look in the project folder the user names (ask for the path if it's not
obvious) for **`slides.md`** — a single Marp-like file that holds both the
deck-wide policy and, optionally, each slide's content:

- **Frontmatter** (between the first two `---` lines): `mode`
  (`verbatim` or `generate`, default `verbatim`), `theme` (must match
  Keynote's theme chooser exactly), `output` (where to save the `.key`),
  `layout_policy`, `text_rules`, `assets`, `color`, and `request` (topic,
  audience, tone — used for `generate` slides and when there are no slides
  below).
- **Slides** (after the frontmatter, separated by `---`): each slide's
  title (`#`), subtitle (`##`), bullets, layout, and images, written by the
  user — either final text (`verbatim`) or notes for Claude to write from
  (`generate`). A slide can override the deck-wide mode with
  `<!-- mode: ... -->`.

See `references/slides-guide.md` for the full spec (frontmatter keys and
defaults, `output` resolution, slide separators, layout roles and the
role→layout mapping, where `##` subtitles go, `generate` rules including
title-only slides, and layout auto-inference). If no `slides.md` exists,
point the user at the template `references/slides.md` to copy into their
folder and fill in, or ask directly for the frontmatter fields.

## 2. Plan the deck

**Save path and new vs. update** — resolve the `.key` path from `output`
per the guide (relative to `slides.md`'s folder; blank → the cover title
as the filename) before creating anything. If a file already exists at
that path, **ask the user every time** (with `AskQuestion` when available)
whether to:

- **Update** it — open it and change the text in place, keeping any
  layout changes, moved images, and other edits they made in Keynote
  (text they rewrote in Keynote is kept or overwritten per slide, as they
  choose — see 3b); or
- **Rebuild** it — recreate it from the theme with `overwrite=true`
  (their manual edits are lost).

Never overwrite without asking. `create_presentation` and `save_as`
refuse existing paths unless `overwrite=true`.

**Content** — if `slides.md` has slides after the frontmatter, parse them
per `references/slides-guide.md` and resolve each slide's mode — a mode
the user gave in chat overrides the frontmatter `mode`, and a slide's own
`<!-- mode: ... -->` overrides both.

- **`verbatim` slides**: use the user's title/subtitle/bullet/image text
  verbatim, don't paraphrase or shorten it. If a slide's text clearly
  exceeds `text_rules`, don't rewrite it — just note it in the final report.
- **`generate` slides**: treat everything written on the slide as notes
  and write that slide's title, subtitle, and body from them, following
  `request`, `layout_policy`, and `text_rules` strictly. Keep one output
  slide per input slide (no adding, splitting, dropping, or reordering),
  keep the user's `<!-- layout: ... -->` and image lines as-is, and never
  invent facts the notes don't contain — insert a placeholder like
  `[TODO: add example]` instead and list those slides in the final report.
  For a title-only `generate` slide, follow the guide's rule: leave the
  body empty for section/title-only/cover roles, otherwise write a body
  from the title, `request`, and neighboring slides — never leave a body
  placeholder silently empty.

If `slides.md` has only the frontmatter (no slides), draft the full
slide-by-slide content (title, subtitle, bullets, and a layout role per
slide) in one pass from `request` and what the user asked for in chat,
respecting `text_rules` strictly — getting the text length right during
planning avoids a costly fix-and-reverify round trip later.

**Layout map** — layouts are written as roles (cover, section, body,
body+image, image, title-only, quote, blank), as exact layout names, or as
`#N` indexes. After creating or opening the document, call
`list_layouts()` once per theme per session. It returns each layout's
index, title/body shown or HIDDEN, extra text slots (subtitles — empty or
holding VISIBLE sample text like "Subtitle" / "サブタイトル"), image placeholders, and
fixed layout text. Build a role→index map from it using the guide's
table, and reuse it for the rest of the session. Always pass
`layout_index` (not a name) to `add_slide` / `set_slide_layout`, since
names can repeat within a theme. When a role has no good match, pick the
closest and mention the substitution in the final report.

## 3a. Build a new deck — batch calls per message

1. `create_presentation(title, theme=<theme>, path=<resolved output>)` —
   pass `overwrite=true` only if the user chose Rebuild. **Slide 1 already
   exists** after this call: use it for the first slide (switch it with
   `set_slide_layout(1, layout_index=...)` if the cover role maps to a
   different layout), and let `add_slide` start from slide 2.
2. `list_layouts()` (skip if the map for this theme is already known).
3. Build slides in batches of 2 within a single tool-call message where
   the content is already fully planned: e.g. `add_slide(layout_index=…)`
   → `set_title(N)` → `set_body(N)` → `add_slide` → `set_title(N+1)` →
   `set_body(N+1)`, then the next message covers N+2/N+3, and so on.
   Keynote runs the AppleScript calls one at a time regardless of how
   many are queued in one message, so this just halves the round trips.
   Skip `set_body` for slides whose role has no body.
4. **Subtitles and sample text** — follow the guide's subtitle rule: on
   the cover, `##` goes into the body via `set_body`; on other slides, if
   the layout map shows an extra text slot below the title, call
   `list_slide_items(N)` and then `set_text_item(N, item_index, text)`
   into that slot (it refuses the title placeholder, so a subtitle can't
   overwrite the title). If a slide has no `##` but its layout carries
   visible sample text (`text_slot_sample`), remove it with `delete_item`.
   The item indexes for a given layout are the same on every slide made
   from it, so after checking one slide you can reuse the index for later
   slides with that layout in the same batch.
5. **Hidden placeholders** — `set_title` / `set_body` refuse to write into
   a placeholder the layout hides and say "NOT WRITTEN". Don't ignore it:
   either choose a layout whose map shows the placeholder, or retry with
   `show=true` when the text genuinely belongs on this layout.
6. **Images** — `add_image(slide_number, image_path)` in the same batched
   message as that slide's other calls, for each `![alt](path)` line plus
   any `assets` no slide already places. It returns the image's item index
   and geometry and warns when it overlaps text. On a warning, fix it
   right away with `set_item_geometry` (e.g. place it beside or below the
   body, using the reported coordinates; images keep their aspect ratio),
   or pass `x`/`y`/`width`/`height` to `add_image` directly when you
   already know the free area.
7. `save_presentation()` roughly every 3-4 slides, not after every single
   one and not only at the end.
8. Don't make a separate `get_slide_count()` call — `add_slide` returns
   the running slide count.

## 3b. Update an existing deck

1. `open_presentation(path)` — returns every slide's number, layout, and
   title. Then `list_layouts()` if the map for this theme isn't known.
2. **Check for text the user rewrote in Keynote** — call
   `find_text_edits()` before writing any text. It compares the deck with
   the text this plugin last wrote (kept in a hidden
   `.<name>.key.md-to-keynote.json` next to the `.key`).
   - If it reports edits, show the user each edited slide with its Keynote
     text and the new text from `slides.md`, and ask (with `AskQuestion`
     when available, one question per edited slide, or one "keep all /
     overwrite all" question when there are many) whether to **keep** the
     Keynote text or **overwrite** it. For kept fields, don't call
     `set_title` / `set_body` / `set_text_item` on them, and call
     `accept_text_edits(N)` for those slides so they aren't reported again.
     In the final report, mention that `slides.md` still has the old text
     for kept verbatim slides (a rebuild would bring it back) and offer to
     copy the kept text into `slides.md`.
   - If it reports slides the plugin never wrote or missing slides, slides
     were added, deleted, or reordered in Keynote: tell the user and agree
     on which `slides.md` slide goes to which deck slide before writing.
   - If it reports `NO RECORD`, edits can't be detected for this deck:
     tell the user and ask whether to overwrite the text with `slides.md`
     or stop, before writing anything.
3. Match `slides.md` slide N to deck slide N. Update only the text:
   `set_title`, `set_body`, and `set_text_item` for subtitles. These skip
   the write when the text is already identical, so the user's formatting
   on unchanged text survives. **Keep each existing slide's layout, image
   positions, and other items as they are** — the user may have adjusted
   them by hand in Keynote. Only change a layout with `set_slide_layout`
   if the user explicitly asked for it.
4. For images, add only those from `slides.md` that the slide doesn't
   already have (check with `list_slide_items`); don't move or re-add
   existing ones.
5. If `slides.md` now has more slides, add them at the end with
   `add_slide(layout_index=…)` as in 3a. If the deck has extra slides that
   `slides.md` no longer has, list them and ask the user before calling
   `delete_slide` (delete from the highest number down so the numbers don't
   shift under you).
6. `save_presentation()` when done.

Known quirk: the Keynote window can still show a "keep this new document?"
prompt if the user closes it by hand. That's cosmetic — the file on disk
is current after your last `save_presentation()` call.

## 4. Verify before handing back

Call `export_slide_images()` with no arguments. It writes into a fresh
folder in the system temp directory, so there is nothing to clean up in
the project folder. It returns each image's absolute path in slide order;
read back only a **sample**, not every slide, to keep token spend down:

- Always check: slide 1, slide 2, slide 3, and the last slide, plus every
  slide you changed in an update.
- If the deck has more than 4 slides, also check a few random slides from
  the rest, scaled to the deck size: `extra = min(5, max(1, total_slides // 5))`
  additional slide numbers picked at random (no repeats).

Don't use `export_pdf` for this — PDF pages have rendered blank when read
back in some environments; the per-slide image export is reliable.

For each sampled slide, confirm: no overlapping text or images, no obvious
overflow, no leftover sample text ("Subtitle" / "サブタイトル",
"Title Text" / "タイトルテキスト"),
and that the title/subtitle/body landed on the intended slide. Fix only the
affected slide(s) in place: `set_item_geometry` for overlaps, `delete_item`
for leftovers, `set_slide_layout` for a wrong layout, and
`set_title`/`set_body`/`set_text_item` for text. Never rebuild the deck to
fix one slide. Then re-save and re-export, and check just those slides.

Report the final `.key` file path in one or two sentences, plus any layout
substitutions, `text_rules` overruns, and slides with `[TODO: …]`
placeholders — don't re-describe every slide's content back to the user.
