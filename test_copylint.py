"""Tests for copylint: controls pass, human text is clean, machine text is flagged,
a broken control makes the run refuse to report, blind inputs are refused, and the
command line behaves (exit codes, bad paths, help, --kind forms)."""
import os, re, shutil, subprocess, sys, tempfile, unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
CLI = os.path.join(HERE, "copylint.py")
SCORE = os.path.join(HERE, "score.py")

import copylint  # noqa: E402


def run(*args, cwd=HERE, stdin=None):
    """Run python with args. Returns (exit code, stdout, stderr)."""
    p = subprocess.run([sys.executable, "-B", *args], capture_output=True, text=True,
                       cwd=cwd, input=stdin)
    return p.returncode, p.stdout, p.stderr


def write(d, name, data):
    """Write str or bytes into directory d and return the path."""
    p = os.path.join(d, name)
    with open(p, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))
    return p


def ids(findings):
    """Set of rule ids in a findings list."""
    return {f[1] for f in findings}


class TestCopylint(unittest.TestCase):
    def test_controls_pass(self) -> None:
        rc, out, err = run(CLI)
        self.assertEqual(rc, 0, out + err)
        self.assertIn("controls pass", out)

    def test_machine_text_is_flagged(self) -> None:
        rc, out, err = run(CLI, "--kind=message", os.path.join(HERE, "corpus", "control-machine.txt"))
        self.assertEqual(rc, 1, out + err)
        self.assertIn("[M11]", out)

    def test_plain_message_is_clean(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "m.txt", "We close at 6 on Saturdays. Cash or debit, no Amex.\n")
            rc, out, err = run(CLI, "--kind=message", p)
            self.assertEqual(rc, 0, out + err)

    def test_broken_control_refuses_a_verdict(self) -> None:
        """Copy the tool, empty the machine corpus: the run must say VACUOUS and exit 2."""
        with tempfile.TemporaryDirectory() as d:
            dst = os.path.join(d, "copy")
            shutil.copytree(HERE, dst, ignore=shutil.ignore_patterns("__pycache__", ".git"))
            write(os.path.join(dst, "corpus"), "control-machine.txt", "Plain words only.\n")
            rc, out, err = run(os.path.join(dst, "copylint.py"), "--kind=message",
                               os.path.join(HERE, "corpus", "control-human.txt"))
            self.assertEqual(rc, 2, out + err)
            self.assertIn("VACUOUS", err)

    def test_empty_control_file_refuses_a_verdict(self) -> None:
        """An emptied control corpus is a refused run, not a traceback or a pass."""
        with tempfile.TemporaryDirectory() as d:
            dst = os.path.join(d, "copy")
            shutil.copytree(HERE, dst, ignore=shutil.ignore_patterns("__pycache__", ".git"))
            write(os.path.join(dst, "corpus"), "control-machine.txt", "")
            rc, out, err = run(os.path.join(dst, "copylint.py"))
            self.assertEqual(rc, 2, out + err)
            self.assertIn("VACUOUS", err)
            self.assertNotIn("Traceback", err)

    def test_dash_control_trips_the_dash_marker(self) -> None:
        """M13 is exercised by an in-code control, so the control must actually fire it."""
        self.assertIn("M13", ids(copylint.lint_text(copylint.DASH_CONTROL, ".txt", "message")))

    def test_scored_set_has_no_false_positives(self) -> None:
        rc, out, err = run(SCORE, os.path.join(HERE, "corpus", "scored-set.tsv"))
        self.assertIn("FP=0", out)


class TestBlindInputsAreRefused(unittest.TestCase):
    """An input that yields no prose must not be reported clean."""

    def check_refused(self, name, data, *flags):
        with tempfile.TemporaryDirectory() as d:
            p = write(d, name, data)
            rc, out, err = run(CLI, *flags, p)
            self.assertEqual(rc, 2, out + err)
            self.assertIn("VACUOUS: no prose extracted from " + p, err)
            self.assertNotIn("clean", out)
            self.assertEqual(len(err.strip().splitlines()), 1, err)

    def test_empty_file(self) -> None:
        self.check_refused("empty.txt", "")

    def test_empty_file_message_mode(self) -> None:
        self.check_refused("empty.md", "", "--kind=message")

    def test_whitespace_file(self) -> None:
        self.check_refused("blank.txt", "  \n\t\n   \n")

    def test_binary_file(self) -> None:
        self.check_refused("blob.txt", bytes([0, 1, 2, 255, 254, 0, 7]) * 40)

    def test_undecodable_file_without_nul(self) -> None:
        self.check_refused("latin.txt", b"Caf\xe9 au lait opens at nine.\n")

    def test_html_without_text(self) -> None:
        self.check_refused("tags.html", "<html><body><div><img src='a.jpg'></div></body></html>")

    def test_empty_stdin(self) -> None:
        rc, out, err = run(CLI, "-", stdin="")
        self.assertEqual(rc, 2, out + err)
        self.assertIn("VACUOUS: no prose extracted from -", err)

    def test_api_raises_on_no_prose(self) -> None:
        for raw, ext in (("", ".txt"), ("   \n", ".md"), ("<p></p>", ".html")):
            with self.assertRaises(copylint.NoProse):
                copylint.lint_text(raw, ext, "message")

    def test_one_blind_input_does_not_hide_a_real_finding(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            empty = write(d, "empty.txt", "")
            bad = write(d, "bad.txt", "Refine your daily style, elevate your weekly look, and build your monthly mood.\n")
            rc, out, err = run(CLI, "--kind=message", empty, bad)
            self.assertEqual(rc, 2, out + err)
            self.assertIn("bad.txt:1:", out)
            self.assertIn("VACUOUS", err)


class TestCommandLine(unittest.TestCase):
    def test_missing_file(self) -> None:
        rc, out, err = run(CLI, "/nonexistent/path/nowhere.txt")
        self.assertEqual(rc, 2, out + err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(len(err.strip().splitlines()), 1, err)
        self.assertIn("cannot read /nonexistent/path/nowhere.txt", err)

    def test_directory_as_path(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            rc, out, err = run(CLI, d)
            self.assertEqual(rc, 2, out + err)
            self.assertNotIn("Traceback", err)
            self.assertEqual(len(err.strip().splitlines()), 1, err)

    def test_bad_path_does_not_stop_the_other_paths(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            ok = write(d, "ok.txt", "We close at 6 on Saturdays. Cash or debit, no Amex.\n")
            rc, out, err = run(CLI, "--kind", "message", os.path.join(d, "missing.txt"), ok)
            self.assertEqual(rc, 2, out + err)
            self.assertIn("ok.txt: clean", out)

    def test_kind_with_space(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "m.txt", "We close at 6 on Saturdays. Cash or debit, no Amex.\n")
            rc, out, err = run(CLI, "--kind", "message", p)
            self.assertEqual(rc, 0, out + err)
            self.assertIn("(message mode)", out)

    def test_kind_with_equals(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "m.txt", "We close at 6 on Saturdays. Cash or debit, no Amex.\n")
            rc, out, err = run(CLI, "--kind=message", p)
            self.assertEqual(rc, 0, out + err)
            self.assertIn("(message mode)", out)

    def test_unknown_kind_is_an_error(self) -> None:
        rc, out, err = run(CLI, "--kind", "essay", "x.txt")
        self.assertEqual(rc, 2, out + err)
        self.assertIn("invalid choice", err)

    def test_help_exits_zero_and_does_not_run_controls(self) -> None:
        for flag in ("-h", "--help"):
            rc, out, err = run(CLI, flag)
            self.assertEqual(rc, 0, out + err)
            self.assertIn("usage:", out)
            self.assertIn("--quiet", out)
            self.assertIn("--kind", out)
            self.assertNotIn("controls pass", out)

    def test_quiet_hides_the_clean_line_only(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            ok = write(d, "ok.txt", "We close at 6 on Saturdays. Cash or debit, no Amex.\n")
            bad = write(d, "bad.txt", "Refine your daily style, elevate your weekly look, and build your monthly mood.\n")
            rc, out, err = run(CLI, "--kind=message", "--quiet", ok, bad)
            self.assertEqual(rc, 1, out + err)
            self.assertNotIn("clean", out)
            self.assertIn("bad.txt:1:", out)

    def test_stdin_is_linted(self) -> None:
        rc, out, err = run(CLI, "--kind=message", "-",
                           stdin="Refine your daily style, elevate your weekly look, and build your monthly mood.\n")
        self.assertEqual(rc, 1, out + err)
        self.assertIn("-:1:", out)

    def test_stdin_gets_the_draft_residue_check(self) -> None:
        rc, out, err = run(CLI, "-", stdin="Lorem ipsum dolor sit amet. We open at nine.\n")
        self.assertEqual(rc, 1, out + err)
        self.assertIn("[F2]", out)


class TestMarkerCount(unittest.TestCase):
    """The count printed on a clean run must equal the markers actually evaluated."""

    def evaluated(self, kind_mode):
        """Lint one sentence with every marker test wrapped, return the ids that ran."""
        seen = set()

        def wrap(fn):
            def inner(rule, sent, kind):
                seen.add(rule["id"])
                return fn(rule, sent, kind)
            return inner

        real_entropy, real_np = copylint.t_entropy, copylint.t_np_tricolon

        def entropy(units):
            seen.add("M12")
            return real_entropy(units)

        def np(units):
            seen.add("M17")
            return real_np(units)

        tests = {k: wrap(v) for k, v in copylint.TESTS.items()}
        with mock.patch.dict(copylint.TESTS, tests), \
                mock.patch.object(copylint, "t_entropy", entropy), \
                mock.patch.object(copylint, "t_np_tricolon", np):
            copylint.lint_text("We close at 6 on Saturdays. Cash or debit, no Amex.\n", ".txt", kind_mode)
        return seen

    def printed(self, kind_mode):
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "m.txt", "We close at 6 on Saturdays. Cash or debit, no Amex.\n")
            rc, out, err = run(CLI, "--kind=" + kind_mode, p)
        m = re.search(r"clean over (\d+) markers", out)
        self.assertIsNotNone(m, out + err)
        return int(m.group(1))

    def test_message_mode_count_equals_markers_evaluated(self) -> None:
        self.assertEqual(self.printed("message"), len(self.evaluated("message")))
        self.assertNotIn("M12", self.evaluated("message"))

    def test_page_mode_count_equals_markers_evaluated(self) -> None:
        total = len(copylint.RULES["markers"])
        self.assertEqual(len(self.evaluated("page")), total)
        self.assertEqual(len(copylint.evaluated_marker_ids("page")), total)
        self.assertEqual(len(copylint.evaluated_marker_ids("message")), total - 1)


class TestMutationGuards(unittest.TestCase):
    """Direct tests for behaviour that no corpus line happened to pin down."""

    def test_draft_residue_is_flagged_in_text_and_markdown(self) -> None:
        for ext in (".txt", ".md"):
            f = copylint.lint_text("Lorem ipsum dolor sit amet. We open at nine.\n", ext, "page")
            self.assertIn("F2", ids(f), ext)

    def test_draft_residue_check_is_page_mode_only(self) -> None:
        f = copylint.lint_text("Lorem ipsum dolor sit amet. We open at nine.\n", ".txt", "message")
        self.assertNotIn("F2", ids(f))

    def test_clean_text_has_no_draft_residue(self) -> None:
        f = copylint.lint_text("We open at nine on Saturdays.\n", ".txt", "page")
        self.assertNotIn("F2", ids(f))

    def test_tricolon_with_varied_openings_is_flagged(self) -> None:
        rule = {"n": 3}
        self.assertTrue(copylint.t_isocolon(rule, "We honor quality, they value comfort, and you earn respect.", "prose"))

    def test_anaphora_is_not_a_tricolon(self) -> None:
        """Three clauses that all open with the same word are a human figure, not M6."""
        rule = {"n": 3}
        s = "We value quality, we value comfort, and we value respect."
        self.assertFalse(copylint.t_isocolon(rule, s, "prose"))
        self.assertNotIn("M6", ids(copylint.lint_text(s + "\n", ".txt", "message")))

    def test_flat_rhythm_flags_on_a_page(self) -> None:
        f = copylint.lint_text(FLAT_FOUR, ".txt", "page")
        self.assertIn("M12", ids(f))

    def test_flat_rhythm_is_not_checked_in_message_mode(self) -> None:
        f = copylint.lint_text(FLAT_FOUR, ".txt", "message")
        self.assertNotIn("M12", ids(f))

    def test_f1_fixture_with_no_cases_is_vacuous(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "f1.tsv", "# comments only\n\n")
            bad = copylint.f1_fixture(p)
            self.assertTrue(any("VACUOUS" in b for b in bad), bad)

    def test_f1_fixture_with_cases_is_not_vacuous(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "f1.tsv", "MUST-PASS\tAppointments require a 48-hour deposit of fifty dollars.\n")
            self.assertEqual(copylint.f1_fixture(p), [])

    def test_f1_fixture_wrong_score_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "f1.tsv", "MUST-FAIL\tAppointments require a 48-hour deposit of fifty dollars.\n")
            bad = copylint.f1_fixture(p)
            self.assertEqual(len(bad), 1, bad)

    def test_m11_fixture_with_no_cases_is_vacuous(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "m11.tsv", "# comments only\n")
            self.assertTrue(any("VACUOUS" in b for b in copylint.m11_fixture(p)))


class TestScoreScript(unittest.TestCase):
    def test_score_writes_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tsv = write(d, "set.tsv", "H1\thuman\tWe close at 6 on Saturdays.\n"
                                      "M1\tmachine\tRefine your daily style, elevate your weekly look, and build your monthly mood.\n")
            work = os.path.join(d, "cwd")
            os.mkdir(work)
            rc, out, err = run(SCORE, tsv, cwd=work)
            self.assertEqual(rc, 0, out + err)
            self.assertIn("TP=1 FP=0 TN=1 FN=0", out)
            self.assertEqual(os.listdir(work), [])

    def test_no_fixed_temp_paths_in_sources(self) -> None:
        for name in ("copylint.py", "score.py"):
            with open(os.path.join(HERE, name), encoding="utf-8") as f:
                self.assertNotIn("/tmp/", f.read(), name)

    def test_score_bad_path(self) -> None:
        rc, out, err = run(SCORE, "/nonexistent/set.tsv")
        self.assertEqual(rc, 2, out + err)
        self.assertNotIn("Traceback", err)


# Four consecutive prose sentences of 15 words each: flat length, mean above the floor.
FLAT_FOUR = (
    "The shop opens at nine and the first customer usually walks in around ten past.\n"
    "Every truck gets a written estimate before anyone touches a wrench or a hoist.\n"
    "Parts that we order arrive within two days unless the supplier is out of stock.\n"
    "Payment is due when the work is finished and the keys are back in your hand.\n"
)


if __name__ == "__main__":
    unittest.main(verbosity=2)
