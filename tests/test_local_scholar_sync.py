import datetime as dt
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "local_scholar_sync.py"
SPEC = importlib.util.spec_from_file_location("local_scholar_sync", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class LocalScholarSyncTests(unittest.TestCase):
    def test_github_workflow_is_manual_backup_only(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "scholar-sync.yml").read_text()

        self.assertNotIn("  schedule:\n", workflow)

    def test_launch_agent_is_scheduled_without_keep_alive(self):
        plist = MODULE.build_launch_agent(
            python_executable="/usr/local/bin/python3",
            installed_script=Path("/tmp/local_scholar_sync.py"),
            log_path=Path("/tmp/local_scholar_sync.log"),
        )

        self.assertNotIn("KeepAlive", plist)
        self.assertEqual(plist["ProcessType"], "Background")
        self.assertTrue(plist["LowPriorityIO"])
        self.assertEqual(plist["StartCalendarInterval"], {"Hour": 9, "Minute": 0})
        self.assertEqual(plist["ProgramArguments"][-1], "--run")

    def test_same_day_success_skips_duplicate_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            publications_path = Path(tmp) / "publications.json"
            publications_path.write_text(
                json.dumps({"source": {"last_successful_sync_at": "2026-08-26T15:54:47+00:00"}}),
                encoding="utf-8",
            )

            self.assertTrue(MODULE.synced_on_date(publications_path, dt.date(2026, 8, 26)))
            self.assertFalse(MODULE.synced_on_date(publications_path, dt.date(2026, 8, 27)))

    def test_invalid_data_does_not_suppress_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            publications_path = Path(tmp) / "publications.json"
            publications_path.write_text("not-json", encoding="utf-8")

            self.assertFalse(MODULE.synced_on_date(publications_path, dt.date(2026, 8, 26)))


if __name__ == "__main__":
    unittest.main()
