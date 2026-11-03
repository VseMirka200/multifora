"""Exercise result delivery across a real Qt worker thread."""

import subprocess
import sys
import textwrap


def test_rename_result_reaches_gui_thread_once():
    script = textwrap.dedent('''
        import tempfile
        from pathlib import Path

        from PySide6.QtCore import QCoreApplication, QObject, QThread, QTimer, Slot

        from app.core.models import FileItem
        from core.workers.rename_worker import RenameWorker

        app = QCoreApplication([])

        class Receiver(QObject):
            def __init__(self):
                super().__init__()
                self.results = []
                self.threads = []

            @Slot(object)
            def receive(self, result):
                self.results.append(result)
                self.threads.append(QThread.currentThread())
                app.quit()

        receiver = Receiver()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "before.txt")
            source.write_text("preserved", encoding="utf-8")
            worker = RenameWorker()
            worker.set_rename([FileItem(str(source))], ["after.txt"])
            worker.finished.connect(receiver.receive)
            QTimer.singleShot(5000, app.quit)
            worker.start()
            app.exec()
            assert worker.wait(5000)
            app.processEvents()
            assert len(receiver.results) == 1
            assert receiver.threads == [app.thread()]
            assert not receiver.results[0].errors
            assert Path(directory, "after.txt").read_text(encoding="utf-8") == "preserved"
    ''')
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
