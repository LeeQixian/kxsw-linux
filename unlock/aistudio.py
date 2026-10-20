from .core import Result, get

URL = "https://aistudio.google.com/prompts/new_chat"
BLOCKED = (
    "not available in your country",
    "not available in your region",
    "unsupported country",
)


def check(port):
    r = get(port, URL)
    if r.status == 0:
        return Result("unreachable")
    if r.status == 429:
        return Result("limited", False)
    if r.status in (403, 451):
        return Result("banned", False)
    body = r.body.lower()
    if any(mark in body for mark in BLOCKED):
        return Result("no", False)
    host = r.final.split("/")[2] if "://" in r.final else ""
    if "aistudio.google.com" in host:
        return Result(f"OK({r.status})", True)
    if "accounts.google.com" in host:
        return Result("OK(login)", True)
    return Result(f"{r.status}->{host}", False)
