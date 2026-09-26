import asyncio
import json
import os

import pytest

from conftest import FS, RS, item_rec, server, slide_rec

MASTERS = RS.join(["Title", "Title & Bullets", "Title & Bullets", "Blank"]) + RS

# A title slide: title, subtitle slot still showing the layout's sample text, slide number.
TITLE_SLIDE = (slide_rec(1, "Title")
               + item_rec(1, "text item", 100, 200, 800, 120, "Hello", title=True)
               + item_rec(2, "shape", 100, 340, 800, 60, "Subtitle", sample=True)
               + item_rec(3, "text item", 900, 700, 40, 20, server.SLIDE_NUMBER_CHAR))

# A bullets slide: title, body, empty text slot, image overlapping the body.
BULLETS_SLIDE = (slide_rec(2, "Title & Bullets")
                 + item_rec(1, "text item", 50, 40, 900, 100, "Agenda", title=True)
                 + item_rec(2, "text item", 50, 160, 900, 500, "One\nTwo", body=True)
                 + item_rec(3, "shape", 50, 680, 900, 40)
                 + item_rec(4, "image", 600, 300, 300, 200))


def tools():
    return {t.name: t for t in asyncio.run(server.mcp.list_tools())}


# --- annotations -------------------------------------------------------------

def test_every_tool_sets_all_four_hints():
    listed = tools()
    assert len(listed) == 21
    for name, tool in listed.items():
        a = tool.annotations
        assert a is not None, name
        for hint in ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"):
            assert isinstance(getattr(a, hint), bool), f"{name}.{hint}"
        assert a.openWorldHint is False, name
        if a.readOnlyHint:
            assert a.destructiveHint is False and a.idempotentHint is True, name


@pytest.mark.parametrize("name,read_only,destructive,idempotent", [
    ("list_slides", True, False, True),
    ("list_slide_items", True, False, True),
    ("get_slide_count", True, False, True),
    ("find_text_edits", True, False, True),
    ("add_slide", False, False, False),
    ("add_image", False, False, False),
    ("set_title", False, True, True),
    ("set_item_geometry", False, True, True),
    ("delete_slide", False, True, False),
    ("delete_item", False, True, False),
    ("create_presentation", False, True, False),
    ("save_as", False, True, True),
])
def test_hint_values(name, read_only, destructive, idempotent):
    a = tools()[name].annotations
    assert (a.readOnlyHint, a.destructiveHint, a.idempotentHint) == (read_only, destructive, idempotent)


# --- create / open / save ----------------------------------------------------

def test_create_presentation_without_path(osa):
    osa.queue("Title")
    msg = server.create_presentation("Deck", theme="Basic White")
    assert 'document theme:theme "Basic White"' in osa.scripts[0]
    assert "layout: Title" in msg
    assert server._record == {"1": {"items": {}}}


def test_create_presentation_saves_record(osa, tmp_path):
    path = str(tmp_path / "deck.key")
    osa.queue("Title", "")
    msg = server.create_presentation("Deck", path=path)
    assert f"saved to {path}" in msg
    assert os.path.exists(server.record_file(path))


def test_create_presentation_refuses_existing_file(osa, tmp_path):
    path = tmp_path / "deck.key"
    path.write_text("x")
    with pytest.raises(FileExistsError):
        server.create_presentation("Deck", path=str(path))
    with pytest.raises(ValueError):
        server.create_presentation("Deck", path=str(tmp_path / "deck.pptx"))
    assert osa.scripts == []


def test_create_presentation_overwrite_closes_open_copy(osa, tmp_path):
    path = tmp_path / "deck.key"
    path.write_text("x")
    osa.queue("", "Title", "")
    msg = server.create_presentation("Deck", path=str(path), overwrite=True)
    assert "close d saving no" in osa.scripts[0]
    assert "replaced the existing file" in msg


def test_open_presentation_loads_record(osa, tmp_path):
    path = tmp_path / "deck.key"
    path.write_text("x")
    with open(server.record_file(str(path)), "w") as f:
        json.dump({"slides": {"1": {"title": "Hello", "items": {}}}}, f)
    osa.queue("", "deck" + RS + FS.join(["1", "Title", "false", "true", "Hello"]) + RS)
    msg = server.open_presentation(str(path))
    assert "1: [Title] Hello" in msg
    assert server._record == {"1": {"title": "Hello", "items": {}}}


def test_open_presentation_missing_file(osa):
    with pytest.raises(FileNotFoundError):
        server.open_presentation("/no/such/deck.key")


def test_save_presentation_writes_record(osa, tmp_path):
    path = str(tmp_path / "deck.key")
    server._doc_path = path
    server._record = {"1": {"title": "Hi", "items": {}}}
    osa.queue("")
    assert server.save_presentation() == "Saved"
    with open(server.record_file(path)) as f:
        assert json.load(f) == {"slides": {"1": {"title": "Hi", "items": {}}}}


def test_save_as(osa, tmp_path):
    path = str(tmp_path / "copy.key")
    osa.queue("")
    assert server.save_as(path) == f"Saved to {path}"
    assert server._doc_path == os.path.realpath(path)
    (tmp_path / "copy.key").write_text("x")
    with pytest.raises(FileExistsError):
        server.save_as(path)


def test_export_pdf(osa):
    osa.queue("")
    assert server.export_pdf("/tmp/out.pdf") == "Exported PDF to /tmp/out.pdf"
    assert "as PDF" in osa.scripts[0]


def test_export_slide_images(osa, tmp_path):
    (tmp_path / "old.png").write_text("x")

    def export(script):
        for n in (1, 2):
            (tmp_path / f"deck.{n:03}.png").write_text("x")
        return ""

    osa.queue(export)
    msg = server.export_slide_images(str(tmp_path))
    assert msg.splitlines() == [
        f"Exported 2 image(s) to {tmp_path}",
        f"1: {tmp_path / 'deck.001.png'}",
        f"2: {tmp_path / 'deck.002.png'}",
    ]


# --- reading -----------------------------------------------------------------

def test_list_slides(osa):
    osa.queue("deck" + RS
              + FS.join(["1", "Title", "false", "true", "Hello"]) + RS
              + FS.join(["2", "Blank", "true", "false", ""]) + RS)
    assert server.list_slides().splitlines() == [
        "Document: deck — 2 slide(s)",
        "1: [Title] Hello",
        "2: [Blank] (title hidden) [skipped]",
    ]


def test_get_slide_count(osa):
    osa.queue("7")
    assert server.get_slide_count() == 7


def test_list_layouts_names_only(osa):
    osa.queue(MASTERS)
    assert server.list_layouts(detail=False).splitlines() == [
        "#1 Title", "#2 Title & Bullets", "#3 Title & Bullets", "#4 Blank"]


def test_list_layouts_detail(osa):
    osa.queue(slide_rec(1, "Title") + item_rec(1, "text item", 0, 0, 10, 10, "Title", title=True)
              + item_rec(2, "shape", 0, 300, 10, 10, "Subtitle", sample=True)
              + FS.join(["mtext", "true", "Title"]) + RS
              + slide_rec(2, "Bullets", title_showing=False)
              + item_rec(1, "image", 0, 0, 10, 10)
              + FS.join(["mtext", "false", "© Footer"]) + RS
              + slide_rec(3, "Bullets") + item_rec(1, "text item", 0, 0, 10, 10, "", body=True))
    lines = server.list_layouts().splitlines()
    assert lines[0].startswith("#1 Title | title: shown | body: shown | extra text slots: 1")
    assert '"Subtitle" sample at y=300' in lines[0]
    assert "title: HIDDEN" in lines[1] and "image placeholders: 1" in lines[1]
    assert 'fixed layout text: "© Footer"' in lines[1] and "same name as #3" in lines[1]
    assert "delete s" in osa.scripts[0]


def test_list_slide_items_roles(osa):
    osa.queue(TITLE_SLIDE)
    lines = server.list_slide_items(1).splitlines()
    assert lines[0] == "Slide 1 (layout: Title) — title: shown, body: shown"
    assert lines[1].startswith('[1] title (text item) x=100 y=200 w=800 h=120 text="Hello"')
    assert lines[2].startswith("[2] text_slot_sample (shape)")
    assert lines[3].startswith("[3] slide_number")


def test_find_text_edits_without_record(osa):
    assert server.find_text_edits().startswith("NO RECORD")


def test_find_text_edits_reports_changes(osa):
    server._record = {"1": {"title": "Hello", "items": {"2": "Sub"}},
                      "2": {"title": "Agenda", "body": "One\nTwo", "items": {}},
                      "4": {"items": {}}}
    osa.queue(TITLE_SLIDE + BULLETS_SLIDE + slide_rec(3, "Blank"))
    out = server.find_text_edits()
    assert out.startswith("1 text edit(s)")
    assert "Slide 1 text item 2: EDITED in Keynote" in out
    assert "never wrote (probably added in Keynote): 3" in out
    assert "record covers slides up to 4" in out


def test_accept_text_edits_updates_baseline(osa):
    server._record = {"1": {"title": "Old", "items": {"2": "Sub", "9": "gone"}}}
    osa.queue(TITLE_SLIDE)
    server.accept_text_edits(1)
    assert server._record == {"1": {"title": "Hello", "items": {"2": "Subtitle"}}}
    osa.queue(TITLE_SLIDE)
    assert server.find_text_edits().startswith("No text was edited")


# --- writing -----------------------------------------------------------------

def test_add_slide_by_name_and_default(osa):
    osa.queue(MASTERS, "2")
    assert server.add_slide(layout="Title & Bullets") == (
        "Added slide #2 (layout: #2 Title & Bullets (note: 2 layouts share this name: #2, #3; pass layout_index to pick another))")
    assert "base layout:master slide 2" in osa.scripts[1]
    osa.queue("3")
    assert server.add_slide() == "Added slide #3 (layout: default)"
    assert set(server._record) == {"2", "3"}


def test_add_slide_bad_layout(osa):
    osa.queue(MASTERS, MASTERS)
    with pytest.raises(ValueError, match="No layout named"):
        server.add_slide(layout="Nope")
    with pytest.raises(ValueError, match="out of range"):
        server.add_slide(layout_index=9)


def test_set_title_records_written_text(osa):
    osa.queue("OK" + FS + "Hello" + RS)
    assert server.set_title(1, 'Say "hi"') == "Set title on slide 1"
    assert 'set newText to "Say \\"hi\\""' in osa.scripts[0]
    assert server._record["1"]["title"] == "Hello"


def test_set_title_same_text_is_left_alone(osa):
    osa.queue("SAME" + FS + "Hello" + RS)
    assert "already has this text" in server.set_title(1, "Hello")


def test_set_body_hidden_is_not_written(osa):
    osa.queue("HIDDEN" + FS + "Title Only")
    assert server.set_body(1, "One").startswith("NOT WRITTEN")
    assert server._record == {}


def test_set_body_show(osa):
    osa.queue("OK" + FS + "One\nTwo" + RS)
    assert server.set_body(2, "One\nTwo", show=True) == "Set body on slide 2 (turned it on)"
    assert "set body showing to true" in osa.scripts[0]
    assert server._record["2"]["body"] == "One\nTwo"


def test_set_text_item(osa):
    osa.queue("OK" + FS + "Sub" + RS)
    assert server.set_text_item(1, 2, "Sub") == "Set text of item 2 on slide 1"
    assert server._record["1"]["items"]["2"] == "Sub"
    osa.queue("TITLE", "CLASS" + FS + "image")
    assert server.set_text_item(1, 1, "x").startswith("NOT WRITTEN: item 1 on slide 1 is the title")
    assert server.set_text_item(1, 4, "x").endswith("is a image, which has no text.")


def test_add_image_warns_on_overlap(osa, tmp_path):
    img = tmp_path / "pic.png"
    img.write_bytes(b"png")
    osa.queue("4", "", BULLETS_SLIDE)
    msg = server.add_image(2, str(img), x=600, width=300)
    assert "set width of t to 300" in osa.scripts[1]
    assert msg.startswith("Added image on slide 2: [4] image (image) x=600 y=300 w=300 h=200")
    assert "WARNING: overlaps [2] body" in msg


def test_add_image_missing_file(osa):
    with pytest.raises(FileNotFoundError):
        server.add_image(1, "/no/such.png")


def test_set_item_geometry(osa):
    osa.queue("", TITLE_SLIDE)
    msg = server.set_item_geometry(1, 2, y=500)
    assert "set position of t to {item 1 of p, 500}" in osa.scripts[0]
    assert "width" not in osa.scripts[0]
    assert msg.startswith("Updated item on slide 1: [2]")


def test_set_slide_layout_resets_item_record(osa):
    server._record = {"1": {"title": "Hi", "items": {"2": "Sub"}}}
    osa.queue(MASTERS, "")
    assert server.set_slide_layout(1, layout_index=4) == "Slide 1 now uses layout #4 Blank"
    assert server._record == {"1": {"title": "Hi", "items": {}}}


def test_delete_item_shifts_recorded_indexes(osa):
    server._record = {"1": {"items": {"2": "a", "3": "b", "5": "c"}}}
    osa.queue("OK")
    assert server.delete_item(1, 3) == "Deleted item 3 from slide 1"
    assert server._record["1"]["items"] == {"2": "a", "4": "c"}


def test_delete_item_placeholder_and_shape(osa):
    server._record = {"1": {"items": {"2": "Sub"}}}
    osa.queue("TITLE", "CLEARED")
    assert server.delete_item(1, 1) == "Hid the title placeholder on slide 1"
    assert server.delete_item(1, 2).startswith("Cleared the text of item 2")
    assert server._record["1"]["items"] == {"2": ""}


def test_delete_slide_shifts_record(osa):
    server._record = {"1": {"items": {}}, "2": {"title": "B", "items": {}}, "3": {"title": "C", "items": {}}}
    osa.queue("2")
    assert server.delete_slide(2) == "Deleted slide 2; the deck now has 2 slide(s)"
    assert server._record == {"1": {"items": {}}, "2": {"title": "C", "items": {}}}
