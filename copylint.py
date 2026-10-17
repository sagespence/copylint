#!/usr/bin/env python3
"""copylint: flag machine-register copy in client-facing text.

Input : one or more .html/.md/.txt paths, or - for stdin.
Output: one finding per line as path:line: [ID] name | sentence, plus file-level checks.
        Exit 0 clean, 1 findings, 2 control failure (report is vacuous and is withheld).

It FLAGS. It never rewrites: the wording call is the human's (the house copy standard).

Rules are read from rules.json beside this file so the prose standard and the code cannot
drift apart silently. Two negative controls gate every run, by design: a machine corpus that
must trip named markers and a human corpus that must trip none. A run whose controls do
not both pass reports itself vacuous and prints no verdict.
"""
import html, json, os, re, sys, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = json.load(open(os.path.join(HERE, "rules.json")))

ABSTRACT = {"experience","excellence","journey","promise","story","passion","craft","soul",
    "spirit","signature","essence","vision","legacy","confidence","transformation","beauty",
    "artistry","mastery","tradition","atmosphere","difference","standard","possibility","moment",
    "style","look","presence","comfort","peace","individuality","respect","potential","clarity",
    "security","integrity","quality","care","excellence","dedication","confidence","harmony",
    "wellbeing","reliability","elegance","sophistication","luxury","ritual","lifestyle"}
CTA = {"book","call","get","find","shop","schedule","order","visit","see","browse","view","start","join","text"}
TAGWORDS = ["on autopilot","in your words","in one place","made easy","done right","that runs itself",
    "without the hassle","on demand","the easy way","simplified","reimagined","handled for you"]

# ---------- extraction ----------
def is_labelish(s):
    """A label is a name, not a statement: short and unpunctuated."""
    return len(re.findall(r"[A-Za-z0-9'$/-]+", s)) <= 6 and not re.search(r"[.!?]\s*$", s)

def strip_html(raw):
    """Yield (line_no, kind, text). kind is heading, label or prose."""
    raw = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", lambda m: "\n"*m.group(0).count("\n"), raw)
    out, line = [], 1
    token = re.compile(r"<[^>]+>|[^<]+")
    tagstack = []
    for m in token.finditer(raw):
        t = m.group(0)
        if t.startswith("<"):
            name = re.match(r"</?\s*([a-zA-Z0-9]+)", t)
            if name:
                n = name.group(1).lower()
                if t.startswith("</"):
                    if tagstack and tagstack[-1][0] == n: tagstack.pop()
                elif not t.rstrip().endswith("/>"):
                    cls = re.search(r'class\s*=\s*"([^"]*)"', t)
                    tagstack.append((n, cls.group(1) if cls else ""))
        else:
            txt = html.unescape(t.replace("&nbsp;", " "))
            s = txt.strip()
            if s:
                ctx = tagstack[-1] if tagstack else ("", "")
                if ctx[0] in ("h1","h2","h3","h4","h5","h6"): kind = "heading"
                elif (ctx[0] in ("button","a","li","dt","th")
                      or "label" in ctx[1].lower() or "eyebrow" in ctx[1].lower()):
                    kind = "label" if is_labelish(s) else "prose"
                else: kind = "prose"
                out.append((line, kind, s))
        line += t.count("\n")
    return out

def strip_md(raw):
    out = []
    fence = False
    for i, ln in enumerate(raw.splitlines(), 1):
        if ln.strip().startswith("```"): fence = not fence; continue
        if fence: continue
        s = ln.strip()
        if not s: continue
        if s.startswith("#"): out.append((i, "heading", s.lstrip("#").strip())); continue
        if re.match(r"^[-*+]\s+\S", s) or re.match(r"^\d+[.)]\s+\S", s):
            body = re.sub(r"^([-*+]|\d+[.)])\s+", "", s)
            if bold_lead(i, body, out): continue
            out.append((i, "label" if is_labelish(body) else "prose", body)); continue
        if bold_lead(i, s, out): continue
        out.append((i, "prose", s))
    return out

def bold_lead(i, s, out):
    """A paragraph or list item that opens with a **bold lead** carries a label, then prose.

    Input: line number, the stripped line, the output list. Output: True when it split the line.
    Why: before 2026-10-16 the whole line went out as prose, so a bold card title such as
    "Deadlines that don't slip" was never tested as a label and M11 could not see it. Found
    when a reviewer caught six such titles in a client PRD that copylint had reported on.
    """
    m = re.match(r"^\*\*(.+?)\*\*\s*(.*)$", s)
    if not m: return False
    lab = m.group(1).strip().rstrip(".:").strip()
    short = len(re.findall(r"[A-Za-z0-9'$/-]+", lab)) <= 9 and not re.search(r"[.!?]\s*$", lab)
    out.append((i, "label" if short else "prose", lab))
    if m.group(2).strip(): out.append((i, "prose", m.group(2).strip()))
    return True

def extract(path):
    raw = sys.stdin.read() if path == "-" else open(path, errors="replace").read()
    ext = "" if path == "-" else os.path.splitext(path)[1].lower()
    if ext in (".html", ".htm"): return strip_html(raw)
    if ext in (".md", ".markdown"): return strip_md(raw)
    return strip_md(raw)

SENT = re.compile(r"[^.!?]*[.!?]|[^.!?]+$")
def sentences(text):
    return [s.strip() for s in SENT.findall(text) if s.strip()]

def syllables(w):
    w = w.lower().strip("'\".,;:!?()")
    if not w: return 0
    g = re.findall(r"[aeiouy]+", w)
    n = len(g)
    if w.endswith("e") and n > 1 and not w.endswith(("le","ee","ye")): n -= 1
    return max(1, n)

def sylls(s): return sum(syllables(w) for w in s.split())
def words(s): return [w for w in re.findall(r"[A-Za-z0-9'$/-]+", s)]

# ---------- marker tests ----------
QUOTED = re.compile(r'"[^"]*"|\u201c[^\u201d]*\u201d|`[^`]*`|\u2018[^\u2019]*\u2019')
def quoted_spans(sent):
    return [(m.start(), m.end()) for m in QUOTED.finditer(sent)]

def in_quote(sent, m):
    """A marker matched inside a quotation is quoted copy, not this document's own copy."""
    return any(a <= m.start() and m.end() <= b for a, b in quoted_spans(sent))

NUMERIC = re.compile(r"\d|\b(one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|"
    r"forty|fifty|sixty|eighty|hundred)\b[- ]?\w*\b(foot|pound|inch|minute|hour|day|week|"
    r"degree|percent|dollar|quart|coat|turn|gram|psi|volt)", re.I)

def t_regex(rule, sent, kind):
    flags = 0 if rule["id"] == "M13" else re.I
    m = re.search(rule["pattern"], sent, flags)
    if not m: return False
    if rule["id"] != "M13" and in_quote(sent, m): return False
    if rule["id"] == "M1" and NUMERIC.search(sent[m.end():]):
        return False        # the tail carries a measurement, so it is a spec and not a benefit tag
    return True

def t_colon_claim(rule, sent, kind):
    if ":" not in sent: return False
    before, after = sent.split(":", 1)
    bw, aw = words(before), words(after)
    if len(bw) < 3 or len(aw) < 4: return False          # label:value pair, leave alone
    if re.match(r"\s*(\d|\$|https?://|[A-Z][a-z]+day\b)", after): return False
    if re.search(r"\b(hours?|phone|address|email|price|cost|call|text|open|closed|book)\b", before, re.I): return False
    if len(bw) <= 4: return False                                # a label or a bulletin head, not a claim
    if re.search(r"\d", before): return False                    # a citation or a date, not a pre-announcement
    if any(w[0].isupper() for w in bw[1:] if w[0].isalpha()) and not before.isupper(): return False  # names a person, place or source
    if before.strip().isupper(): return False                     # a heading or a label, not a claim
    if re.match(r'\s*["\u201c\u2018`]', after): return False       # introduces a quotation
    if re.search(r"\d|\$", after): return False                   # unpacks into a concrete specific
    IMPER = {"bring","call","text","book","come","ask","pick","drop","park","wear","bear",
             "check","leave","use","take","pay","send","show","let","keep","give","email"}
    if aw and aw[0].lower().strip(",.") in IMPER: return False    # an instruction, not an assertion
    return True

# A filter, not a population.  Expanding it raises recall and never precision;
# an expansion is asked of an external reviewer in .
VERBHEADS = {"get","keep","make","take","give","cut","book","stay","run","build","refine",
    "elevate","walk","show","tell","bring","find","save","grow","boost","win","serve","meet",
    "deliver","create","provide","protect","restore","unlock","discover","experience","enjoy",
    "we","you","our","it","they","he","she","i"}

def _clauses(sent, n):
    body = re.sub(r"[.!?]+$", "", sent)
    if n == 3:
        parts = re.split(r",\s*(?:and\s+)?|\s+and\s+", body)
    else:
        parts = re.split(r"\s+and\s+", body)
    parts = [p.strip() for p in parts if p.strip()]
    return parts if len(parts) == n else None

def t_isocolon(rule, sent, kind):
    n = rule["n"]
    parts = _clauses(sent, n)
    if not parts: return False
    wc = [len(words(p)) for p in parts]
    if min(wc) < 2: return False                          # noun list, not clauses
    if max(wc) - min(wc) > 1: return False
    sy = [sylls(p) for p in parts]
    if max(sy) - min(sy) > 2: return False
    heads = [words(p)[0].lower() for p in parts]
    if len(set(heads)) == 1: return False                 # anaphora, a human figure
    # each part must be a CLAUSE, not a noun phrase: 3+ words with a verb head.
    for p in parts:
        if len(words(p)) < 3: return False
    joined = " ".join(parts).lower()
    if not any(re.search(r"\b" + a + r"s?\b", joined) for a in ABSTRACT):
        return False        # symmetrical PHYSICAL coordination is natural trade speech
    return True

def t_tagline(rule, sent, kind):
    if kind != "heading": return False
    w = words(sent)
    if not (3 <= len(w) <= 9): return False
    if any(re.search(r"\d|\$", x) for x in w): return False
    if w[0].lower().strip(".,") in CTA: return False
    if any(x[0].isupper() for x in w[1:]): return False   # names a business or place
    if sent.rstrip().endswith("?"): return False
    return any(x.lower().strip(".,") in ABSTRACT for x in w)

def t_label_rule(rule, sent, kind):
    if kind not in ("label", "heading"): return False
    # A bold card title is a label by position, so it is tested up to nine words (2026-10-16).
    if not is_labelish(sent) and not (kind == "label" and len(words(sent)) <= 9
                                      and not re.search(r"[.!?]\s*$", sent)): return False
    low = sent.lower().rstrip(".")
    # A label that opens "Not ..." or "No ..." states an exclusion, a boundary, not a claim (2026-10-16).
    if re.match(r"^(not|no)\s", low): return False
    if any(low.endswith(t) or (" " + t) in low for t in TAGWORDS): return True
    w = words(sent)
    if len(w) < 3: return False
    if re.search(r"\w+\s+(that|who|which)\s+\w+", low): return True
    if any(x.lower().endswith("ing") and x.lower() not in NOUN_ING for x in w[1:]) and len(w) >= 3: return True
    if re.match(r"^[A-Za-z][\w&/-]*(\s+[a-z][\w&/-]*){0,2}\s+(on|in|without|with|for)\s+\w+", sent) \
       and not re.search(r"\b(in|on)\s+(the\s+)?(shop|store|studio|salon|downtown|nyc|person)\b", low):
        return True
    return label_claim_extra(low, w)

# Added 2026-10-16 after six PRD card titles passed M11 ("Deadlines that don't slip", "The key
# paperwork read for you", "Problems flagged early", "Know where any case stands in seconds",
# "A clear next step in negotiations", "The attorney stays in charge"). Each carries a claim
# the old tests could not see: the reader addressed, a negation, a speed or timing promise,
# a finite verb, an imperative, a past participle used as a predicate, or a selling adjective.
# Gated by corpus/m11-label-fixture.tsv so none of these can quietly stop firing.
# Nouns that end in -ing and are not verbs; "A morning brief" tripped the -ing test (2026-10-16).
NOUN_ING = {"morning", "evening", "building", "booking", "pricing", "training", "setting", "meeting",
            "wedding", "ceiling", "clothing", "parking", "housing", "landing", "listing", "filing",
            "billing", "onboarding", "warning", "opening", "reading", "tracking", "ring", "spring",
            "thing", "string", "wing", "ending", "funding", "hearing", "pudding", "icing",
            "managing"}
LABEL_YOU = {"you", "your", "yours", "you're"}
LABEL_NEG = {"don't", "doesn't", "won't", "never"}
LABEL_SPEED = re.compile(r"\bin (seconds|minutes|one place|one click|real time)\b|\b(instantly|automatically|early|fast|effortlessly)\b")
LABEL_FINITE = {"stays", "keeps", "runs", "works", "stands", "tells", "shows", "knows", "gets", "makes",
                "takes", "handles", "slips", "lands", "matters", "happens", "catches", "reads"}
LABEL_IMPERATIVE = {"know", "see", "get", "keep", "stop", "find", "make", "take", "catch", "never", "meet", "say"}
LABEL_SELL = {"clear", "simple", "smart", "easy", "seamless", "effortless", "powerful", "instant", "better", "faster"}
LABEL_AFTER_ED = {"early", "fast", "for", "by", "automatically", "instantly", "daily", "first"}

def label_claim_extra(low, w):
    """Extra M11 tests for a label that carries a claim. Input: lowered label, its words. Output: bool."""
    lw = [x.lower().strip(".,:;") for x in w]
    if any(x in LABEL_YOU for x in lw): return True
    if any(x in LABEL_NEG or x.endswith("n't") for x in lw): return True
    if LABEL_SPEED.search(low): return True
    if any(x in LABEL_FINITE for x in lw[1:]): return True
    if len(lw) >= 3 and lw[0] in LABEL_IMPERATIVE: return True
    if any(x in LABEL_SELL for x in lw): return True
    for k in range(1, len(lw)):
        if lw[k].endswith("ed") and len(lw[k]) > 4 and (k == len(lw) - 1 or lw[k + 1] in LABEL_AFTER_ED):
            return True
    return False

BASEVERBS = {"thank","welcome","enjoy","discover","experience","choose","meet","join","book",
    "call","bring","get","let","take","make","see","try","come","ask","tell","show","keep","give"}

FINITE = re.compile(r"\b(is|are|was|were|be|been|does|do|did|has|have|had|can|could|will|"
    r"would|should|must|may|might|gives|creates|makes|takes|sounds|means|costs|runs|needs|"
    r"keeps|works|comes|goes|gets|sends|stores|charges|holds|shows|tells|brings|builds|"
    r"delivers|provides|offers|supersedes|happens|follows|starts|ends|stays|lets|helps)\b", re.I)
TEMPORAL = re.compile(r"^(Starting|Beginning|Effective|Ending|Closing|Opening)\s+"
    r"(tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday|next|this|"
    r"[A-Z][a-z]+\s+\d|\d)", re.I)

def t_fronted(rule, sent, kind):
    m = re.search(rule["pattern"], sent, re.I)
    if not m: return False
    if TEMPORAL.match(sent): return False   # "Starting tomorrow," is a schedule notice, not an inversion
    if in_quote(sent, m): return False
    head, tail = sent.split(",", 1)[0], sent.split(",", 1)[1]
    if FINITE.search(head): return False      # gerund subject, e.g. "Removing it does not sound human, it..."
    if not (FINITE.search(tail) or re.match(r"\s*(we|our|you|your|it|they|the)\b", tail, re.I)
            or re.search(r"\b\w+(s|ed)\b", tail)):
        return False                                  # no main clause follows
    return True

DET_TRI = re.compile(
    r"\b(your|our|their|the|every|each|no)\s+[\w'-]+\s*,\s+\1\s+[\w'-]+\s*,?\s+(?:and\s+)?\1\s+[\w'-]+",
    re.I)
def t_det_tricolon(rule, sent, kind):
    m = DET_TRI.search(sent)
    return bool(m) and not in_quote(sent, m)

IMP_SERIES = re.compile(
    r"\b[a-z]+\s+(your|our)\s+[\w'-]+\s*,\s+[a-z]+\s+(?:\1\s+)?[\w'-]+\s*,?\s+(?:and\s+)?[a-z]+\s+",
    re.I)
def t_imp_series(rule, sent, kind):
    m = IMP_SERIES.search(sent)
    if not m or in_quote(sent, m): return False
    return len(re.findall(r"\b(your|our)\b", sent, re.I)) >= 2

TESTS = {"regex": t_regex, "imp_series": t_imp_series, "det_tricolon": t_det_tricolon, "colon_claim": t_colon_claim, "fronted": t_fronted, "isocolon": t_isocolon,
         "tagline": t_tagline, "label_rule": t_label_rule}

def t_entropy(units):
    """Flag windows of consecutive prose sentences with flat length. Returns [(line, text)].

    Metric is the COEFFICIENT OF VARIATION, stdev over mean, not raw stdev, because stdev
    scales with sentence length: 3.0 words of spread on 12-word sentences is a 25% variation
    and on 24-word sentences only 12.5%, so one raw floor means two different things. Window
    is 4 rather than 3 because three plain declarative human sentences reach a low stdev by
    coincidence (13, 14, 13 gives 0.58). Both changes: reviewer 2026-09-14.
    """
    rule = next(r for r in RULES["markers"] if r["test"] == "entropy")
    win = rule["window"]
    mean_floor = rule["mean_floor"]
    cv_ceiling = rule["cv_ceiling"]
    out, run = [], []
    for line, kind, sent in units:
        if kind != "prose": run = []; continue
        run.append((line, sent, len(words(sent))))
        if len(run) >= win:
            w = run[-win:]
            counts = [x[2] for x in w]
            mean = statistics.mean(counts)
            if mean >= mean_floor and (statistics.pstdev(counts) / mean) < cv_ceiling:
                out.append((w[0][0], " / ".join(x[1][:40] for x in w)))
                run = []
    return out


VERBISH = set("""is are was were be been being am has have had do does did will would can could
shall should may might must get gets got take takes took make makes made comes come came go goes
went brings bring brought sells sell sold need needs needed use uses used let lets book books
call calls run runs ask asks give gives start starts starting adjust adjusts hold holds""".split())
ADJ_SUFFIX = re.compile(r"(ed|ing|al|ic|ive|ous|ful|less|able|ible|ary|ional)$", re.I)

def t_np_tricolon(units):
    """Three consecutive verbless noun-phrase fragments carrying claim adjectives.

    STRUCTURAL, NOT A WORD LIST. M6 sees clause tricolons and M15 sees a shared determiner
    ("your time, your trust, and your style"); neither can see three bare adjective-plus-noun
    fragments punctuated as separate sentences, which is the commonest form of the machine
    strapline. Measured 2026-09-14 on a real professional restaurant page: "Globally-inspired
    menus. Welcoming atmosphere. Award-winning hospitality." tripped nothing at all and is the
    most synthetic line on that page.

    At least two of the three must carry an adjective, which is what keeps a genuine fragment
    menu out: "Haircuts. Beard trims. Hot towel shaves." carries none and does not flag.
    """
    out, run = [], []
    for line, kind, sent in units:
        w = words(sent)
        adj = any("-" in t or (ADJ_SUFFIX.search(t) and t.lower() not in VERBISH) for t in w)
        verbless = not any(t.lower() in VERBISH for t in w)
        ok = 2 <= len(w) <= 4 and verbless and sent.rstrip().endswith((".", "!"))
        if not ok:
            run = []; continue
        run.append((line, sent, adj))
        if len(run) >= 3:
            g = run[-3:]
            if sum(1 for x in g if x[2]) >= 2:
                out.append((g[0][0], " / ".join(x[1][:34] for x in g)))
                run = []
    return out


BOUNDARY_RX = None

def boundary_archetypes(text):
    """Return the names of the boundary archetypes present in text.

    A GENUINE OPERATIONAL BOUNDARY IS A STRUCTURE, NOT A WORD. The four archetypes are the
    reviewer's (): a bilateral condition penalty, a hard capacity ceiling, an
    explicit scope exclusion, a prerequisite gate. E, a concretely posted schedule, is ours
    and is added because a real page that says "Tuesday to Saturday, 9 to 5" has stated a
    real limit and would otherwise fail on a rule written against machine copy.

    The old test was a vocabulary list and passed on any mention of a deposit, an hour or a
    price, which is exactly how the reviewer's bypass cleared it.
    """
    global BOUNDARY_RX
    if BOUNDARY_RX is None:
        fc = next(f for f in RULES["file_checks"] if f["id"] == "F1")
        BOUNDARY_RX = [(k, re.compile(v, re.I)) for k, v in fc["archetypes"].items()]
    return [k for k, rx in BOUNDARY_RX if rx.search(text)]

# ---------- driver ----------
PAGE_ONLY = {"F1", "M12"}

def lint(path, kind_mode="page"):
    units_raw = extract(path)
    units = []
    for line, kind, text in units_raw:
        for s in sentences(text):
            units.append((line, kind, s))
    findings = []
    for line, kind, sent in units:
        for rule in RULES["markers"]:
            if rule["test"] in ("entropy", "np_tricolon"): continue  # windowed, run below
            fn = TESTS.get(rule["test"])
            if fn is None:
                raise SystemExit(f"VACUOUS: rules.json names unknown test {rule['test']!r} "
                                 f"for {rule['id']}. No verdict is reported.")
            try: hit = fn(rule, sent, kind)
            except Exception: hit = False
            if hit: findings.append((line, rule["id"], rule["name"], sent))
    if kind_mode == "page":
        for line, blob in t_entropy(units):
            findings.append((line, "M12", "flat sentence-length entropy", blob))
    for line, blob in t_np_tricolon(units):
        findings.append((line, "M17", "noun-phrase tricolon", blob))
    # file-level
    alltext = " ".join(s for _, _, s in units)
    if kind_mode == "page":
        findings += page_structure(path, alltext)
    for fc in RULES["file_checks"]:
        if kind_mode != "page": continue
        if fc.get("test") == "page_structure": continue
        if fc["id"] == "F1":
            if not boundary_archetypes(alltext):
                findings.append((0, "F1", fc["name"],
                                 "no operational boundary anywhere on this page: no condition with a "
                                 "consequence, no capacity ceiling, no stated exclusion, no prerequisite, "
                                 "no posted schedule. Naming a price is not a boundary."))
    findings.sort(key=lambda f: (f[0], f[1]))
    return findings

ADVISORY = {r["id"] for r in RULES["markers"] if r.get("rank") == 7}

RESIDUE = re.compile(
    r"\b(TODO|FIXME|lorem ipsum|placeholder|draft copy|copy to come|fill this in|"
    r"example text|copy tbd|image tbd)\b"
    r"|\[insert|\[name\]|\{\{|<%"
    r"|\b(her|his|their|your) own words (on|from)\b"          # copy naming its own source
    r"|\bthe (events|details|specifics) behind them\b"        # copy naming what it will hold
    r"|\b(copy|text|words) (for|from) (her|his|their|the) [a-z]+ page\b", re.I)

def page_structure(path, alltext):
    """Page-level AI-site tells. Measured 2026-09-14 on the reviewer's a sample site site review.
    These are STRUCTURE, not sentence register, which is a different layer and is why the
    sentence markers all passed a page he called underwhelming."""
    out = []
    try:
        raw = open(path, errors="replace").read()
    except Exception:
        return out
    if not path.lower().endswith((".html", ".htm")):
        m = RESIDUE.search(alltext)
        if m: out.append((0, "F2", "draft residue in copy", alltext[max(0,m.start()-60):m.start()+80]))
        return out

    m = RESIDUE.search(alltext)
    if m:
        out.append((0, "F2", "draft residue in copy",
                    "builder scaffolding survived into visible text: " + alltext[max(0,m.start()-50):m.start()+90]))

    srcs = re.findall(r'(?:src|srcset)\s*=\s*"([^"]+)"', raw, re.I)
    names = [os.path.basename(s.split()[0].split("?")[0]) for s in srcs if s.strip()]
    names = [n for n in names if re.search(r"\.(jpe?g|png|webp|avif|gif)$", n, re.I)]
    for n in sorted(set(names)):
        c = names.count(n)
        if c >= 3:
            out.append((0, "F3", "asset reused across the page",
                        f"{n} is wired into {c} separate places, which reads as a thin library"))

    grids = re.findall(r"grid-template-columns\s*:\s*([^;}\n]+)", raw, re.I)
    norm = [re.sub(r"\s+", " ", g.strip().lower()) for g in grids]
    two = [g for g in norm if g in ("1fr 1fr", "repeat(2,1fr)", "repeat(2, 1fr)")]
    if len(two) >= 4:
        out.append((0, "F4", "monotonous grid rhythm",
                    f"the same two-column split is declared {len(two)} times; an alternating "
                    "50/50 flip down the whole page is the commonest generated-site cadence"))
    return out

def f1_fixture():
    """F1's structural archetypes are gated on a fixture that must score perfectly.

    A vocabulary list could be eyeballed. Four regex archetypes cannot, and the two false
    positives this check produced on the day it was written were both found by running it
    over real boundary sentences rather than by reading it. Returns [] when correct.
    """
    path = os.path.join(HERE, "corpus", "f1-boundary-fixture.tsv")
    bad = []
    for line in open(path, errors="replace"):
        if line.startswith("#") or not line.strip(): continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) != 2: continue
        want, text = parts
        got = boundary_archetypes(text)
        if want == "MUST-FAIL" and got:
            bad.append(f"MUST-FAIL line matched {','.join(got)}: {text[:70]!r}")
        if want == "MUST-PASS" and not got:
            bad.append(f"MUST-PASS line matched no archetype: {text[:70]!r}")
    if not bad and not any(True for _ in open(path, errors="replace") if _.startswith("MUST-")):
        bad.append("VACUOUS: the F1 fixture holds no cases")
    return bad

def m11_fixture():
    """the M11 label test is gated on a fixture that must score perfectly. Returns [] when correct.

    Each case is run through strip_md as a bold card title, so the fixture fails if either the
    bold-lead extraction or the label test stops working. Added 2026-10-16.
    """
    path = os.path.join(HERE, "corpus", "m11-label-fixture.tsv")
    bad, n = [], 0
    for line in open(path, errors="replace"):
        if line.startswith("#") or not line.strip(): continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) != 2: continue
        want, text = parts; n += 1
        units = strip_md("**%s.** Body sentence follows here." % text)
        got = any(k == "label" and t_label_rule(None, t, k) for _, k, t in units)
        if want == "MUST-FLAG" and not got: bad.append(f"MUST-FLAG label not flagged: {text!r}")
        if want == "MUST-PASS" and got: bad.append(f"MUST-PASS label flagged: {text!r}")
    if n == 0: bad.append("VACUOUS: the M11 fixture holds no cases")
    return bad

def run_controls():
    """the report is withheld unless every control passes."""
    ok, msgs = True, []
    f1bad = f1_fixture()
    if f1bad:
        ok = False
        msgs.append("CONTROL FAIL F1 boundary fixture, %d wrong: %s" % (len(f1bad), "; ".join(f1bad)))
    m11bad = m11_fixture()
    if m11bad:
        ok = False
        msgs.append("CONTROL FAIL M11 label fixture, %d wrong: %s" % (len(m11bad), "; ".join(m11bad)))
    mach = lint(os.path.join(HERE, "corpus", "control-machine.txt"))
    mach += lint(os.path.join(HERE, "corpus", "control-machine-page.html"))
    got = {f[1] for f in mach}
    want = {r["id"] for r in RULES["markers"]} | {"F1", "F2", "F3", "F4"}
    # M12 IS REQUIRED LIKE ANY OTHER MARKER. The line that used to sit here read
    #     want -= {"M12"} - got
    # which subtracts M12 from the requirement exactly when M12 did not fire, so M12 could
    # never fail this control: it was required only when it had already passed. That is the classic
    # check-that-cannot-fail inside its own control, found 2026-09-14 while mutation testing
    # the new CV threshold, which the mutation could not turn red because nothing tested it.
    missing = want - got
    if missing:
        ok = False; msgs.append("CONTROL FAIL machine corpus did not trip: " + ",".join(sorted(missing)))
    hum = [f for f in lint(os.path.join(HERE, "corpus", "control-human.txt"))
           if f[1] not in ADVISORY]
    if hum:
        ok = False
        msgs.append("CONTROL FAIL human corpus produced %d false positives: %s"
                    % (len(hum), "; ".join(f"{f[1]} on {f[3][:60]!r}" for f in hum)))
    return ok, msgs

def main(argv):
    quiet = "--quiet" in argv
    kind_mode = "page"
    for a in argv:
        if a.startswith("--kind="): kind_mode = a.split("=", 1)[1]
    if kind_mode not in ("page", "message"):
        print(f"VACUOUS: unknown --kind {kind_mode!r}. Use page or message.", file=sys.stderr)
        return 2
    argv = [a for a in argv if not a.startswith("--")]
    ok, msgs = run_controls()
    if not ok:
        print("VACUOUS: controls did not pass, no verdict is reported.", file=sys.stderr)
        for m in msgs: print("  " + m, file=sys.stderr)
        return 2
    if not argv:
        print("controls pass (machine corpus trips every named marker, human corpus trips none)")
        return 0
    total = 0
    for p in argv:
        fs = lint(p, kind_mode)
        total += len(fs)
        for line, rid, name, sent in fs:
            tag = " (advisory)" if rid in ADVISORY else ""
            print(f"{p}:{line}: [{rid}]{tag} {name} | {sent[:160]}")
        if not fs and not quiet:
            n = len(RULES['markers']) - (len(PAGE_ONLY) if kind_mode != "page" else 0)
            print(f"{p}: clean over {n} markers ({kind_mode} mode)")
    return 1 if total else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
