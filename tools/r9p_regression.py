"""Explicit isolated R.9P native regression; excluded from root test discovery."""
import unittest
from unittest.mock import patch

from tools.r9p_integrated import BoundaryError, supervise, run


class IntegratedNativeRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run()

    def test_all_ten_acceptance_criteria(self):
        self.assertTrue(self.result["passed"])
        self.assertEqual(len(self.result["acceptance"]), 10)
        self.assertTrue(all(self.result["acceptance"].values()))

    def test_successful_layout_meter_accounting(self):
        self.assertEqual([item["page_size"] for item in self.result["layouts"]], [512, 1024, 4096])
        for item in self.result["layouts"]:
            meter = item["payload"]["diagnostic"]
            self.assertEqual(meter["requested"], meter["reserved"])
            self.assertEqual(meter["reserved"], meter["delegated"])
            self.assertEqual(meter["delegated"], meter["returned"])
            self.assertEqual(item["projection"]["terminal"], "SYNTHETIC_AUDIT_COMPLETED")

    def test_failures_never_publish_success(self):
        for item in self.result["cases"].values():
            self.assertFalse(item["success_present"])
            self.assertIn(item["projection"]["terminal"], {
                "SYNTHETIC_AUDIT_FAILED", "SYNTHETIC_AUDIT_INCOMPLETE_AFTER_CRASH"
            })

    def test_job_timeout_kills_descendant(self):
        observed = self.result["cases"]["timeout_descendant"]["containment"]
        self.assertTrue(observed["assigned_before_resume"])
        self.assertTrue(observed["timed_out"])
        self.assertTrue(observed["descendant_dead"])

    def test_job_creation_failure_starts_no_worker(self):
        with patch("tools.r9p_integrated.create_job", side_effect=BoundaryError("injected")), \
             patch("tools.r9p_integrated.spawn_suspended") as spawn:
            with self.assertRaises(BoundaryError):
                supervise(None, {"attempt_id": "attempt-0000000000000000"}, "normal")
            spawn.assert_not_called()

    def test_assignment_failure_never_resumes_worker(self):
        calls = []
        class Kernel:
            def AssignProcessToJobObject(self, job, process): calls.append("assign"); return 0
            def ResumeThread(self, thread): calls.append("resume"); return 1
        class FakeNative:
            k = Kernel()
            def check(self, value):
                if not value: raise BoundaryError("injected assignment failure")
                return value
            def close(self, value): calls.append("close")
        process = type("Process", (), {"process": 1, "thread": 2})()
        root = type("Root", (), {"name": "case-0000000000000000"})()
        with patch("tools.r9p_integrated.create_job", return_value=(FakeNative(), 3)), \
             patch("tools.r9p_integrated.spawn_suspended", return_value=(FakeNative(), process)), \
             patch("tools.r9p_integrated._dead", return_value=True):
            with self.assertRaises(BoundaryError):
                supervise(root, {"attempt_id": "attempt-0000000000000000"}, "normal")
        self.assertIn("assign", calls)
        self.assertNotIn("resume", calls)


if __name__ == "__main__":
    unittest.main()
