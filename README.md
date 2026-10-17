# copylint

A linter for machine-sounding copy. Point it at a web page, a message or a draft and it
flags the sentence patterns that make writing read as if a language model produced it.
It flags and never rewrites: the wording call stays with a human.

Python 3, standard library only.

## Run it

```bash
python3 copylint.py page.html                 # page mode (default): includes page-level checks
python3 copylint.py --kind=message draft.txt  # a text, caption or DM: no page-level checks
python3 copylint.py                           # run the built-in controls only
python3 score.py corpus/scored-set.tsv        # precision and recall against a labelled sentence set
python3 -B test_copylint.py                   # tests
```

Exit codes: `0` clean, `1` findings, `2` the controls failed so no verdict is given.

Example output line: `draft.txt:3: [M11] label with bolted-on claim | Social posts on autopilot`

## What it checks

Seventeen markers (see `rules.json`), among them a trailing benefit clause, a fronted
participial, a copular abstraction, antithetical polarity ("not just X but Y"), symmetrical
tricolons, rhetorical question headers, tagline headlines, flat sentence-length rhythm,
banned dashes and a list of banned phrases. Page mode adds a structural check for missing
operational boundaries: real businesses state limits, hours, deposits and exclusions, and
copy with none of them reads as a simulation of a business with infinite capacity. That
check is structural, not a vocabulary list, so adding the word "deposit" does not satisfy it.

Rules live in `rules.json` so the written standard and the code cannot drift apart silently.

## The part worth reading: it refuses to report on itself being blind

Every run starts with two negative controls:

- a **machine corpus** that must trip every named marker, and
- a **human corpus** that must trip none.

If either control fails, copylint prints `VACUOUS` and gives no verdict at all. A linter
that says "clean" while unable to catch a planted violation is worse than no linter, so
this one withholds the answer instead. The page-level boundary check and the label check
are each gated on their own fixture (`corpus/f1-boundary-fixture.tsv`,
`corpus/m11-label-fixture.tsv`) that must score perfectly.

## Honest limits

`corpus/KNOWN-MISSES.md` records copy this tool does not catch, including a second-order
evasive paragraph written specifically to pass every marker. Those samples are kept out of
the controls on purpose, so nobody can claim coverage the tool does not have. The scored
set in `corpus/scored-set.tsv` was used to tune the thresholds, so a score on it is
in-sample; it is a ruler for comparing two versions, not an estimate on new copy.

## Layout

| Path | What |
|---|---|
| `copylint.py` | extraction, markers, controls, CLI |
| `rules.json` | marker definitions, thresholds, carve-outs |
| `score.py` | precision / recall on a labelled TSV |
| `corpus/` | control corpora, fixtures, scored set, known misses |
| `test_copylint.py` | unit tests |
