import re

from .core import Result, get
from .countries import GEMINI, ISO3

URL = "https://gemini.google.com/"
REGION = re.compile(r',2,1,200,"([A-Z]{3})"')
MARKS = ("45631641,null,true", "45617354,null,true")


def check(port):
    r = get(port, URL)
    if r.status == 0:
        return Result("unreachable")
    if r.status == 429:
        return Result("limited", False)
    if r.status in (403, 451):
        return Result("banned", False)
    if r.status != 200:
        return Result(f"HTTP{r.status}", False)
    m = REGION.search(r.body)
    loc = ISO3.get(m.group(1).lower(), "") if m else ""
    marked = any(mark in r.body for mark in MARKS)
    if loc and loc in GEMINI:
        return Result(f"OK({loc})", True, loc)
    if marked:
        return Result(f"OK({r.status})", True, loc)
    return Result(f"no({loc})" if loc else "no", False, loc)
