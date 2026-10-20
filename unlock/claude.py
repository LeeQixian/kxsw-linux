from .core import Result, get, trace, waf
from .countries import CLAUDE

URL = "https://claude.ai/"
TRACE = "https://claude.ai/cdn-cgi/trace"


def check(port):
    page = get(port, URL)
    loc = trace(port, TRACE)
    if page.status == 0 and not loc:
        return Result("unreachable")
    if "app-unavailable-in-region" in page.final:
        return Result(f"no({loc})" if loc else "no", False, loc)
    if page.status == 429:
        return Result(f"limited({loc})" if loc else "limited", False, loc)
    if page.status == 451:
        return Result(f"no({loc})" if loc else "no", False, loc)
    if not loc:
        if 200 <= page.status < 400:
            return Result(f"OK({page.status})", True)
        if page.status == 403 or waf(page.body):
            return Result("banned")
        return Result(f"HTTP{page.status}")
    if loc not in CLAUDE:
        return Result(f"no({loc})", False, loc)
    if page.status == 403 or waf(page.body):
        return Result(f"challenge({loc})", True, loc)
    if 200 <= page.status < 400:
        return Result(f"OK({loc})", True, loc)
    return Result(f"HTTP{page.status}({loc})", False, loc)
