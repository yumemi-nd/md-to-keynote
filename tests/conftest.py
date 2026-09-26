import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

import keynote_slides_server as server  # noqa: E402

FS, RS = server.FS, server.RS


class FakeOsascript:
    """Stands in for run_applescript: records every script and answers with queued
    replies in order. A reply may be a callable, which gets the script and returns the reply."""

    def __init__(self):
        self.replies = []
        self.scripts = []

    def queue(self, *replies):
        self.replies.extend(replies)
        return self

    def __call__(self, script):
        self.scripts.append(script)
        if not self.replies:
            raise AssertionError("unexpected AppleScript call:\n" + script)
        reply = self.replies.pop(0)
        return reply(script) if callable(reply) else reply


@pytest.fixture
def osa(monkeypatch):
    fake = FakeOsascript()
    monkeypatch.setattr(server, "run_applescript", fake)
    monkeypatch.setattr(server, "_doc_path", None)
    monkeypatch.setattr(server, "_record", {})
    yield fake
    assert not fake.replies, f"unused AppleScript replies: {fake.replies}"


def slide_rec(number, layout, title_showing=True, body_showing=True):
    return FS.join(["slide", str(number), layout, str(title_showing).lower(), str(body_showing).lower()]) + RS


def item_rec(index, cls, x, y, w, h, text="", title=False, body=False, sample=False):
    return FS.join(["item", str(index), cls, str(title).lower(), str(body).lower(),
                    str(x), str(y), str(w), str(h), str(sample).lower(), text]) + RS
