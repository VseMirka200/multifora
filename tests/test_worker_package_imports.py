import subprocess
import sys
import unittest


class WorkerPackageImportTests(unittest.TestCase):
    def test_core_workers_package_import_is_qt_lazy(self):
        script = (
            "import sys; "
            "import core.workers; "
            "print('core.workers.file_worker' in sys.modules)"
        )

        output = subprocess.check_output([sys.executable, "-c", script], text=True, encoding="utf-8").strip()

        self.assertEqual(output, "False")


if __name__ == "__main__":
    unittest.main()
