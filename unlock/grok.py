from .core import Result, get, trace, waf
from .countries import GROK_BLOCKED

URL = "https://grok.com/"
TRACE = "https://grok.com/cdn-cgi/trace"


def check(port):
    page = get(port, URL)
    loc = trace(port, TRACE)
    if page.status == 0 and not loc:
        return Result("unreachable")
    if page.status == 429:
        return Result(f"limited({loc})" if loc else "limited", False, loc)
    if page.status == 451:
        return Result(f"no({loc})" if loc else "no", False, loc)
    if loc in GROK_BLOCKED:
        return Result(f"no({loc})", False, loc)
    if page.status == 403 or waf(page.body):
        if loc:
            return Result(f"challenge({loc})", True, loc)
        return Result("banned", False)
    if loc:
        return Result(f"OK({loc})", True, loc)
    if 200 <= page.status < 400:
        return Result(f"OK({page.status})", True)
    return Result(f"HTTP{page.status}", False)
