"""Tests for copylint: controls pass, human text is clean, machine text is flagged,
a broken control makes the run refuse to report."""
import os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.join(HERE, "copylint.py")


def run(*args, cwd=HERE):
    p = subprocess.run([sys.executable, "-B", *args], capture_output=True, text=True, cwd=cwd)
    return p.returncode, p.stdout + p.stderr


class TestCopylint(unittest.TestCase):
    def test_controls_pass(self) -> None:
        rc, out = run(CLI)
        self.assertEqual(rc, 0, out)
        self.assertIn("controls pass", out)

    def test_machine_text_is_flagged(self) -> None:
        rc, out = run(CLI, "--kind=message", os.path.join(HERE, "corpus", "control-machine.txt"))
        self.assertEqual(rc, 1, out)
        self.assertIn("[M11]", out)

    def test_plain_message_is_clean(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "m.txt")
            with open(p, "w") as f:
                f.write("We close at 6 on Saturdays. Cash or debit, no Amex.\n")
            rc, out = run(CLI, "--kind=message", p)
            self.assertEqual(rc, 0, out)

    def test_broken_control_refuses_a_verdict(self) -> None:
        """Copy the tool, empty the machine corpus: the run must say VACUOUS and exit 2."""
        with tempfile.TemporaryDirectory() as d:
            dst = os.path.join(d, "copy")
            shutil.copytree(HERE, dst, ignore=shutil.ignore_patterns("__pycache__"))
            with open(os.path.join(dst, "corpus", "control-machine.txt"), "w") as f:
                f.write("Plain words only.\n")
            rc, out = run(os.path.join(dst, "copylint.py"), "--kind=message",
                          os.path.join(HERE, "corpus", "control-human.txt"))
            self.assertEqual(rc, 2, out)
            self.assertIn("VACUOUS", out)

    def test_scored_set_has_no_false_positives(self) -> None:
        rc, out = run(os.path.join(HERE, "score.py"), os.path.join(HERE, "corpus", "scored-set.tsv"))
        self.assertIn("FP=0", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
