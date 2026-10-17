#!/usr/bin/env python3
"""copylint: flag machine-register copy in client-facing text.

Input : one or more .html/.md/.txt paths, or - for stdin.
Output: one finding per line as path:line: [ID] name | sentence, plus file-level checks.
        Exit 0 clean, 1 findings, 2 refused or error (a control failed, an input could
        not be read, or an input held no prose to judge; no verdict is given).

It FLAGS. It never rewrites: the wording call belongs to a human.

Rules are read from rules.json beside this file and documented in the README, so the prose
standard and the code cannot drift apart silently. Two negative controls gate every run, by
design: a machine corpus that must trip named markers and a human corpus that must trip
none. A run whose controls do not both pass reports itself vacuous and prints no verdict.
An input that yields no prose at all is refused the same way, never reported clean.
"""
import argparse, html, json, os, re, sys, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "rules.json"), encoding="utf-8") as _fh:
    RULES = json.load(_fh)


class NoProse(Exception):
    """Raised when an input yields no prose units, so any verdict on it would be vacuous."""

ABSTRACT = {"experience","excellence","journey","promise","story","passion","craft","soul",
    "spirit","signature","essence","vision","legacy","confidence","transformation","beauty",
    "artistry","mastery","tradition","atmosphere","difference","standard","possibility","moment",
    "style","look","presence","comfort","peace","individuality","respect","potential","clarity",
    "security","integrity","quality","care","dedication","harmony",
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
    """Yield (line_no, kind, text) for markdown or plain text. kind is heading, label or prose."""
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
    Why: if the whole line went out as prose, a bold card title such as "Deadlines that
    don't slip" would never be tested as a label and M11 could not see it.
    """
    m = re.match(r"^\*\*(.+?)\*\*\s*(.*)$", s)
    if not m: return False
    lab = m.group(1).strip().rstrip(".:").strip()
    short = len(re.findall(r"[A-Za-z0-9'$/-]+", lab)) <= 9 and not re.search(r"[.!?]\s*$", lab)
    out.append((i, "label" if short else "prose", lab))
    if m.group(2).strip(): out.append((i, "prose", m.group(2).strip()))
    return True

def read_text(path):
    """Read a path (or stdin for "-") as UTF-8 text.

    Input: a file path or "-". Output: the decoded text. Raises OSError when the path cannot
    be read and NoProse when the bytes are binary or not valid UTF-8, since text that cannot
    be decoded cannot be judged and must not be reported clean.
    """
    if path == "-":
        data = sys.stdin.buffer.read()
    else:
        with open(path, "rb") as fh:
            data = fh.read()
    if b"\x00" in data:
        raise NoProse("binary input")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise NoProse("input is not valid UTF-8") from None

def extract_text(raw, ext):
    """Split raw text into (line_no, kind, text) units. Input: text and a lowercase extension.

    .html and .htm go through the HTML extractor; everything else, stdin included, is read
    as markdown or plain text.
    """
    if ext in (".html", ".htm"): return strip_html(raw)
    return strip_md(raw)

def extract(path):
    """Read a path (or "-") and return its (line_no, kind, text) units."""
    raw = read_text(path)
    ext = "" if path == "-" else os.path.splitext(path)[1].lower()
    return extract_text(raw, ext)

SENT = re.compile(r"[^.!?]*[.!?]|[^.!?]+$")
def sentences(text):
    """Split text into stripped, non-empty sentences on . ! and ?."""
    return [s.strip() for s in SENT.findall(text) if s.strip()]

def syllables(w):
    """Rough syllable count for one word (vowel groups, minus a silent final e). Minimum 1."""
    w = w.lower().strip("'\".,;:!?()")
    if not w: return 0
    g = re.findall(r"[aeiouy]+", w)
    n = len(g)
    if w.endswith("e") and n > 1 and not w.endswith(("le","ee","ye")): n -= 1
    return max(1, n)

def sylls(s):
    """Total syllables in a string."""
    return sum(syllables(w) for w in s.split())

def words(s):
    """Word tokens in a string: letters, digits, apostrophes, $, / and hyphens."""
    return re.findall(r"[A-Za-z0-9'$/-]+", s)

# ---------- marker tests ----------
QUOTED = re.compile(r'"[^"]*"|\u201c[^\u201d]*\u201d|`[^`]*`|\u2018[^\u2019]*\u2019')
def quoted_spans(sent):
    """Return (start, end) offsets of every quoted span in a sentence."""
    return [(m.start(), m.end()) for m in QUOTED.finditer(sent)]

def in_quote(sent, m):
    """A marker matched inside a quotation is quoted copy, not this document's own copy."""
    return any(a <= m.start() and m.end() <= b for a, b in quoted_spans(sent))

NUMERIC = re.compile(r"\d|\b(one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|"
    r"forty|fifty|sixty|eighty|hundred)\b[- ]?\w*\b(foot|pound|inch|minute|hour|day|week|"
    r"degree|percent|dollar|quart|coat|turn|gram|psi|volt)", re.I)

def t_regex(rule, sent, kind):
    """Plain pattern marker. True when rule["pattern"] matches outside a quotation.

    M13 (dashes) is case-sensitive and ignores quotes. M1 is waived when the tail carries a
    measurement, because that is a spec and not a benefit tag.
    """
    flags = 0 if rule["id"] == "M13" else re.I
    m = re.search(rule["pattern"], sent, flags)
    if not m: return False
    if rule["id"] != "M13" and in_quote(sent, m): return False
    if rule["id"] == "M1" and NUMERIC.search(sent[m.end():]):
        return False        # the tail carries a measurement, so it is a spec and not a benefit tag
    return True

def t_colon_claim(rule, sent, kind):
    """M5: a claim pre-announced with a colon and unpacked after it.

    True for a long lead-in followed by a colon and an abstract explanation. Label:value
    pairs, citations, instructions, quotations and concrete specifics are excluded.
    """
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

def _clauses(sent, n):
    """Split a sentence into exactly n coordinate clauses, or return None."""
    body = re.sub(r"[.!?]+$", "", sent)
    if n == 3:
        parts = re.split(r",\s*(?:and\s+)?|\s+and\s+", body)
    else:
        parts = re.split(r"\s+and\s+", body)
    parts = [p.strip() for p in parts if p.strip()]
    return parts if len(parts) == n else None

def t_isocolon(rule, sent, kind):
    """M6 and M7: n parallel clauses of near-equal length that praise an abstraction.

    True when rule["n"] clauses have near-equal word and syllable counts, do not all open
    with the same word (that is anaphora, a human figure), are real clauses of three or more
    words, and name an abstract virtue.
    """
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
    """M10: a short abstract heading that works as free-standing ad copy."""
    if kind != "heading": return False
    w = words(sent)
    if not (3 <= len(w) <= 9): return False
    if any(re.search(r"\d|\$", x) for x in w): return False
    if w[0].lower().strip(".,") in CTA: return False
    if any(x[0].isupper() for x in w[1:]): return False   # names a business or place
    if sent.rstrip().endswith("?"): return False
    return any(x.lower().strip(".,") in ABSTRACT for x in w)

def t_label_rule(rule, sent, kind):
    """M11: a label or heading that carries a claim instead of being a bare noun."""
    if kind not in ("label", "heading"): return False
    # A bold card title is a label by position, so it is tested up to nine words.
    if not is_labelish(sent) and not (kind == "label" and len(words(sent)) <= 9
                                      and not re.search(r"[.!?]\s*$", sent)): return False
    low = sent.lower().rstrip(".")
    # A label that opens "Not ..." or "No ..." states an exclusion, a boundary, not a claim.
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

# Extra M11 tests for card titles such as "Deadlines that don't slip", "The key paperwork read
# for you", "Problems flagged early", "Know where any case stands in seconds", "A clear next
# step in negotiations" and "The attorney stays in charge". Each carries a claim that a bare
# noun label would not: the reader addressed, a negation, a speed or timing promise, a finite
# verb, an imperative, a past participle used as a predicate, or a selling adjective.
# Gated by corpus/m11-label-fixture.tsv so none of these can quietly stop firing.
# Nouns that end in -ing and are not verbs; "A morning brief" would otherwise trip the -ing test.
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

FINITE = re.compile(r"\b(is|are|was|were|be|been|does|do|did|has|have|had|can|could|will|"
    r"would|should|must|may|might|gives|creates|makes|takes|sounds|means|costs|runs|needs|"
    r"keeps|works|comes|goes|gets|sends|stores|charges|holds|shows|tells|brings|builds|"
    r"delivers|provides|offers|supersedes|happens|follows|starts|ends|stays|lets|helps)\b", re.I)
TEMPORAL = re.compile(r"^(Starting|Beginning|Effective|Ending|Closing|Opening)\s+"
    r"(tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday|next|this|"
    r"[A-Z][a-z]+\s+\d|\d)", re.I)

def t_fronted(rule, sent, kind):
    """M2: a sentence that opens with a verb-ing phrase before the actor.

    Schedule notices ("Starting tomorrow, ...") and phrases whose head already holds a
    finite verb are excluded, and a main clause must follow the comma.
    """
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
    """M15: three noun phrases sharing one determiner ("your time, your trust, and your style")."""
    m = DET_TRI.search(sent)
    return bool(m) and not in_quote(sent, m)

IMP_SERIES = re.compile(
    r"\b[a-z]+\s+(your|our)\s+[\w'-]+\s*,\s+[a-z]+\s+(?:\1\s+)?[\w'-]+\s*,?\s+(?:and\s+)?[a-z]+\s+",
    re.I)
def t_imp_series(rule, sent, kind):
    """M16: a repeated imperative-plus-possessive frame ("Refine your X, express your Y, and ...")."""
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
    coincidence (13, 14, 13 gives 0.58).
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
    strapline. A restaurant-page line such as "Globally-inspired menus. Welcoming atmosphere.
    Award-winning hospitality." trips nothing else in this tool.

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

    A GENUINE OPERATIONAL BOUNDARY IS A STRUCTURE, NOT A WORD. Four archetypes: a bilateral
    condition penalty (A), a hard capacity ceiling (B), an explicit scope exclusion (C) and a
    prerequisite gate (D). A fifth, a concretely posted schedule (E), is added because a real
    page that says "Tuesday to Saturday, 9 to 5" has stated a real limit and would otherwise
    fail on a rule written against machine copy.

    A vocabulary list would pass on any mention of a deposit, an hour or a price, which is
    exactly how a bypass such as "Enjoy zero deposits, flexible hours" would clear it.
    """
    global BOUNDARY_RX
    if BOUNDARY_RX is None:
        fc = next(f for f in RULES["file_checks"] if f["id"] == "F1")
        BOUNDARY_RX = [(k, re.compile(v, re.I)) for k, v in fc["archetypes"].items()]
    return [k for k, rx in BOUNDARY_RX if rx.search(text)]

# ---------- driver ----------
# Markers that need a whole page (a window of consecutive sentences) and are skipped in
# message mode. Derived from rules.json so the count printed for a run cannot drift from
# what lint() actually evaluates.
PAGE_ONLY = {r["id"] for r in RULES["markers"] if r["test"] == "entropy"}


class RulesError(Exception):
    """Raised when rules.json cannot be applied, so no verdict can be given."""


def evaluated_marker_ids(kind_mode):
    """IDs of the markers lint evaluates in a mode: all of them on a page, all but the
    page-only ones in message mode. Input: "page" or "message". Output: list of ids."""
    return [r["id"] for r in RULES["markers"]
            if kind_mode == "page" or r["id"] not in PAGE_ONLY]


def lint_text(raw, ext="", kind_mode="page"):
    """Lint already-read text.

    Input: the text, its lowercase extension (".html" selects the HTML extractor, anything
    else is read as markdown or plain text) and the mode, "page" or "message".
    Output: sorted findings as (line, id, name, sentence). Raises NoProse when the text
    holds no sentences, because an empty reading is blindness and not a clean result, and
    RulesError when rules.json names a test that does not exist.
    """
    units = []
    for line, kind, text in extract_text(raw, ext):
        for s in sentences(text):
            units.append((line, kind, s))
    if not units:
        raise NoProse()
    active = set(evaluated_marker_ids(kind_mode))
    findings = []
    for line, kind, sent in units:
        for rule in RULES["markers"]:
            if rule["id"] not in active: continue
            if rule["test"] in ("entropy", "np_tricolon"): continue  # windowed, run below
            fn = TESTS.get(rule["test"])
            if fn is None:
                raise RulesError(f"rules.json names unknown test {rule['test']!r} "
                                 f"for {rule['id']}")
            if fn(rule, sent, kind): findings.append((line, rule["id"], rule["name"], sent))
    if "M12" in active:
        for line, blob in t_entropy(units):
            findings.append((line, "M12", "flat sentence-length entropy", blob))
    for line, blob in t_np_tricolon(units):
        findings.append((line, "M17", "noun-phrase tricolon", blob))
    if kind_mode == "page":
        alltext = " ".join(s for _, _, s in units)
        findings += page_structure(raw, ext, alltext)
        if not boundary_archetypes(alltext):
            fc = next(f for f in RULES["file_checks"] if f["id"] == "F1")
            findings.append((0, "F1", fc["name"],
                             "no operational boundary anywhere on this page: no condition with a "
                             "consequence, no capacity ceiling, no stated exclusion, no prerequisite, "
                             "no posted schedule. Naming a price is not a boundary."))
    findings.sort(key=lambda f: (f[0], f[1]))
    return findings


def lint(path, kind_mode="page"):
    """Lint a file path, or "-" for stdin. Output as lint_text. Raises OSError when the path
    cannot be read and NoProse when it is binary or holds no prose."""
    raw = read_text(path)
    ext = "" if path == "-" else os.path.splitext(path)[1].lower()
    return lint_text(raw, ext, kind_mode)

ADVISORY = {r["id"] for r in RULES["markers"] if r.get("rank") == 7}

RESIDUE = re.compile(
    r"\b(TODO|FIXME|lorem ipsum|placeholder|draft copy|copy to come|fill this in|"
    r"example text|copy tbd|image tbd)\b"
    r"|\[insert|\[name\]|\{\{|<%"
    r"|\b(her|his|their|your) own words (on|from)\b"          # copy naming its own source
    r"|\bthe (events|details|specifics) behind them\b"        # copy naming what it will hold
    r"|\b(copy|text|words) (for|from) (her|his|their|the) [a-z]+ page\b", re.I)

def page_structure(raw, ext, alltext):
    """Page-level AI-site tells: F2 draft residue, F3 reused assets, F4 monotonous grids.

    These are STRUCTURE, not sentence register, which is a different layer: a page can pass
    every sentence marker and still read as generated. Input: the raw text, its extension
    and the extracted prose. F2 runs on any input; F3 and F4 read markup and run on HTML only.
    Output: list of findings.
    """
    out = []
    m = RESIDUE.search(alltext)
    if ext not in (".html", ".htm"):
        if m: out.append((0, "F2", "draft residue in copy", alltext[max(0,m.start()-60):m.start()+80]))
        return out

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

def f1_fixture(path=None):
    """F1's structural archetypes are gated on a fixture that must score perfectly.

    A vocabulary list could be eyeballed. Five regex archetypes cannot, and false positives
    are found by running them over real boundary sentences rather than by reading them.
    Input: optional fixture path (default corpus/f1-boundary-fixture.tsv). Output: list of
    problems, [] when correct. A fixture with no cases is itself a problem.
    """
    path = path or os.path.join(HERE, "corpus", "f1-boundary-fixture.tsv")
    bad, n = [], 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip(): continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 2: continue
            want, text = parts; n += 1
            got = boundary_archetypes(text)
            if want == "MUST-FAIL" and got:
                bad.append(f"MUST-FAIL line matched {','.join(got)}: {text[:70]!r}")
            if want == "MUST-PASS" and not got:
                bad.append(f"MUST-PASS line matched no archetype: {text[:70]!r}")
    if n == 0:
        bad.append("VACUOUS: the F1 fixture holds no cases")
    return bad

def m11_fixture(path=None):
    """The M11 label test is gated on a fixture that must score perfectly.

    Each case is run through strip_md as a bold card title, so the fixture fails if either the
    bold-lead extraction or the label test stops working. Input: optional fixture path
    (default corpus/m11-label-fixture.tsv). Output: list of problems, [] when correct.
    """
    path = path or os.path.join(HERE, "corpus", "m11-label-fixture.tsv")
    bad, n = [], 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
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

# The banned-dash control is built from a code point so that no corpus file in the repository
# has to contain the character itself. It must trip M13.
DASH_CONTROL = "We believe in real craft " + chr(0x2014) + " the kind you can see.\n"

def _control_lint(name, msgs):
    """Lint one control corpus file. Returns its findings, or [] after recording a failure
    in msgs when the file is missing, unreadable or holds no prose."""
    try:
        return lint(os.path.join(HERE, "corpus", name))
    except (OSError, NoProse) as e:
        msgs.append(f"CONTROL FAIL cannot use corpus/{name}: {e or 'no prose'}")
        return []

def run_controls():
    """Run the negative controls. Output: (ok, messages). The report is withheld unless
    every control passes."""
    ok, msgs = True, []
    f1bad = f1_fixture()
    if f1bad:
        ok = False
        msgs.append("CONTROL FAIL F1 boundary fixture, %d wrong: %s" % (len(f1bad), "; ".join(f1bad)))
    m11bad = m11_fixture()
    if m11bad:
        ok = False
        msgs.append("CONTROL FAIL M11 label fixture, %d wrong: %s" % (len(m11bad), "; ".join(m11bad)))
    mach = _control_lint("control-machine.txt", msgs) + _control_lint("control-machine-page.html", msgs)
    mach += lint_text(DASH_CONTROL, ".txt", "message")
    got = {f[1] for f in mach}
    want = {r["id"] for r in RULES["markers"]} | {"F1", "F2", "F3", "F4"}
    # Every marker is required, M12 included. Subtracting "M12 unless it fired" from the
    # requirement would make M12 required only when it had already passed, a check that
    # cannot fail.
    missing = want - got
    if missing:
        ok = False; msgs.append("CONTROL FAIL machine corpus did not trip: " + ",".join(sorted(missing)))
    hum = [f for f in _control_lint("control-human.txt", msgs) if f[1] not in ADVISORY]
    if hum:
        ok = False
        msgs.append("CONTROL FAIL human corpus produced %d false positives: %s"
                    % (len(hum), "; ".join(f"{f[1]} on {f[3][:60]!r}" for f in hum)))
    if any(m.startswith("CONTROL FAIL cannot use") for m in msgs):
        ok = False
    return ok, msgs

def build_parser():
    """Command-line parser. Positional paths (or - for stdin), --kind, --quiet, -h."""
    ap = argparse.ArgumentParser(
        prog="copylint",
        description="Flag machine-register copy in .html, .md and .txt files. "
                    "It flags and never rewrites. With no path it runs the built-in controls only.",
        epilog="Exit codes: 0 clean, 1 findings, 2 refused or error (a control failed, a path "
               "could not be read, or an input held no prose, so no verdict is given).")
    ap.add_argument("paths", nargs="*", metavar="PATH",
                    help="files to lint; use - to read stdin (treated as plain text or markdown)")
    ap.add_argument("--kind", choices=("page", "message"), default="page",
                    help="page (default) adds page-level checks F1 to F4 and M12; "
                         "message is for a text, caption or DM")
    ap.add_argument("--quiet", action="store_true",
                    help="do not print the 'clean over N markers' line for files with no findings")
    return ap

def main(argv):
    """CLI entry point. Input: argument list. Output: exit code (0 clean, 1 findings,
    2 refused or error)."""
    args = build_parser().parse_args(argv)
    ok, msgs = run_controls()
    if not ok:
        print("VACUOUS: controls did not pass, no verdict is reported.", file=sys.stderr)
        for m in msgs: print("  " + m, file=sys.stderr)
        return 2
    if not args.paths:
        print("controls pass (machine corpus trips every named marker, human corpus trips none)")
        return 0
    total, refused = 0, False
    for p in args.paths:
        try:
            fs = lint(p, args.kind)
        except OSError as e:
            print(f"ERROR: cannot read {p}: {e.strerror or e}", file=sys.stderr)
            refused = True; continue
        except NoProse as e:
            why = f" ({e})" if str(e) else ""
            print(f"VACUOUS: no prose extracted from {p}{why}, no verdict", file=sys.stderr)
            refused = True; continue
        except RulesError as e:
            print(f"VACUOUS: {e}. No verdict is reported.", file=sys.stderr)
            return 2
        total += len(fs)
        for line, rid, name, sent in fs:
            tag = " (advisory)" if rid in ADVISORY else ""
            print(f"{p}:{line}: [{rid}]{tag} {name} | {sent[:160]}")
        if not fs and not args.quiet:
            print(f"{p}: clean over {len(evaluated_marker_ids(args.kind))} markers ({args.kind} mode)")
    if refused: return 2
    return 1 if total else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
