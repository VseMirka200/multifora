import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core import app_ipc


class _SocketStub:
    instances = []

    def __init__(self):
        self.server_name = None
        self.payload = b""
        self.disconnected = False
        self.__class__.instances.append(self)

    def connectToServer(self, server_name):
        self.server_name = server_name

    def waitForConnected(self, _timeout):
        return True

    def write(self, payload):
        self.payload = payload

    def flush(self):
        return None

    def waitForBytesWritten(self, _timeout):
        return True

    def disconnectFromServer(self):
        self.disconnected = True


class AppIpcTests(unittest.TestCase):
    def test_collect_paths_filters_options_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = Path(tmp_dir, "source file.pdf")
            source.write_bytes(b"pdf")

            result = app_ipc._collect_paths_from_args(
                ["--silent", str(source), str(source), "missing.pdf"]
            )

        self.assertEqual(result, [str(source)])

    def test_collect_paths_accepts_more_than_15_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            sources = []
            for index in range(20):
                source = Path(tmp_dir, f"sample_{index:02d}.png")
                source.write_bytes(b"sample")
                sources.append(str(source))

            result = app_ipc._collect_paths_from_args(sources)

        self.assertEqual(result, sources)
        self.assertGreater(len(result), 15)

    def test_normalize_file_url(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = Path(tmp_dir, "source file.pdf")
            source.write_bytes(b"pdf")

            result = app_ipc._collect_paths_from_args([source.as_uri()])

        self.assertEqual(result, [str(source)])

    def test_drain_queue_deduplicates_paths_and_removes_queue_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir, tempfile.TemporaryDirectory() as files_dir:
            source = Path(files_dir, "source.pdf")
            source.write_bytes(b"pdf")
            first_queue = Path(tmp_dir, "queue_1.txt")
            second_queue = Path(tmp_dir, "queue_2.txt")
            first_queue.write_text(f"{source}\n{source}\n", encoding="utf-8")
            second_queue.write_text(f"missing.pdf\n{source}\n", encoding="utf-8")

            with patch.object(app_ipc, "_get_queue_dir", return_value=tmp_dir):
                result = app_ipc._drain_queued_files()

            self.assertEqual(result, [str(source)])
            self.assertFalse(first_queue.exists())
            self.assertFalse(second_queue.exists())

    def test_send_files_uses_existing_wire_format(self):
        _SocketStub.instances.clear()
        files = [r"C:\docs\one.pdf", r"C:\docs\two.docx"]

        with patch.object(app_ipc, "QLocalSocket", _SocketStub), \
            patch.object(app_ipc, "_load_ipc_token", return_value="secret"), \
            patch.object(app_ipc, "_get_ipc_server_name", return_value="Multifora_IPC_test"):
            sent = app_ipc.send_files_to_running_instance(files, retries=1, delay=0)

        self.assertTrue(sent)
        self.assertEqual(len(_SocketStub.instances), 1)
        socket = _SocketStub.instances[0]
        self.assertEqual(socket.server_name, "Multifora_IPC_test")
        self.assertEqual(
            socket.payload,
            b"TOKEN:secret\nADD_FILE:C:\\docs\\one.pdf\nADD_FILE:C:\\docs\\two.docx\n",
        )
        self.assertTrue(socket.disconnected)

    def test_non_windows_first_instance_does_not_call_win32(self):
        if os.name == "nt":
            self.skipTest("Проверка предназначена для неплатформенного пути")

        with patch.object(app_ipc.ctypes, "WinDLL", create=True) as win_dll:
            self.assertTrue(app_ipc.is_first_instance())

        win_dll.assert_not_called()


if __name__ == "__main__":
    unittest.main()
