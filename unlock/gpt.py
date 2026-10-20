from .core import Result, get, trace
from .countries import GPT

API = "https://api.openai.com/compliance/cookie_requirements"
IOS = "https://ios.chat.openai.com/"
TRACE = "https://chat.openai.com/cdn-cgi/trace"

API_HEADERS = {
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9",
    "authorization": "Bearer null",
    "content-type": "application/json",
    "origin": "https://platform.openai.com",
    "referer": "https://platform.openai.com/",
    "sec-ch-ua": '"Chromium";v="125", "Not.A/Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
}

IOS_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "zh-CN,zh;q=0.9",
    "sec-ch-ua": '"Chromium";v="125", "Not.A/Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
}


def check(port):
    api = get(port, API, headers=API_HEADERS)
    ios = get(port, IOS, headers=IOS_HEADERS)
    loc = trace(port, TRACE)
    if api.status == 0 and ios.status == 0 and not loc:
        return Result("unreachable")
    if api.status == 429 or ios.status == 429:
        return Result(f"limited({loc})" if loc else "limited", False, loc)
    if loc == "t1":
        return Result("OK(tor)", True, loc)
    unsupported = "unsupported_country" in api.body
    vpn = "VPN" in ios.body
    if vpn and unsupported:
        return Result(f"no({loc})" if loc else "no", False, loc)
    if vpn:
        return Result(f"web-only({loc})" if loc else "web-only", True, loc)
    if unsupported:
        if ios.status:
            return Result(f"app-only({loc})" if loc else "app-only", True, loc)
        return Result(f"no({loc})" if loc else "no", False, loc)
    if loc:
        if loc in GPT:
            return Result(f"OK({loc})", True, loc)
        return Result(f"no({loc})", False, loc)
    if api.status and ios.status:
        return Result(f"OK({api.status})", True)
    return Result("no")
