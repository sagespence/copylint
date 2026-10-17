#!/usr/bin/env python3
"""Score copylint against a labelled sentence set.

Input: a TSV of id<TAB>label<TAB>sentence, label in {human, machine}. Comment lines start #.
A sentence is called MACHINE when any non-advisory marker fires on it in message mode.

WHAT THIS MEASURES AND WHAT IT DOES NOT. It measures the SENTENCE markers only. F1 and M12
are page-level and a one-sentence input can never exercise them, so a score here is silent
about both. A score on a set the checker was tuned against is IN SAMPLE and overfit; it is a
ruler for comparing two versions of the checker, never an estimate of new copy.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import copylint

def score(tsv):
    """Score the labelled TSV. Input: path to id<TAB>label<TAB>sentence rows. Output: a dict
    with n, tp, fp, tn, fn, precision, recall, accuracy, misses and falsepos. Each sentence
    is linted in memory in message mode, so no temporary file is written."""
    rows = []
    with open(tsv, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip(): continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3: continue
            rows.append(parts)
    tp = fp = tn = fn = 0
    misses, falsepos = [], []
    for rid, label, sent in rows:
        fs = [x for x in copylint.lint_text(sent + "\n", "", "message") if x[1] not in copylint.ADVISORY]
        flagged = bool(fs)
        if label == "machine":
            if flagged: tp += 1
            else: fn += 1; misses.append((rid, sent))
        else:
            if flagged: fp += 1; falsepos.append((rid, sent, [x[1] for x in fs]))
            else: tn += 1
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec  = tp / (tp + fn) if (tp + fn) else float("nan")
    acc  = (tp + tn) / len(rows) if rows else float("nan")
    return dict(n=len(rows), tp=tp, fp=fp, tn=tn, fn=fn,
                precision=prec, recall=rec, accuracy=acc,
                misses=misses, falsepos=falsepos)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: score.py <labelled.tsv>", file=sys.stderr); sys.exit(2)
    try:
        r = score(sys.argv[1])
    except OSError as e:
        print(f"ERROR: cannot read {sys.argv[1]}: {e.strerror or e}", file=sys.stderr); sys.exit(2)
    print(f"n={r['n']}  TP={r['tp']} FP={r['fp']} TN={r['tn']} FN={r['fn']}")
    print(f"PRECISION {r['precision']:.2f}  RECALL {r['recall']:.2f}  ACCURACY {r['accuracy']:.2f}")
    if r["falsepos"]:
        print("\nFALSE POSITIVES (human called machine):")
        for rid, s, ids in r["falsepos"]: print(f"  {rid} {','.join(ids)} | {s[:110]}")
    if r["misses"]:
        print("\nMISSES (machine called human):")
        for rid, s in r["misses"]: print(f"  {rid} | {s[:110]}")
