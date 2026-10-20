GROK_BLOCKED = set("cn ru ir kp cu sy".split())

GPT = set("""
    al dz ad ao ag ar am au at az bs bd bb be bz bj bt ba bw br bg bf cv ca cl co km cr hr cy dk dj
    dm do ec sv ee fj fi fr ga gm ge de gh gr gd gt gn gw gy ht hn hu is in id iq ie il it jm jp jo
    kz ke ki kw kg lv lb ls lr li lt lu mg mw my mv ml mt mh mr mu mx mc mn me ma mz mm na nr np nl
    nz ni ne ng mk no om pk pw pa pg pe ph pl pt qa ro rw kn lc vc ws sm st sn rs sc sl sg sk si sb
    za es lk sr se ch th tg to tt tn tr tv ug ae us uy vu zm bo bn cg cz va fm md ps kr tw tz tl gb
""".split())

CLAUDE = set("""
    al dz ad ao ag ar am au at az bs bh bd bb be bz bj bt bo ba bw br bn bg bf bi cv kh cm ca td cl
    co km cg cr ci hr cy cz dk dj dm do ec eg sv gq ee sz fj fi fr ga gm ge de gh gr gd gt gn gw gy
    ht hn hu is in id iq ie il it jm jp jo kz ke ki kw kg la lv lb ls lr li lt lu mg mw my mv mt mh
    mr mu mx fm md mc mn me ma mz na nr np nl nz ne ng mk no om pk pw ps pa pg py pe ph pl pt qa ro
    rw kn lc vc ws sm st sa sn rs sc sl sg sk si sb za kr es lk sr se ch tw tj tz th tl tg to tt tn
    tr tm tv ug ua ae gb us uy uz vu va vn zm zw
""".split())

GEMINI = set("""
    ax al dz as ad ao ai aq ag ar am aw au at az bh bd bb be bz bj bm bt bo ba bw br io vg bn bg bf
    bi cv kh cm ca bq ky cf td cl cx cc co km ck cr ci hr cw cz cd dk dj dm do ec eg sv gq er ee sz
    et fk fo fj fi fr gf pf tf ga ge de gh gi gr gl gd gp gu gt gg gn gw gy ht hm hn hu is in id iq
    ie im il it jm jp je jo kz ke ki xk kw kg la lv lb ls lr ly li lt lu mg mw my mv ml mt mh mq mr
    mu yt mx fm md mc mn me ms ma mz mm na nr np nl nc nz ni ne ng nu nf mk mp no om pk pw ps pa pg
    py pe ph pn pl pt pr qa cy cg re ro rw bl sh kn lc mf pm vc ws sm st sa sn rs sc sl sg sx sk si
    sb so za gs kr ss es lk sd sr sj se ch tw tj tz th bs gm tl tg tk to tt tn tr tm tc tv vi ug ua
    ae gb us um uy uz vu va ve vn wf eh ye zm zw
""".split())

ISO3 = {
    "and": "ad", "are": "ae", "afg": "af", "atg": "ag", "aia": "ai", "alb": "al", "arm": "am", "ago": "ao",
    "ata": "aq", "arg": "ar", "asm": "as", "aut": "at", "aus": "au", "abw": "aw", "ala": "ax", "aze": "az",
    "bih": "ba", "brb": "bb", "bgd": "bd", "bel": "be", "bfa": "bf", "bgr": "bg", "bhr": "bh", "bdi": "bi",
    "ben": "bj", "blm": "bl", "bmu": "bm", "brn": "bn", "bol": "bo", "bes": "bq", "bra": "br", "bhs": "bs",
    "btn": "bt", "bvt": "bv", "bwa": "bw", "blr": "by", "blz": "bz", "can": "ca", "cck": "cc", "cod": "cd",
    "caf": "cf", "cog": "cg", "che": "ch", "civ": "ci", "cok": "ck", "chl": "cl", "cmr": "cm", "chn": "cn",
    "col": "co", "cri": "cr", "cub": "cu", "cpv": "cv", "cuw": "cw", "cxr": "cx", "cyp": "cy", "cze": "cz",
    "deu": "de", "dji": "dj", "dnk": "dk", "dma": "dm", "dom": "do", "dza": "dz", "ecu": "ec", "est": "ee",
    "egy": "eg", "esh": "eh", "eri": "er", "esp": "es", "eth": "et", "fin": "fi", "fji": "fj", "flk": "fk",
    "fsm": "fm", "fro": "fo", "fra": "fr", "gab": "ga", "gbr": "gb", "grd": "gd", "geo": "ge", "guf": "gf",
    "ggy": "gg", "gha": "gh", "gib": "gi", "grl": "gl", "gmb": "gm", "gin": "gn", "glp": "gp", "gnq": "gq",
    "grc": "gr", "sgs": "gs", "gtm": "gt", "gum": "gu", "gnb": "gw", "guy": "gy", "hkg": "hk", "hmd": "hm",
    "hnd": "hn", "hrv": "hr", "hti": "ht", "hun": "hu", "idn": "id", "irl": "ie", "isr": "il", "imn": "im",
    "ind": "in", "iot": "io", "irq": "iq", "irn": "ir", "isl": "is", "ita": "it", "jey": "je", "jam": "jm",
    "jor": "jo", "jpn": "jp", "ken": "ke", "kgz": "kg", "khm": "kh", "kir": "ki", "com": "km", "kna": "kn",
    "prk": "kp", "kor": "kr", "kwt": "kw", "cym": "ky", "kaz": "kz", "lao": "la", "lbn": "lb", "lca": "lc",
    "lie": "li", "lka": "lk", "lbr": "lr", "lso": "ls", "ltu": "lt", "lux": "lu", "lva": "lv", "lby": "ly",
    "mar": "ma", "mco": "mc", "mda": "md", "mne": "me", "maf": "mf", "mdg": "mg", "mhl": "mh", "mkd": "mk",
    "mli": "ml", "mmr": "mm", "mng": "mn", "mac": "mo", "mnp": "mp", "mtq": "mq", "mrt": "mr", "msr": "ms",
    "mlt": "mt", "mus": "mu", "mdv": "mv", "mwi": "mw", "mex": "mx", "mys": "my", "moz": "mz", "nam": "na",
    "ncl": "nc", "ner": "ne", "nfk": "nf", "nga": "ng", "nic": "ni", "nld": "nl", "nor": "no", "npl": "np",
    "nru": "nr", "niu": "nu", "nzl": "nz", "omn": "om", "pan": "pa", "per": "pe", "pyf": "pf", "png": "pg",
    "phl": "ph", "pak": "pk", "pol": "pl", "spm": "pm", "pcn": "pn", "pri": "pr", "pse": "ps", "prt": "pt",
    "plw": "pw", "pry": "py", "qat": "qa", "reu": "re", "rou": "ro", "srb": "rs", "rus": "ru", "rwa": "rw",
    "sau": "sa", "slb": "sb", "syc": "sc", "sdn": "sd", "swe": "se", "sgp": "sg", "shn": "sh", "svn": "si",
    "sjm": "sj", "svk": "sk", "sle": "sl", "smr": "sm", "sen": "sn", "som": "so", "sur": "sr", "ssd": "ss",
    "stp": "st", "slv": "sv", "sxm": "sx", "syr": "sy", "swz": "sz", "tca": "tc", "tcd": "td", "atf": "tf",
    "tgo": "tg", "tha": "th", "tjk": "tj", "tkl": "tk", "tls": "tl", "tkm": "tm", "tun": "tn", "ton": "to",
    "tur": "tr", "tto": "tt", "tuv": "tv", "twn": "tw", "tza": "tz", "ukr": "ua", "uga": "ug", "umi": "um",
    "usa": "us", "ury": "uy", "uzb": "uz", "vat": "va", "vct": "vc", "ven": "ve", "vgb": "vg", "vir": "vi",
    "vnm": "vn", "vut": "vu", "wlf": "wf", "wsm": "ws", "yem": "ye", "myt": "yt", "zaf": "za", "zmb": "zm",
    "zwe": "zw",
}
