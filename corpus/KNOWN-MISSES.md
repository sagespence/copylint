# KNOWN MISSES. Copy this checker does not catch.

NOT a control. These must NOT be added to control-machine.txt: they do not trip the rules,
which is the point of the file. A control is a thing that must fire. This is the record of
what gets through, kept so nobody claims coverage the tool does not have.

## 1. Second-order evasive machine copy.

Written deliberately to pass the first fourteen markers, and it does. Re-run against all
seventeen markers in rules.json, in both page and message mode: STILL PASSES CLEAN.

    Every vehicle possesses an inherent visual harmony. Our technicians honor that potential
    through multi-stage rotary passes that restore true optical clarity across clear-coat
    layers. We work slowly. You experience the subtle transformation when sunlight strikes
    the fender panels at dawn. Appointments require a 48-hour deposit of fifty dollars.

It evades every marker honestly: no benefit tail, no fronted participial, no copula
abstraction, no polarity, no colon, no isocolon, no question header, bursty sentence lengths
(6, 17, 3, 12, 8), no banned dash, no banned phrase, and it carries a real operational
boundary in the last sentence so F1 passes too.

WHY IT IS STILL MACHINE COPY: it trades in
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
the honest gap.

## 2. What the checker never sees at all

A PDF. Image text. A design file. A chat message typed straight to a client. Any copy that
never becomes a .html, .md or .txt file or reaches stdin.

## 3. M12's threshold is UNSIZED, and the one measurement taken points the wrong way.

The window is 4 sentences and the metric is the coefficient of variation (CV), not raw
standard deviation. The metric choice is arithmetic and stands on its own: standard deviation
scales with sentence length, so one raw floor means a 25% variation on 12-word sentences and
12.5% on 24-word sentences. The window choice stands too: three plain declarative sentences
reach a low standard deviation by coincidence.

THE THRESHOLD VALUE, CV < 0.18 at mean >= 14, IS NOT MEASURED AND IS NOT DEFENDED HERE. The
expectation is that human service copy runs above CV 0.35. Measured on the two corpora
that exist, the opposite (every 4-sentence prose window with mean >= 14):

    control-human.txt   window at line 12   counts [14, 14, 15, 16]   CV 0.056
    control-human.txt   window at line 19   counts [16, 16, 14, 15]   CV 0.054
    control-human.txt   window at line 20   counts [16, 14, 15, 11]   CV 0.134
    control-machine.txt window at line  8   counts [15, 13, 13, 15]   CV 0.071

All three human windows sit under 0.18, and two are flatter than the machine window. That
does not refute the expectation: control-human.txt is a stitched fixture whose consecutive
lines come from unrelated sources, so it is the wrong instrument for a statistic computed
across consecutive sentences. A reading whose instrument could not have seen the thing is
unknown, not a negative result. What it does establish is that nothing in this repository
sizes this number, in either direction.

WHY IT SHIPPED ANYWAY: M12 is advisory and rank 7, so it annotates and never gates. The
missing artifact is a corpus of CONTINUOUS real human page copy, four or more consecutive
sentences from one real business page, which this repository does not hold. Until that exists, an
M12 hit is a prompt to look, never evidence.

## 4. What F1 still cannot do, after being made structural.

F1 no longer passes on a vocabulary hit, so the spoof ("Enjoy zero deposits, flexible
hours, and unlimited payments!") now fails it. It is still a page-level PRESENCE test: one
genuine boundary anywhere on a long page satisfies it, and a page that buries a single
deposit line under two thousand words of frictionless prose passes. It counts boundaries at
one, never in proportion to the page.
