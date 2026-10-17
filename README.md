# copylint

A linter for machine-sounding copy. Point it at a web page, a message or a draft and it
flags the sentence patterns that make writing read as if a language model produced it.
It flags and never rewrites: the wording call stays with a human.

Python 3, standard library only.

## Run it

```bash
python3 copylint.py corpus/control-machine-page.html     # page mode (default): adds page-level checks
python3 copylint.py --kind=message corpus/control-machine.txt   # a text, caption or DM: no page-level checks
python3 copylint.py --kind message --quiet corpus/control-human.txt   # space form also works; --quiet hides "clean" lines
printf '%s\n' '- Social posts on autopilot' | python3 copylint.py --kind=message -   # "-" reads stdin
python3 copylint.py                                      # run the built-in controls only
python3 copylint.py --help                               # usage
python3 score.py corpus/scored-set.tsv                   # precision and recall against a labelled sentence set
python3 -B test_copylint.py                              # tests
```

Options:

- `PATH ...`: one or more `.html`, `.htm`, `.md` or `.txt` files. `-` reads stdin.
- `--kind page|message`: `page` (default) adds the page-level checks F1 to F4 and the
  sentence-rhythm marker M12. `message` is for a text, caption or DM.
- `--quiet`: do not print the `clean over N markers` line for files with no findings.
  Findings and errors are still printed.
- `-h`, `--help`: print usage and exit 0.

Exit codes: `0` clean, `1` findings, `2` refused or error. Exit 2 means no verdict was
given: a control failed, a path could not be read (missing file, a directory), or an input
held no prose to judge (empty, whitespace only, markup with no text, binary or not valid
UTF-8). A bad path is reported on one line and the remaining paths are still linted, but the
run exits 2.

Example (this command reproduces it). M11 applies to labels, so it fires on a list item, a
heading, a button or a bold lead, not on a sentence:

```
$ printf '%s\n' '- Social posts on autopilot' | python3 copylint.py --kind=message -
-:1: [M11] label with bolted-on claim | Social posts on autopilot
-:1: [M14] banned phrase | Social posts on autopilot
```

A clean file prints `<path>: clean over N markers (<mode> mode)`. N is the number of
markers evaluated in that mode: 17 in page mode, 16 in message mode (M12 needs a whole page).

## What it checks

Seventeen markers, M1 to M17 (see `rules.json`, which holds each pattern and a one-line reason), among them a trailing benefit clause, a fronted
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

Other limits:

- Input must be UTF-8 text. Binary or undecodable files are refused, not guessed at.
- Stdin (`-`) has no file extension, so it is read as plain text or markdown. HTML sent on
  stdin is not parsed as HTML, and the HTML-only checks F3 and F4 do not run on it. The
  draft-residue check F2 does run, on the text of the input.
- Page mode on a short snippet will report F1 (no operational boundary) because a snippet
  rarely states hours or limits. Use `--kind=message` for snippets.
- M12 is advisory (rank 7) and its threshold is unsized; see `corpus/KNOWN-MISSES.md`.

## Layout

| Path | What |
|---|---|
| `copylint.py` | extraction, markers, controls, CLI |
| `rules.json` | marker definitions, patterns and thresholds |
| `score.py` | precision / recall on a labelled TSV |
| `corpus/` | control corpora, fixtures, scored set, known misses |
| `test_copylint.py` | unit tests |
| `LICENSE` | MIT license |

## License

MIT. See `LICENSE`.
