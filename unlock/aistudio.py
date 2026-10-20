from urllib.parse import urlsplit

from . import gemini
from .core import Result, get
from .countries import GEMINI

URL = "https://aistudio.google.com/prompts/new_chat"
BLOCKED = (
    "not available in your country",
    "not available in your region",
    "unsupported country",
)


def classify(status, final, body, loc=""):
    if status == 0:
        return Result("unreachable")
    if status == 429:
        return Result(f"limited({loc})" if loc else "limited", False, loc)
    if status in (403, 451):
        return Result(f"banned({loc})" if loc else "banned", False, loc)
    if any(mark in body.lower() for mark in BLOCKED):
        return Result(f"no({loc})" if loc else "no", False, loc)
    parts = urlsplit(final)
    host = (parts.hostname or "").lower()
    path = parts.path.lower()
    if "/docs" in path or host == "ai.google.dev" or host.endswith("developers.google.com"):
        return Result(f"no(docs,{loc})" if loc else "no(docs)", False, loc)
    if host.endswith("aistudio.google.com"):
        return Result(f"OK({loc})" if loc else f"OK({status})", True, loc)
    if host.endswith("accounts.google.com"):
        return Result(f"OK(login,{loc})" if loc else "OK(login)", True, loc)
    return Result(f"{status}->{host}", False, loc)


def check(port):
    # AI Studio has no unauthenticated region signal; reuse Gemini's.
    g = gemini.check(port)
    loc = g.loc
    if loc and loc not in GEMINI:
        return Result(f"no({loc})", False, loc)
    r = get(port, URL)
    return classify(r.status, r.final, r.body, loc)
