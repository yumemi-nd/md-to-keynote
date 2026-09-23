---
# Copy this file into your project folder, edit it,
# then ask Claude: "Build a Keynote deck from this slides.md".
# See slides-guide.md in the same folder for the full syntax.
#
# Write each setting on one line as `key: value`.

# mode sets how slides are generated.
#   generate … Claude writes each slide's text from what you wrote
#   verbatim … your text goes onto the slides as written
# To change only one slide, put e.g. <!-- mode: verbatim --> at the top of that slide.
mode: generate

# One Keynote theme name, as shown in your Keynote's language
# (e.g. Basic White / ベーシックホワイト). Your own themes work too.
theme: Basic White

# The .key file to save: a path relative to slides.md, or one starting with /Users/….
# If blank, it's saved next to slides.md, named after the cover title.
# If a file with the same name exists, Claude asks whether to update or rebuild it.
output: presentation.key

# Which layouts to use on which slides, or "auto-select based on content".
layout_policy: auto-select based on content

# Rules for the generated text.
# e.g. titles under 30 characters; bullets one line each, max 10
text_rules: titles under 30 characters; bullets one line each, max 10

# Paths to images or logos on your Mac, or "none".
assets: none

# Accent color name or HEX code, or "theme default".
color: theme default

# What you want Claude to write (topic, audience, tone, slide count, etc.).
# To build the deck from request alone, delete everything after the `---` below.
request:
---

# Main title here
## Subtitle here (a one-liner for the cover)

---
<!-- layout: body -->
<!-- mode: verbatim -->

# Title
## Subtitle (delete this line if not needed)
- This slide uses exactly what you wrote

---

# Keynote themes make decks efficient and beautiful
- Claude writes the content of this slide
- Letting Claude write saves time
- Using the theme keeps the design consistent
- You can also reapply the theme's styles to a slide

---

# In generate, key points get you the result you want
- Write key points as bullets, and Claude writes the text from them
- With only a title, Claude writes the body from the surrounding slides and request
- Layouts can be given as roles: cover, section, body, body+image, image, etc.

---
<!-- layout: section -->

# Next Section

---
# Slide with an Image
![Image description](/Users/yourname/Pictures/example.png)
- Supporting text
