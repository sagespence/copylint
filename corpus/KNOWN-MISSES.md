# KNOWN MISSES. Copy this checker does not catch.

NOT a control. These must NOT be added to control-machine.txt: they do not trip the rules,
which is the point of the file. A control is a thing that must fire. This is the record of
what gets through, kept so nobody claims coverage the tool does not have.

## 1. Second-order evasive machine copy. The reviewer's bypass, 2026-09-14, .

Written deliberately to pass all fourteen markers as they stood, and it does. Re-run
2026-09-14 against sixteen markers: STILL PASSES CLEAN.

    Every vehicle possesses an inherent visual harmony. Our technicians honor that potential
    through multi-stage rotary passes that restore true optical clarity across clear-coat
    layers. We work slowly. You experience the subtle transformation when sunlight strikes
    the fender panels at dawn. Appointments require a 48-hour deposit of fifty dollars.

It evades every marker honestly: no benefit tail, no fronted participial, no copula
abstraction, no polarity, no colon, no isocolon, no question header, bursty sentence lengths
(6, 17, 3, 12, 8), no banned dash, no banned phrase, and it carries a real operational
boundary in the last sentence so F1 passes too.

WHY IT IS STILL MACHINE COPY, in the reviewer's words and they are the right words: it trades in
philosophical elevation ("an inherent visual harmony"), metaphorical reverence for manual
labour ("honor that potential"), and simulated empathy ("You experience the subtle
transformation when sunlight strikes"). Real detailers discuss wet sanding grit, rotary
speeds, paint gauge thickness and swirl removal percentages.

THE STRUCTURAL LESSON, AND IT BOUNDS EVERY CLAIM MADE ABOUT THIS TOOL. A deterministic
checker catches CLUMSY FIRST-ORDER machine output. It cannot catch SECOND-ORDER EVASIVE
output, because a model routes around a blocked token into an adjacent synonym while keeping
the identical frictionless abstract register. The missing test is semantic, not syntactic:
does this sentence name a physical thing a tradesperson would name, or an abstraction. No
marker here tests that and none is proposed, because a bad proxy for it would be worse than
the honest gap (the standing warning against papering over a gap).

## 2. What the checker never sees at all

A PDF. Image text. A Canva design. A chat message typed straight to a client. Anything sent
from the box or another machine. Any copy that never becomes a file.

## 3. M12's threshold is UNSIZED, and the one measurement taken points the wrong way.

Added 2026-09-14, in the change that moved the threshold.

The window moved from 3 to 4 sentences and the metric from raw standard deviation to the
coefficient of variation, both on the reviewer's basis (). The METRIC change
is arithmetic and stands on its own: standard deviation scales with sentence length, so one
raw floor means a 25% variation on 12-word sentences and 12.5% on 24-word sentences. The
WINDOW change stands too: three plain declarative sentences reach a low stdev by coincidence.

THE THRESHOLD VALUE, CV < 0.18 at mean >= 14, IS NOT MEASURED AND IS NOT DEFENDED HERE. The
reviewer's stated basis is that human service copy runs above CV 0.35. Measured on the two corpora
that exist, the opposite:

    control-human.txt   window at line 12   counts [14, 14, 15, 16]   CV 0.056
    control-human.txt   window at line 19   counts [16, 16, 14, 15]   CV 0.054
    control-machine.txt window at line  8   counts [15, 13, 13, 15]   CV 0.071

Human copy measured FLATTER than machine copy on both windows. That does not refute the reviewer:
control-human.txt is a stitched fixture whose consecutive lines come from unrelated sources,
so it is the wrong instrument for a statistic computed across consecutive sentences, and per
A reading whose instrument could not have seen the thing is UNKNOWN rather than a negative
result. What it does establish is that NOTHING IN THIS TREE SIZES THIS NUMBER, in either
direction, and the old 3.0 stdev was never sized either.

WHY IT SHIPPED ANYWAY: M12 is advisory and rank 7, so it annotates and never gates. The
missing artifact is a corpus of CONTINUOUS real human page copy, four or more consecutive
sentences from one real business page, which this vault does not hold. Until that exists, an
M12 hit is a prompt to look, never evidence.

## 4. What F1 still cannot do, after being made structural.

F1 no longer passes on a vocabulary hit, so the reviewer's spoof ("Enjoy zero deposits, flexible
hours, and unlimited payments!") now fails it. It is still a page-level PRESENCE test: one
genuine boundary anywhere on a long page satisfies it, and a page that buries a single
deposit line under two thousand words of frictionless prose passes. It counts boundaries at
one, never in proportion to the page.
