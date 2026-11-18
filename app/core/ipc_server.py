"""Локальный транспорт Qt для получения файлов от другого экземпляра Мультифоры."""

import hmac
import os

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from app.core.app_ipc import _get_ipc_server_name, _load_ipc_token, _normalize_path_candidate


class LocalFileServer(QObject):
    files_received = Signal(list)
    files_queued = Signal()

    def __init__(self, log, parent=None):
        super().__init__(parent)
        self._log = log
        self._server: QLocalServer | None = None
        self._buffers: dict[QLocalSocket, bytearray] = {}
        self._pending_paths: list[str] = []
        self._batch_timer = QTimer(self)
        self._batch_timer.setSingleShot(True)
        self._batch_timer.setInterval(350)
        self._batch_timer.timeout.connect(self.flush)

    def start(self) -> None:
        """Создает IPC-сервер для приема файлов от других экземпляров."""
        if self._server is not None:
            return
        token = _load_ipc_token()
        if not token:
            self._log("IPC сервер не запущен: токен недоступен", "ERROR")
            return
        self._server = QLocalServer(self)
        server_name = _get_ipc_server_name(token)
        try:
            QLocalServer.removeServer(server_name)
        except Exception as e:
            self._log(f"Ошибка IPC при removeServer: {e}", "WARN")

        if not self._server.listen(server_name):
            self._log(
                f"IPC сервер не запущен: {self._server.errorString()}",
                "ERROR",
            )
            self.close()
            return

        self._server.newConnection.connect(self._on_ipc_connection)
        self._log(f"IPC сервер запущен: {server_name}")

    def _on_ipc_connection(self):
        """Обрабатывает IPC по событиям Qt, не блокируя интерфейс на чтении."""
        if not self._server:
            return
        while self._server.hasPendingConnections():
            connection = self._server.nextPendingConnection()
            if connection is None:
                continue
            self._buffers[connection] = bytearray()
            connection.readyRead.connect(
                lambda socket=connection: self._read_ipc_socket(socket)
            )
            connection.disconnected.connect(
                lambda socket=connection: self._finish_ipc_socket(socket)
            )
            QTimer.singleShot(
                5000, self, lambda socket=connection: self._expire_ipc_socket(socket)
            )
            self._read_ipc_socket(connection)

    def _read_ipc_socket(self, socket_conn):
        """Считывает только доступные байты, без waitForReadyRead в GUI-потоке."""
        buffer = self._buffers.get(socket_conn)
        if buffer is None:
            return
        buffer.extend(bytes(socket_conn.readAll()))
        if len(buffer) > 1024 * 1024:
            self._log("IPC: превышен лимит данных", "WARN")
            self._buffers.pop(socket_conn, None)
            socket_conn.disconnectFromServer()
            socket_conn.deleteLater()
            return
        if (
            socket_conn.state()
            == QLocalSocket.LocalSocketState.UnconnectedState
        ):
            self._finish_ipc_socket(socket_conn)

    def _expire_ipc_socket(self, socket_conn):
        if socket_conn not in self._buffers:
            return
        self._log("IPC: соединение не завершено за 5 секунд", "WARN")
        self._buffers.pop(socket_conn, None)
        socket_conn.disconnectFromServer()
        socket_conn.deleteLater()

    def _finish_ipc_socket(self, socket_conn):
        buffer = self._buffers.pop(socket_conn, None)
        if buffer is None:
            return
        try:
            buffer.extend(bytes(socket_conn.readAll()))
        finally:
            socket_conn.deleteLater()
        if len(buffer) > 1024 * 1024:
            self._log("IPC: превышен лимит данных", "WARN")
            return
        self._process_ipc_payload(bytes(buffer))

    def _process_ipc_payload(self, data: bytes):
        if not data:
            return
        lines = data.decode("utf-8", errors="replace").splitlines()
        if not lines:
            return
        token = _load_ipc_token()
        if (
            not token
            or not lines[0].startswith("TOKEN:")
            or not hmac.compare_digest(lines[0][6:], token)
        ):
            self._log("IPC: неверный токен", "WARN")
            return
        file_paths = []
        for line in lines[1:]:
            if line.startswith("ADD_FILE:"):
                file_path = _normalize_path_candidate(line[9:].strip())
                if file_path and os.path.exists(file_path):
                    file_paths.append(file_path)
        if file_paths:
            self.enqueue(file_paths)
        else:
            self._log("IPC: нет допустимых файлов", "WARN")

    def enqueue(self, file_paths: list[str]) -> None:
        if file_paths:
            self._pending_paths.extend(file_paths)
            self._batch_timer.start()
            self.files_queued.emit()

    def flush(self) -> None:
        self._batch_timer.stop()
        paths, self._pending_paths = self._pending_paths, []
        if paths:
            self.files_received.emit(paths)

    def close(self) -> None:
        self._batch_timer.stop()
        self._pending_paths.clear()
        connections = list(self._buffers)
        self._buffers.clear()
        for connection in connections:
            connection.disconnectFromServer()
            connection.deleteLater()
        if self._server is not None:
            self._server.close()
            self._server.deleteLater()
            self._server = None
