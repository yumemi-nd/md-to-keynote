# Writing slides.md

`slides.md` is the instruction file for building a Keynote deck.
One file holds both the deck-wide settings (theme, text limits, save location, etc.) and each slide's content.

## How to use

1. Copy the template `slides.md` from this folder into your working folder
2. Edit the settings at the top and each slide's content
3. Ask Claude: "Build a Keynote deck from this slides.md"

If a `.key` with the same name already exists at the save location, Claude asks every time whether to update it (keeping your edits made in Keynote) or rebuild it.

## File structure

```markdown
---
mode: generate
theme: Basic White
output: presentation.key
layout_policy: auto-select based on content
text_rules: titles under 30 characters; bullets one line each, max 5
assets: none
color: theme default
request:
---

# Main Title
## Subtitle (a one-liner for the cover)

---
<!-- layout: body -->
<!-- mode: verbatim -->

# What It Does
## Three key points
- Generates a .key directly from a chat request
- Uses the theme's own text sizes

---
<!-- layout: section -->

# Next Section

---

# Benefits
- less work time, consistent design

---
# Slide with an Image
![Logo](/Users/example/Pictures/logo.png)
- Supporting text
```

- The block between the first `---` and the next `---` at the top of the file is the **settings**.
- Below that, a line containing only `---` separates slides. Everything between two separators is one slide.

## Settings

Write one setting per line as `key: value`. Lines starting with `#` are comments and are ignored.
Settings left blank use the "If blank" behavior.

| Key | What to write | If blank |
|---|---|---|
| `mode` | How slide content is handled: `generate` or `verbatim` (see "Modes" below) | `generate` |
| `theme` | The theme name exactly as shown in Keynote's theme chooser (it depends on Keynote's language, e.g. `Basic White` / `ベーシックホワイト`) | Claude asks |
| `output` | Where to save the `.key`: a path starting with `/Users/…`, or a path relative to `slides.md` (e.g. `presentation.key`, `out/presentation.key`) | Saved next to `slides.md`, named after the cover title |
| `layout_policy` | Which layouts to use for which slides | Auto-select based on content |
| `text_rules` | Text length rules (e.g. titles under 30 characters, max 5 bullets) | No limits |
| `assets` | Paths to images or logos on your Mac (starting with `/Users/…`), comma-separated | None |
| `color` | Color names or HEX codes to use (e.g. `#1E88E5`) | Theme colors |
| `request` | What you want when Claude writes text (topic, audience, tone, slide count, etc.) | What you asked in chat |

## Writing slides

| Syntax | Role on the slide |
|---|---|
| `# Heading` | Title (only the first one per slide is used) |
| `## Heading` | Subtitle. If the layout has no subtitle slot, it becomes the first line of the body |
| `- item` or `* item` | One bullet |
| `![description](image path)` | Places an image on the slide |
| `<!-- layout: role -->` | Sets the slide's layout (put it at the top of the slide) |
| `<!-- mode: verbatim -->` | Changes the mode for this slide only (put it at the top of the slide) |

### Specifying layouts

We recommend writing layouts as **roles**, which work with any theme. Claude picks the layout in your theme that fits each role.

| Role | Use for |
|---|---|
| `cover` | The first slide (title + subtitle) |
| `section` | Chapter breaks (a large title only) |
| `body` | Title + bullets |
| `body+image` | Title + bullets + image |
| `image` | Title + image (no bullets) |
| `title-only` | A title, with the rest of the slide free |
| `quote` | A quote or a big statement |
| `blank` | An empty slide |

To pick a specific layout from the theme, you can also write its name (e.g. `<!-- layout: Title & Bullets -->` / `<!-- layout: タイトルと本文 -->`) or the number Claude showed in its list (e.g. `<!-- layout: #5 -->`). In themes with several layouts of the same name, a number is more reliable.
If omitted, a layout is chosen automatically based on the content.

## Modes

| Mode | Behavior | Best when |
|---|---|---|
| `generate` (default) | Your content is treated as notes, and **Claude writes the text** | You only have key points or keywords |
| `verbatim` | Your text goes onto the slide **as written** | Your text is final |

- **Whole deck**: change `mode` in the settings
- **One slide**: put `<!-- mode: generate -->` or `<!-- mode: verbatim -->` at the top of that slide
- **In chat**: ask, e.g., "Build it in verbatim mode"

When several are given, priority is **per-slide setting → chat instruction → settings `mode`**.

In `generate`, Claude never invents facts (numbers, company names, examples, etc.) that aren't in your notes.
Gaps get a placeholder like `[TODO: add example]`, and Claude tells you at the end which slides still have them.

If a `generate` slide has only a title, the body stays empty for section or title-only slides.
For slides with a body, Claude writes it from the title, `request`, and the surrounding slides.

If you write no slides and only the settings, Claude creates every slide from `request`, regardless of mode.

---

## Processing rules for Claude

Everything below is for Claude when reading `slides.md`. Users don't need to read it.

### Parsing

- Settings = from the first `---` at the top of the file to the next `---` (frontmatter). After that, a standalone `---` line separates slides.
- If nothing follows the settings (only blank lines or comments), follow "When there are no slides".
- At the top of a slide (ignoring blank lines), `<!-- layout: ... -->` and `<!-- mode: ... -->` are both valid, in any order.
- `# Heading` → `set_title`. Ignore any further `#` headings.
- `## Heading` → follow "Where subtitles go".
- `- item` / `* item` → pass all items on the slide to `set_body`, newline-separated.
- `![alt](path)` → `add_image(slide_number, path)`.

### Save path (`output`)

- Use absolute paths as-is; resolve relative paths from the folder containing `slides.md`. Append `.key` if missing.
- If blank, use `<cover title>.key` next to `slides.md` (replace characters not allowed in filenames with `-`).
- If a file already exists at that path, always ask the user before starting whether to update (keep edits) or rebuild. Never overwrite without asking.

### Where subtitles go

Decide from the slot info in `list_layouts()` and each slide's `list_slide_items()`.

1. **Cover**-role slide: if the body placeholder is shown, put the `##` line into it with `set_body` (on the Basic White / ベーシックホワイト and Portfolio Blue covers, the body placeholder sits where the subtitle goes).
2. **Other** slides: if there's an extra text slot right below the title (`text_slot_empty` or `text_slot_sample`), put it there with `set_text_item`.
3. If neither exists, include it in `set_body` as the first body line (before any bullets).
4. On slides with no `##`, if sample text remains (`text_slot_sample`, e.g. "Subtitle" / "サブタイトル", "Title Text" / "タイトルテキスト"), remove it with `delete_item`. Sample text is visible on the slide, so never leave it.

### Resolving the mode

Per-slide `<!-- mode: ... -->` > chat instruction > settings `mode` > default `generate`.

### verbatim slides

- Use the text exactly as written. Don't paraphrase, summarize, or shorten.
- Don't rewrite text that exceeds `text_rules`; just mention it briefly in the final report.

### generate slides

Treat every written line (headings, bullets, free-form notes) as material for that slide, and write its title and body.

- Keep one slide per slide. Don't add, delete, split, or reorder. If the material doesn't fit on one slide, narrow it to the key points and mention it in the final report.
- If there's a `# Heading`, treat it as the slide's topic; you may adjust it to fit `text_rules`. If not, write a title from the material.
- Strictly follow `text_rules` and `layout_policy`, and match the topic, audience, and tone in `request`.
- Don't change `<!-- layout: ... -->` or `![alt](path)`. If no layout is given, decide it from the written text via "Inferring layouts".
- Don't invent facts (numbers, company names, examples, etc.) that aren't in the material. Where content is missing, insert a placeholder like `[TODO: add example]` and list those slides in the final report.
- **When only a title is written**:
  - If the role is `section` / `title-only` / `cover` (or the layout hides the body), leave the body empty.
  - If the layout shows a body, write one from the title, `request`, and the surrounding slides. Keep to general statements, and use `[TODO: add …]` where facts are needed. Never leave the body empty.
  - With no layout given, decide the role from its position in the deck and the surrounding content (`section` at a chapter break, otherwise `body`).

### When there are no slides

Regardless of mode, plan every slide's title, subtitle, body, and layout from `request` (or the chat request if blank).
Strictly follow `text_rules`, choose layouts per `layout_policy`, and place `assets` images on suitable slides.

### Applying settings policies

- `color` and `assets` apply as policies even when slides are written.
- Place `assets` images on suitable slides only if no `![alt](path)` in the slides already places them.

### Resolving layouts

Interpret the `<!-- layout: ... -->` value in this order:

1. `#number` → use as `layout_index` directly.
2. Exact match with a name from `list_layouts()` → that layout (if several share the name, the first index; tell them apart by `fixed layout text` etc., and mention it in the report if needed).
3. Role name → choose via "Mapping roles to layouts" below.
4. Otherwise, treat it as the closest role and mention the substitution in the final report.

### Mapping roles to layouts

From the slot info (title/body shown, extra text slots, image placeholders) and names returned by `list_layouts()`, build a role→index map once per theme and reuse it for the session.
Layout names depend on Keynote's language, so match both English and Japanese names.

| Role | Guideline |
|---|---|
| cover | The first layout, or a name containing "Title" / 「タイトル」「表紙」, with title and body (subtitle) shown and no image placeholder |
| section | Title shown, body hidden, large title (names like "Section" / 「セクション」「中間の表紙」) |
| body | Title shown, body shown, no image placeholder (names like "Bullets" / 「箇条書き」「本文」). If several match, prefer one with an extra text slot for a subtitle |
| body+image | Title shown, body shown, image placeholder present |
| image | Title shown, image placeholder present, no or small body (names like "Photo" / 「画像」「写真」) |
| title-only | Title shown, body hidden, title placed at the top |
| quote | Name contains "Quote" / "Statement" / 「引用」「ステートメント」 |
| blank | Title and body hidden, no image placeholder (names like "Blank" / 「空白」) |

For a role with no match, pick the closest and mention it in the final report (e.g. Portfolio Blue has no `body+image`, so place the image on a `body` layout).

### Inferring layouts

For slides with no `<!-- layout: ... -->`, infer the role from the content and map it to an actual layout using the table above.

- First slide with only a title + subtitle (no bullets or images) → `cover`
- Title only (no subtitle, body, or image), not the cover → `section` (`body` if generate will write a body)
- Title + bullets → `body`
- Title + image + bullets → `body+image`
- Title + image only (no bullets) → `image`
