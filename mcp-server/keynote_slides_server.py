# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp<2.0.0"]
# ///
"""
Keynote MCP (md-to-keynote-mcp): a minimal Keynote MCP server that drives the theme's REAL
title/body placeholders (default title item / default body item) instead of
freeform text boxes, so slides inherit the theme's registered font sizes,
colors, and bullet styles automatically.

macOS + Keynote.app only (drives Keynote via AppleScript/osascript).
"""
import json
import os
import subprocess
import tempfile
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("md-to-keynote-mcp")

RS = "\x1e"
FS = "\x1f"
SLIDE_NUMBER_CHAR = "\ufffc"

# AppleScript handlers shared by every tool that inspects a slide's items.
# describeSlide emits one header record and one record per iWork item, using
# ASCII 30/31 as record/field separators because object text can contain tabs
# and newlines. An item counts as "sample" when the slide's layout has a text
# item with the same position and the same text, i.e. the layout's own
# example text (e.g. "Subtitle" / "サブタイトル") copied onto the slide and still visible.
DESCRIBE_HANDLERS = r'''
on fmtNum(v)
    return ((round v) as integer) as string
end fmtNum

on describeSlide(s)
    set RS to character id 30
    set FS to character id 31
    tell application "Keynote"
        set sampleKeys to {}
        try
            set mts to text items of base layout of s
            repeat with k from 1 to count of mts
                set mt to item k of mts
                set p to position of mt
                set end of sampleKeys to (my fmtNum(item 1 of p)) & "," & (my fmtNum(item 2 of p)) & "|" & (object text of mt as string)
            end repeat
        end try
        set out to "slide" & FS & (slide number of s) & FS & (name of base layout of s) & FS & (title showing of s) & FS & (body showing of s) & RS
        set n to count of iWork items of s
        repeat with i from 1 to n
            set t to iWork item i of s
            set cl to class of t as string
            set txt to ""
            try
                set txt to object text of t as string
            end try
            set isTitle to false
            set isBody to false
            try
                if t is equal to default title item of s then set isTitle to true
            end try
            try
                if t is equal to default body item of s then set isBody to true
            end try
            set p to position of t
            set k to (my fmtNum(item 1 of p)) & "," & (my fmtNum(item 2 of p)) & "|" & txt
            set isSample to (txt is not "") and (sampleKeys contains {k})
            set out to out & "item" & FS & i & FS & cl & FS & isTitle & FS & isBody & FS & (my fmtNum(item 1 of p)) & FS & (my fmtNum(item 2 of p)) & FS & (my fmtNum(width of t)) & FS & (my fmtNum(height of t)) & FS & isSample & FS & txt & RS
        end repeat
    end tell
    return out
end describeSlide
'''


# Text this server last wrote into the front document, per slide:
# {"<slide number>": {"title": str, "body": str, "items": {"<item index>": str}}}.
# Saved next to the .key as a hidden JSON file whenever the deck is saved, so a
# later update can tell text the user edited in Keynote apart from text we wrote.
_doc_path: Optional[str] = None
_record: dict = {}


def record_file(key_path: str) -> str:
    folder, name = os.path.split(os.path.realpath(key_path))
    return os.path.join(folder, f".{name}.md-to-keynote.json")


def load_record(key_path: str) -> None:
    global _doc_path, _record
    _doc_path = os.path.realpath(key_path)
    try:
        with open(record_file(key_path), encoding="utf-8") as f:
            _record = json.load(f).get("slides", {})
    except (OSError, ValueError):
        _record = {}


def save_record() -> None:
    if not _doc_path:
        return
    with open(record_file(_doc_path), "w", encoding="utf-8") as f:
        json.dump({"slides": _record}, f, ensure_ascii=False, indent=1)


def remember(slide_number: int, field: str, text: str) -> None:
    entry = _record.setdefault(str(slide_number), {"items": {}})
    if field in ("title", "body"):
        entry[field] = text
    else:
        entry.setdefault("items", {})[field] = text


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip()


def split_readback(result: str) -> tuple[str, str]:
    """Split a '<STATUS><FS><text><RS>' AppleScript result into (status, text)."""
    status, _, rest = result.partition(FS)
    return status, rest[:rest.rfind(RS)] if RS in rest else rest


def run_applescript(script: str) -> str:
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "AppleScript failed")
    return result.stdout.rstrip("\n")


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def parse_records(raw: str) -> list[list[str]]:
    return [rec.split(FS) for rec in raw.split(RS) if rec.strip("\n")]


def parse_slide(records: list[list[str]]) -> dict:
    """Turn describeSlide records (one header + its items) into a dict."""
    head = records[0]
    slide = {
        "number": int(head[1]),
        "layout": head[2],
        "title_showing": head[3] == "true",
        "body_showing": head[4] == "true",
        "items": [],
    }
    for rec in records[1:]:
        _, idx, cls, is_title, is_body, x, y, w, h, is_sample, *rest = rec
        text = FS.join(rest)
        if is_title == "true":
            role = "title"
        elif is_body == "true":
            role = "body"
        elif text.strip() == SLIDE_NUMBER_CHAR:
            role = "slide_number"
        elif cls == "image":
            role = "image"
        elif cls in ("shape", "text item"):
            if is_sample == "true":
                role = "text_slot_sample"
            elif text == "":
                role = "text_slot_empty"
            else:
                role = "text"
        else:
            role = cls
        slide["items"].append({
            "index": int(idx), "class": cls, "role": role, "text": text,
            "x": int(x), "y": int(y), "w": int(w), "h": int(h),
        })
    return slide


def describe_slide(slide_number: int) -> dict:
    raw = run_applescript(DESCRIBE_HANDLERS + f'''
    tell application "Keynote"
        return my describeSlide(slide {slide_number} of front document)
    end tell
    ''')
    return parse_slide(parse_records(raw))


def describe_all_slides() -> list[dict]:
    raw = run_applescript(DESCRIBE_HANDLERS + '''
    tell application "Keynote"
        set out to ""
        repeat with s in slides of front document
            set out to out & my describeSlide(s)
        end repeat
        return out
    end tell
    ''')
    groups: list[list[list[str]]] = []
    for rec in parse_records(raw):
        if rec[0] == "slide":
            groups.append([rec])
        else:
            groups[-1].append(rec)
    return [parse_slide(g) for g in groups]


def current_texts(s: dict) -> dict:
    """The slide's current text in the same shape as a _record entry."""
    out = {"items": {}}
    for it in s["items"]:
        if it["role"] in ("title", "body"):
            out[it["role"]] = it["text"]
        else:
            out["items"][str(it["index"])] = it["text"]
    return out


def preview(text: str, limit: int = 40) -> str:
    one_line = text.replace("\n", " / ")
    return one_line if len(one_line) <= limit else one_line[:limit] + "…"


def format_item(it: dict) -> str:
    geo = f"x={it['x']} y={it['y']} w={it['w']} h={it['h']}"
    role = it["role"]
    if role == "text_slot_sample":
        note = f'layout sample text "{preview(it["text"])}" (VISIBLE on the slide until replaced with set_text_item or removed with delete_item)'
    elif role == "text_slot_empty":
        note = "empty text slot (e.g. subtitle) — fill with set_text_item"
    elif role == "slide_number":
        note = "slide number (automatic)"
    elif role in ("title", "body", "text"):
        note = f'text="{preview(it["text"])}"'
    else:
        note = ""
    return f"[{it['index']}] {role} ({it['class']}) {geo} {note}".rstrip()


def master_names() -> list[str]:
    raw = run_applescript(f'''
    tell application "Keynote"
        set out to ""
        repeat with m in master slides of front document
            set out to out & (name of m) & (character id 30)
        end repeat
        return out
    end tell
    ''')
    return [n for n in raw.split(RS) if n]


def resolve_layout(layout: str, layout_index: int) -> tuple[str, str]:
    """Return (AppleScript master slide reference, human note) for a layout given by name or 1-based index."""
    names = master_names()
    if layout_index:
        if not 1 <= layout_index <= len(names):
            raise ValueError(f"layout_index {layout_index} is out of range (1-{len(names)}). Call list_layouts().")
        return f"master slide {layout_index}", f"#{layout_index} {names[layout_index - 1]}"
    matches = [i + 1 for i, n in enumerate(names) if n == layout]
    if not matches:
        raise ValueError(f"No layout named '{layout}'. Available: " + ", ".join(f"#{i + 1} {n}" for i, n in enumerate(names)))
    note = f"#{matches[0]} {layout}"
    if len(matches) > 1:
        note += f" (note: {len(matches)} layouts share this name: " + ", ".join(f"#{m}" for m in matches) + "; pass layout_index to pick another)"
    return f"master slide {matches[0]}", note


def slides_summary() -> str:
    raw = run_applescript(f'''
    set RS to character id 30
    set FS to character id 31
    tell application "Keynote"
        tell front document
            set out to (name as string) & RS
            repeat with s in slides
                set tt to ""
                try
                    set tt to object text of default title item of s as string
                end try
                set out to out & (slide number of s) & FS & (name of base layout of s) & FS & (skipped of s) & FS & (title showing of s) & FS & tt & RS
            end repeat
            return out
        end tell
    end tell
    ''')
    recs = parse_records(raw)
    lines = [f"Document: {recs[0][0]} — {len(recs) - 1} slide(s)"]
    for num, layout, skipped, title_showing, *title in recs[1:]:
        title_text = preview(FS.join(title)) if title_showing == "true" else "(title hidden)"
        flag = " [skipped]" if skipped == "true" else ""
        lines.append(f"{num}: [{layout}] {title_text}{flag}")
    return "\n".join(lines)


def check_target_path(path: str, overwrite: bool) -> None:
    if not path.endswith(".key"):
        raise ValueError(f"path must end with .key: {path}")
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        raise ValueError(f"Folder does not exist: {parent}")
    if os.path.exists(path) and not overwrite:
        raise FileExistsError(
            f"{path} already exists. Ask the user whether to UPDATE it (open_presentation, keeps their manual edits) "
            f"or REBUILD it from scratch (call again with overwrite=true)."
        )


def close_documents_at(path: str) -> None:
    """Close (without saving) any open Keynote document backed by `path`, so it can be replaced."""
    run_applescript(f'''
    tell application "Keynote"
        repeat with d in (documents as list)
            try
                if POSIX path of (file of d as alias) is "{esc(os.path.realpath(path))}" then close d saving no
            end try
        end repeat
    end tell
    ''')


@mcp.tool()
def create_presentation(title: str, theme: str = "", path: str = "", overwrite: bool = False) -> str:
    """Create a new Keynote presentation. `theme` should match a theme name exactly as shown in Keynote's theme chooser (e.g. 'Basic White' / 'ベーシックホワイト'). `path` (recommended): an absolute POSIX path ending in .key — if given, the presentation is saved there immediately. If a file already exists at `path` this FAILS unless `overwrite=true`; ask the user first whether to update the existing file with open_presentation instead. NOTE: Keynote creates slide 1 automatically — use it for the first slide instead of calling add_slide."""
    if path:
        check_target_path(path, overwrite)
        if overwrite and os.path.exists(path):
            close_documents_at(path)
    props = f' with properties {{document theme:theme "{esc(theme)}"}}' if theme else ""
    layout = run_applescript(f'''
    tell application "Keynote"
        activate
        set newDoc to make new document{props}
        return name of base layout of slide 1 of newDoc
    end tell
    ''')
    global _doc_path, _record
    _doc_path, _record = None, {"1": {"items": {}}}
    msg = f"Created presentation '{title}'" + (f" with theme '{theme}'" if theme else "")
    if path:
        run_applescript(f'''
        tell application "Keynote"
            save front document in POSIX file "{esc(path)}"
        end tell
        ''')
        _doc_path = os.path.realpath(path)
        save_record()
        msg += f", saved to {path}" + (" (replaced the existing file)" if overwrite else "")
    msg += (f". Slide 1 already exists (layout: {layout}) — fill it with set_title/set_body instead of add_slide, "
            f"and change its layout with set_slide_layout if needed. The next add_slide creates slide 2.")
    return msg


@mcp.tool()
def open_presentation(path: str) -> str:
    """Open an existing .key file (absolute POSIX path) and make it the front document, so later tools update it in place instead of rebuilding from the theme. Returns every slide's number, layout, and title. Before changing any text, call find_text_edits to see which text the user rewrote in Keynote."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"No such file: {path}")
    run_applescript(f'''
    tell application "Keynote"
        activate
        open POSIX file "{esc(path)}"
    end tell
    ''')
    load_record(path)
    return "Opened " + path + "\n" + slides_summary()


@mcp.tool()
def list_slides() -> str:
    """List every slide in the front document: number, layout name, and title text (or '(title hidden)')."""
    return slides_summary()


@mcp.tool()
def list_layouts(detail: bool = True) -> str:
    """List the theme's layouts (master slides) with their 1-based index. With detail=true (default) each layout also reports whether its title and body placeholders are shown or hidden, its extra text slots (e.g. a subtitle — empty, or pre-filled with the layout's sample text such as 'Subtitle' / 'サブタイトル' that stays VISIBLE until replaced), its image placeholders, and any fixed text the layout itself draws (e.g. a footer — often the only difference between same-named layouts). Layouts can share a name; use the index with add_slide/set_slide_layout's `layout_index` to pick an exact one. detail=true briefly adds and removes a temporary slide per layout (a few seconds); cache the result per theme."""
    if not detail:
        return "\n".join(f"#{i + 1} {n}" for i, n in enumerate(master_names()))
    raw = run_applescript(DESCRIBE_HANDLERS + '''
    tell application "Keynote"
        tell front document
            set startCount to count of slides
            set out to ""
            try
                repeat with i from 1 to count of master slides
                    set m to master slide i
                    set s to make new slide at end with properties {base layout:m}
                    set out to out & my describeSlide(s)
                    delete s
                    set mts to text items of m
                    repeat with k from 1 to count of mts
                        set mt to item k of mts
                        set isPH to false
                        try
                            if mt is equal to default title item of m then set isPH to true
                        end try
                        try
                            if mt is equal to default body item of m then set isPH to true
                        end try
                        set out to out & "mtext" & (character id 31) & isPH & (character id 31) & (object text of mt as string) & (character id 30)
                    end repeat
                end repeat
            on error errMsg
                repeat while (count of slides) > startCount
                    delete last slide
                end repeat
                error errMsg
            end try
            return out
        end tell
    end tell
    ''')
    recs = parse_records(raw)
    groups: list[list[list[str]]] = []
    master_texts: list[list[tuple[bool, str]]] = []
    for rec in recs:
        if rec[0] == "slide":
            groups.append([rec])
            master_texts.append([])
        elif rec[0] == "mtext":
            master_texts[-1].append((rec[1] == "true", FS.join(rec[2:])))
        else:
            groups[-1].append(rec)
    names = [parse_slide(g)["layout"] for g in groups]
    lines = []
    for i, group in enumerate(groups, start=1):
        s = parse_slide(group)
        placeholder_texts = {t for is_ph, t in master_texts[i - 1] if is_ph}
        slide_texts = {it["text"] for it in s["items"]}
        fixed = []
        for is_ph, t in master_texts[i - 1]:
            if is_ph or t in placeholder_texts or t in slide_texts or not t.strip() or t.strip() == SLIDE_NUMBER_CHAR:
                continue
            if t not in fixed:
                fixed.append(t)
        slots = [it for it in s["items"] if it["role"] in ("text_slot_sample", "text_slot_empty", "text")]
        images = [it for it in s["items"] if it["role"] == "image"]
        slot_desc = ", ".join(
            f'"{preview(it["text"], 20)}" sample at y={it["y"]}' if it["role"] != "text_slot_empty" else f"empty at y={it['y']}"
            for it in slots
        )
        dup = [j for j, n in enumerate(names, start=1) if n == s["layout"] and j != i]
        parts = [
            f"#{i} {s['layout']}",
            f"title: {'shown' if s['title_showing'] else 'HIDDEN'}",
            f"body: {'shown' if s['body_showing'] else 'HIDDEN'}",
            f"extra text slots: {len(slots)}" + (f" ({slot_desc})" if slots else ""),
            f"image placeholders: {len(images)}",
        ]
        if fixed:
            parts.append("fixed layout text: " + ", ".join(f'"{preview(t, 30)}"' for t in fixed))
        if dup:
            parts.append("same name as " + ", ".join(f"#{j}" for j in dup))
        lines.append(" | ".join(parts))
    return "\n".join(lines)


@mcp.tool()
def add_slide(layout: str = "", layout_index: int = 0) -> str:
    """Add a new slide at the end of the presentation. Pick the layout by `layout_index` (1-based index from list_layouts — exact, even when names repeat) or by `layout` name (the first layout with that name); leave both blank for the theme's default layout."""
    if layout or layout_index:
        ref, note = resolve_layout(layout, layout_index)
        props = f" with properties {{base layout:{ref}}}"
    else:
        props, note = "", "default"
    out = run_applescript(f'''
    tell application "Keynote"
        tell front document
            make new slide at end{props}
            return (count of slides) as string
        end tell
    end tell
    ''')
    _record.setdefault(out, {"items": {}})
    return f"Added slide #{out} (layout: {note})"


def set_placeholder(slide_number: int, which: str, text: str, show: bool) -> str:
    showing = f"{which} showing"
    item = f"default {which} item"
    result = run_applescript(f'''
    tell application "Keynote"
        tell slide {slide_number} of front document
            if not ({showing}) then
                if {"true" if show else "false"} then
                    set {showing} to true
                else
                    return "HIDDEN" & (character id 31) & (name of base layout)
                end if
            end if
            set newText to "{esc(text)}"
            considering case
                set isSame to ((object text of {item}) as string) is newText
            end considering
            if isSame then return "SAME" & (character id 31) & newText & (character id 30)
            set object text of {item} to newText
            return "OK" & (character id 31) & ((object text of {item}) as string) & (character id 30)
        end tell
    end tell
    ''')
    if result.startswith("HIDDEN"):
        layout = result.split(FS, 1)[1]
        return (f"NOT WRITTEN: the {which} placeholder is hidden on slide {slide_number} (layout: {layout}), so the text would not appear. "
                f"Call again with show=true to turn the {which} on, or change the layout with set_slide_layout.")
    status, written = split_readback(result)
    remember(slide_number, which, written)
    if status == "SAME":
        return f"The {which} on slide {slide_number} already has this text; left it untouched (keeps any formatting the user applied)"
    return f"Set {which} on slide {slide_number}" + (" (turned it on)" if show else "")


@mcp.tool()
def set_title(slide_number: int, text: str, show: bool = False) -> str:
    """Set the slide's REAL title placeholder text. Inherits the theme's registered title font/size/color automatically — do not set font size manually. If the layout hides the title, nothing is written and the result says so; pass show=true to turn the title on and write it."""
    return set_placeholder(slide_number, "title", text, show)


@mcp.tool()
def set_body(slide_number: int, text: str, show: bool = False) -> str:
    """Set the slide's REAL body/bullet placeholder text. Pass items separated by newlines (\\n); Keynote applies the theme's bullet style automatically. Inherits the theme's registered body font/size/color — do not set font size manually. If the layout hides the body, nothing is written and the result says so; pass show=true to turn the body on and write it."""
    return set_placeholder(slide_number, "body", text, show)


@mcp.tool()
def list_slide_items(slide_number: int) -> str:
    """List every item on a slide with its 1-based item index, role, position, and size. Roles: title / body (the real placeholders — use set_title/set_body), text_slot_empty (an empty text slot such as a subtitle), text_slot_sample (a slot still holding the layout's sample text like 'Subtitle' / 'サブタイトル', which IS visible on the slide), text, image, slide_number. Also reports whether the layout's title/body are shown or hidden. Use the index with set_text_item, set_item_geometry, and delete_item; re-list after adding or deleting items because indexes shift."""
    s = describe_slide(slide_number)
    head = (f"Slide {s['number']} (layout: {s['layout']}) — title: {'shown' if s['title_showing'] else 'HIDDEN'}, "
            f"body: {'shown' if s['body_showing'] else 'HIDDEN'}")
    return "\n".join([head] + [format_item(it) for it in s["items"]])


@mcp.tool()
def set_text_item(slide_number: int, item_index: int, text: str) -> str:
    """Set the text of any text slot on a slide by its item index from list_slide_items — e.g. the subtitle slot (text_slot_empty or text_slot_sample). Refuses the title and body placeholders (use set_title/set_body) so a subtitle can't overwrite the title by accident. Text inherits the slot's theme style."""
    result = run_applescript(f'''
    tell application "Keynote"
        tell slide {slide_number} of front document
            set t to iWork item {item_index}
            try
                if t is equal to default title item then return "TITLE"
            end try
            try
                if t is equal to default body item then return "BODY"
            end try
            set cl to class of t as string
            if cl is not "shape" and cl is not "text item" then return "CLASS" & (character id 31) & cl
            set newText to "{esc(text)}"
            considering case
                set isSame to ((object text of t) as string) is newText
            end considering
            if isSame then return "SAME" & (character id 31) & newText & (character id 30)
            set object text of t to newText
            return "OK" & (character id 31) & ((object text of t) as string) & (character id 30)
        end tell
    end tell
    ''')
    if result == "TITLE":
        return f"NOT WRITTEN: item {item_index} on slide {slide_number} is the title placeholder. Use set_title for the title; call list_slide_items to find the subtitle slot."
    if result == "BODY":
        return f"NOT WRITTEN: item {item_index} on slide {slide_number} is the body placeholder. Use set_body instead."
    if result.startswith("CLASS"):
        return f"NOT WRITTEN: item {item_index} on slide {slide_number} is a {result.split(FS, 1)[1]}, which has no text."
    status, written = split_readback(result)
    remember(slide_number, str(item_index), written)
    if status == "SAME":
        return f"Item {item_index} on slide {slide_number} already has this text; left it untouched (keeps any formatting the user applied)"
    return f"Set text of item {item_index} on slide {slide_number}"


@mcp.tool()
def add_image(slide_number: int, image_path: str, x: Optional[float] = None, y: Optional[float] = None,
              width: Optional[float] = None, height: Optional[float] = None) -> str:
    """Place an image file (by absolute POSIX path) onto a slide. Without x/y/width/height it uses Keynote's default placement; pass any of them to position/size it right away (points, origin top-left; setting only width or height keeps the aspect ratio). Returns the image's item index and geometry, and warns if it overlaps the title, body, or other text so you can fix it with set_item_geometry."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"No such image: {image_path}")
    idx = run_applescript(f'''
    tell application "Keynote"
        tell slide {slide_number} of front document
            set img to make new image with properties {{file:POSIX file "{esc(image_path)}"}}
            repeat with i from 1 to count of iWork items
                if iWork item i is equal to img then return i as string
            end repeat
            return (count of iWork items) as string
        end tell
    end tell
    ''')
    if any(v is not None for v in (x, y, width, height)):
        apply_geometry(slide_number, int(idx), x, y, width, height)
    return report_item(slide_number, int(idx), "Added image")


def apply_geometry(slide_number: int, item_index: int, x, y, width, height) -> None:
    lines = []
    if width is not None:
        lines.append(f"set width of t to {width}")
    if height is not None:
        lines.append(f"set height of t to {height}")
    if x is not None or y is not None:
        px = "item 1 of p" if x is None else str(x)
        py = "item 2 of p" if y is None else str(y)
        lines.append(f"set p to position of t\nset position of t to {{{px}, {py}}}")
    body = "\n".join(lines)
    run_applescript(f'''
    tell application "Keynote"
        tell slide {slide_number} of front document
            set t to iWork item {item_index}
            {body}
        end tell
    end tell
    ''')


def overlaps(a: dict, b: dict) -> bool:
    return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]


def report_item(slide_number: int, item_index: int, verb: str) -> str:
    s = describe_slide(slide_number)
    target = next(it for it in s["items"] if it["index"] == item_index)
    msg = f"{verb} on slide {slide_number}: " + format_item(target)
    hits = [it for it in s["items"]
            if it["index"] != item_index and it["role"] in ("title", "body", "text", "text_slot_sample")
            and it["text"].strip() and overlaps(target, it)]
    if hits:
        msg += "\nWARNING: overlaps " + "; ".join(format_item(it) for it in hits)
    return msg


@mcp.tool()
def set_item_geometry(slide_number: int, item_index: int, x: Optional[float] = None, y: Optional[float] = None,
                      width: Optional[float] = None, height: Optional[float] = None) -> str:
    """Move and/or resize an item (image, text slot, placeholder) by its index from list_slide_items. Only the values you pass change; units are points with the origin at the slide's top-left. Images keep their aspect ratio, so setting width may also change height. Returns the new geometry and warns about overlaps with text."""
    apply_geometry(slide_number, item_index, x, y, width, height)
    return report_item(slide_number, item_index, "Updated item")


@mcp.tool()
def delete_item(slide_number: int, item_index: int) -> str:
    """Delete an item from a slide by its index from list_slide_items (e.g. a misplaced image, or a layout sample text such as 'Subtitle' / 'サブタイトル' you don't want). For the title or body placeholder this hides it (title/body showing = off) instead of deleting it. Layout-provided slots of class 'shape' are emptied instead of deleted, because Keynote deletes the title along with them; an empty slot doesn't show on the slide. Indexes of later items shift after a real deletion."""
    result = run_applescript(f'''
    tell application "Keynote"
        tell slide {slide_number} of front document
            set t to iWork item {item_index}
            try
                if t is equal to default title item then
                    set title showing to false
                    return "TITLE"
                end if
            end try
            try
                if t is equal to default body item then
                    set body showing to false
                    return "BODY"
                end if
            end try
            if (class of t as string) is "shape" then
                set object text of t to ""
                return "CLEARED"
            end if
            delete t
            return "OK"
        end tell
    end tell
    ''')
    if result == "TITLE":
        return f"Hid the title placeholder on slide {slide_number}"
    if result == "BODY":
        return f"Hid the body placeholder on slide {slide_number}"
    items = _record.get(str(slide_number), {}).get("items", {})
    if result == "CLEARED":
        if str(item_index) in items:
            items[str(item_index)] = ""
        return (f"Cleared the text of item {item_index} on slide {slide_number} instead of deleting it: "
                f"Keynote removes the title together with layout-provided shape slots, so the empty slot is left in place (it doesn't show on the slide).")
    for k in sorted(int(k) for k in items):
        if k == item_index:
            del items[str(k)]
        elif k > item_index:
            items[str(k - 1)] = items.pop(str(k))
    return f"Deleted item {item_index} from slide {slide_number}"


@mcp.tool()
def delete_slide(slide_number: int) -> str:
    """Delete a slide. Later slides move up by one number."""
    out = run_applescript(f'''
    tell application "Keynote"
        tell front document
            delete slide {slide_number}
            return (count of slides) as string
        end tell
    end tell
    ''')
    for k in sorted(int(k) for k in _record):
        if k == slide_number:
            del _record[str(k)]
        elif k > slide_number:
            _record[str(k - 1)] = _record.pop(str(k))
    return f"Deleted slide {slide_number}; the deck now has {out} slide(s)"


@mcp.tool()
def set_slide_layout(slide_number: int, layout: str = "", layout_index: int = 0) -> str:
    """Change an existing slide's layout, by `layout_index` (exact, from list_layouts) or `layout` name. Title/body text is kept; check the result with list_slide_items, since the new layout may add sample text slots or hide the body."""
    ref, note = resolve_layout(layout, layout_index)
    run_applescript(f'''
    tell application "Keynote"
        tell front document
            set base layout of slide {slide_number} to {ref}
        end tell
    end tell
    ''')
    if str(slide_number) in _record:
        _record[str(slide_number)]["items"] = {}
    return f"Slide {slide_number} now uses layout {note}"


def field_label(field: str) -> str:
    return field if field in ("title", "body") else f"text item {field}"


@mcp.tool()
def find_text_edits() -> str:
    """Compare the front document's current text with the text this server last wrote into it (recorded when the deck was built or updated), and report every title, body, and text slot (e.g. subtitle) the user rewrote in Keynote since then, with both versions in full. Call this after open_presentation and BEFORE changing any text in an update, then ask the user, per edited slide, whether to keep their Keynote text or overwrite it with slides.md. Also reports slides that this server never wrote (e.g. added in Keynote) and recorded slides that no longer exist."""
    if not _record:
        return ("NO RECORD: there is no record of the text this plugin wrote into this deck (it was built before edit tracking, "
                "or its record file was removed), so text edited in Keynote can't be told apart from slides.md changes.")
    slides = describe_all_slides()
    edits, unrecorded = [], []
    for s in slides:
        wrote = _record.get(str(s["number"]))
        if wrote is None:
            unrecorded.append(s["number"])
            continue
        now = current_texts(s)
        fields = [f for f in ("title", "body") if f in wrote] + list(wrote.get("items", {}))
        for f in fields:
            before = wrote[f] if f in ("title", "body") else wrote["items"][f]
            after = now.get(f) if f in ("title", "body") else now["items"].get(f)
            if after is None:
                edits.append(f"Slide {s['number']} {field_label(f)}: REMOVED in Keynote\n  wrote: {before!r}")
            elif normalize(after) != normalize(before):
                edits.append(f"Slide {s['number']} {field_label(f)}: EDITED in Keynote\n  wrote: {before!r}\n  now:   {after!r}")
    missing = sorted(int(k) for k in _record if int(k) > len(slides))
    lines = [f"{len(edits)} text edit(s) made in Keynote since this plugin last wrote the deck." if edits
             else "No text was edited in Keynote since this plugin last wrote the deck."]
    lines += edits
    if unrecorded:
        lines.append("Slides this plugin never wrote (probably added in Keynote): " + ", ".join(map(str, unrecorded)))
    if missing:
        lines.append(f"The record covers slides up to {max(missing)} but the deck has only {len(slides)} (slides deleted in Keynote?)")
    if unrecorded or missing:
        lines.append("Slides may have been added, deleted, or reordered in Keynote, so slides.md slide N may no longer match deck slide N — confirm the mapping with the user before writing.")
    return "\n".join(lines)


@mcp.tool()
def accept_text_edits(slide_number: int = 0) -> str:
    """Record the slide's current text (all slides when slide_number=0) as what the plugin last wrote, so text the user chose to KEEP isn't reported by find_text_edits again. Doesn't change the slide. Takes effect on disk at the next save_presentation."""
    slides = describe_all_slides() if slide_number == 0 else [describe_slide(slide_number)]
    for s in slides:
        wrote = _record.get(str(s["number"]))
        if wrote is None:
            continue
        now = current_texts(s)
        for f in ("title", "body"):
            if f in wrote and f in now:
                wrote[f] = now[f]
        items = wrote.get("items", {})
        for f in list(items):
            if f in now["items"]:
                items[f] = now["items"][f]
            else:
                del items[f]
    target = "every slide" if slide_number == 0 else f"slide {slide_number}"
    return f"Accepted the current text of {target} as the baseline for find_text_edits"


@mcp.tool()
def get_slide_count() -> int:
    """Return the number of slides in the front document."""
    return int(run_applescript('tell application "Keynote" to return (count of slides of front document) as string'))


@mcp.tool()
def save_presentation() -> str:
    """Save the front presentation in place, to whatever path it's currently bound to (from create_presentation's `path`, open_presentation, or a prior save_as). Call this after every few slides, not just once at the end, so the file on disk stays current."""
    run_applescript('tell application "Keynote" to save front document')
    save_record()
    return "Saved"


@mcp.tool()
def save_as(path: str, overwrite: bool = False) -> str:
    """Save the front presentation as a .key file at the given absolute POSIX path. Fails if a file already exists there unless overwrite=true. Prefer passing `path` to create_presentation instead so the document is file-backed from the start; use this only to change the save location later."""
    check_target_path(path, overwrite)
    run_applescript(f'''
    tell application "Keynote"
        save front document in POSIX file "{esc(path)}"
    end tell
    ''')
    global _doc_path
    _doc_path = os.path.realpath(path)
    save_record()
    return f"Saved to {path}"


@mcp.tool()
def export_pdf(path: str) -> str:
    """Export the front presentation as a single PDF to the given absolute POSIX path. Note: PDF export has been unreliable for visual verification in some environments (pages sometimes render blank when read back) — prefer export_slide_images for checking layout."""
    script = f'''
    tell application "Keynote"
        export front document to POSIX file "{esc(path)}" as PDF
    end tell
    '''
    run_applescript(script)
    return f"Exported PDF to {path}"


@mcp.tool()
def export_slide_images(folder_path: str = "") -> str:
    """Export every slide as a separate image for visual verification and return the absolute path of each file, in slide order. Leave `folder_path` blank to export into a fresh folder in the system temp directory (nothing to clean up in the project folder). Read back only the slides you need to check, not every file, to save tokens."""
    folder = folder_path or tempfile.mkdtemp(prefix="keynote-verify-")
    os.makedirs(folder, exist_ok=True)
    before = set(os.listdir(folder))
    run_applescript(f'''
    tell application "Keynote"
        export front document to POSIX file "{esc(folder)}" as slide images
    end tell
    ''')
    files = sorted(f for f in os.listdir(folder) if f not in before and not f.startswith("."))
    lines = [f"Exported {len(files)} image(s) to {folder}"]
    lines += [f"{i}: {os.path.join(folder, f)}" for i, f in enumerate(files, start=1)]
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
