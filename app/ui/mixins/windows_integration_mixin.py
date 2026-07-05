import os
import shutil
import subprocess
import sys
import winreg
import ctypes

from PyQt6.QtCore import Qt, QStandardPaths
from PyQt6.QtWidgets import QMessageBox

from app.core.app_identity import APP_DISPLAY_NAME
from app.core.app_utils import _debug_log
from app.core.app_icons import _get_shortcut_icon_path


class WindowsIntegrationMixin:
    def get_pythonw_path(self):
        """Получает путь к pythonw.exe."""
        try:
            python_exe = sys.executable
            python_dir = os.path.dirname(python_exe)
            pythonw_names = [
                "pythonw.exe",
                "pythonw",
                os.path.basename(python_exe).replace("python", "pythonw"),
            ]
            for name in pythonw_names:
                pythonw_path = os.path.join(python_dir, name)
                if os.path.exists(pythonw_path):
                    return pythonw_path
            for name in ["pythonw.exe", "pythonw"]:
                pythonw_path = shutil.which(name)
                if pythonw_path:
                    return pythonw_path
            return None
        except Exception as exc:
            _debug_log(f"Ошибка получения пути к pythonw.exe: {exc}")
            return None

    def is_context_menu_registered(self):
        """Проверяет, зарегистрировано ли контекстное меню в реестре (HKCU)."""
        try:
            for key_path in [
                r"Software\Classes\*\shell\AddToMultifora",
                r"Software\Classes\Directory\shell\AddToMultifora",
            ]:
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ):
                        return True
                except FileNotFoundError:
                    continue
            return False
        except Exception:
            return False

    def register_context_menu(self):
        """Регистрирует пункт контекстного меню Windows (HKCU, без админа)."""
        try:
            exe_path = os.path.abspath(sys.argv[0])
            pythonw_path = None
            if exe_path.lower().endswith(".pyw"):
                pythonw_path = self.get_pythonw_path() or sys.executable
                base_cmd = f"\"{pythonw_path}\" \"{exe_path}\""
            elif exe_path.lower().endswith(".py"):
                base_cmd = f"\"{sys.executable}\" \"{exe_path}\""
            else:
                base_cmd = f"\"{exe_path}\""

            icon_path = _get_shortcut_icon_path()
            if not icon_path:
                if exe_path.lower().endswith(".pyw"):
                    icon_path = pythonw_path or sys.executable
                elif exe_path.lower().endswith(".py"):
                    icon_path = sys.executable
                else:
                    icon_path = exe_path
            if icon_path:
                if icon_path.lower().endswith((".exe", ".dll")):
                    icon_value = f"\"{icon_path}\",0"
                else:
                    icon_value = f"\"{icon_path}\""
            else:
                icon_value = None

            self.unregister_context_menu_silent()
            self.log_event("Регистрирую контекстное меню...")
            roots = [
                r"Software\Classes\*\shell\AddToMultifora",
                r"Software\Classes\Directory\shell\AddToMultifora",
            ]
            for root in roots:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, root) as key:
                    winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "Добавить в Мультифору")
                    # Document mode lets Explorer pass the full multi-selection to the verb.
                    winreg.SetValueEx(key, "MultiSelectModel", 0, winreg.REG_SZ, "Document")
                    if icon_value:
                        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon_value)
                cmd_key = root + r"\command"
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cmd_key) as key:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f"{base_cmd} %*")

            self.log_event("✓ Контекстное меню успешно добавлено!")
            self.log_event(f"Команда: {base_cmd} %*", "INFO")
            return True
        except Exception as exc:
            self.log_event(f"Ошибка регистрации контекстного меню: {exc}", "ERROR")
            try:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось добавить контекстное меню.\n\n{exc}",
                )
            except Exception:
                pass
            return False

    def unregister_context_menu_silent(self):
        def _del_tree(root_key, subkey):
            try:
                with winreg.OpenKey(root_key, subkey, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                    i = 0
                    while True:
                        try:
                            child = winreg.EnumKey(key, i)
                            _del_tree(root_key, subkey + "\\" + child)
                        except OSError:
                            break
                        i += 1
            except Exception:
                return
            try:
                winreg.DeleteKey(root_key, subkey)
            except Exception:
                pass

        try:
            for sub in [
                r"Software\Classes\*\shell\Multifora",
                r"Software\Classes\Directory\shell\Multifora",
                r"Software\Classes\Directory\Background\shell\Multifora",
            ]:
                _del_tree(winreg.HKEY_CURRENT_USER, sub)
            for sub in [
                r"Software\Classes\*\shell\AddToMultifora",
                r"Software\Classes\Directory\shell\AddToMultifora",
                r"Software\Classes\Directory\Background\shell\AddToMultifora",
            ]:
                _del_tree(winreg.HKEY_CURRENT_USER, sub)
        except Exception:
            pass

    def unregister_context_menu(self):
        """Удаляет контекстное меню (HKCU, без админ-прав)."""
        try:
            self.unregister_context_menu_silent()
            return True
        except Exception as exc:
            self.log_event(f"Ошибка удаления контекстного меню: {exc}", "ERROR")
            try:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить контекстное меню.\n\n{exc}")
            except Exception:
                pass
            return False

    def toggle_context_menu(self, state):
        """Вкл/выкл пункта контекстного меню."""
        if not getattr(self, "initial_load_complete", False):
            return
        checked = state == Qt.CheckState.Checked.value
        if getattr(self, "_context_menu_toggle_in_progress", False):
            return

        self._context_menu_toggle_in_progress = True
        try:
            if checked:
                success = self.register_context_menu()
                if success:
                    self.windows_context_menu_enabled = True
                    self.save_settings()
                    self.status_bar.showMessage("✓ Контекстное меню добавлено")
                    self.refresh_shell_context_menu()
                    QMessageBox.information(
                        self,
                        "Контекстное меню добавлено",
                        "Пункт 'Добавить в Мультифору' добавлен в контекстное меню."
                        "Теперь вы можете:"
                        "1. Выделить файлы или папки"
                        "2. Нажать правой кнопкой мыши"
                        "3. Выбрать 'Добавить в Мультифору'",
                    )
                else:
                    self.context_menu_checkbox.blockSignals(True)
                    self.context_menu_checkbox.setChecked(False)
                    self.context_menu_checkbox.blockSignals(False)
                    QMessageBox.warning(self, "Ошибка", "Не удалось добавить контекстное меню. Проверьте права доступа.")
            else:
                success = self.unregister_context_menu()
                if success:
                    self.windows_context_menu_enabled = False
                    self.save_settings()
                    self.status_bar.showMessage("✓ Контекстное меню удалено")
                    self.refresh_shell_context_menu()
                else:
                    self.context_menu_checkbox.blockSignals(True)
                    self.context_menu_checkbox.setChecked(True)
                    self.context_menu_checkbox.blockSignals(False)
                    QMessageBox.warning(self, "Ошибка", "Не удалось удалить контекстное меню. Возможно, нет прав доступа.")
        finally:
            self._context_menu_toggle_in_progress = False

    def refresh_shell_context_menu(self):
        """Обновляет кэш контекстного меню Windows Explorer."""
        if os.name != "nt":
            return
        try:
            SHCNE_ASSOCCHANGED = 0x08000000
            SHCNF_IDLIST = 0x0000
            ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
        except Exception:
            pass

    def get_desktop_shortcut_path(self):
        """Возвращает путь ярлыка на рабочем столе."""
        try:
            desktop_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
            if not desktop_dir:
                desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        except Exception:
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        return os.path.join(desktop_dir, f"{APP_DISPLAY_NAME}.lnk")

    def get_start_menu_shortcut_path(self):
        """Возвращает путь ярлыка в меню Пуск."""
        try:
            start_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.ApplicationsLocation)
            if not start_dir:
                start_dir = os.path.join(
                    os.path.expanduser("~"),
                    "AppData",
                    "Roaming",
                    "Microsoft",
                    "Windows",
                    "Start Menu",
                    "Programs",
                )
        except Exception:
            start_dir = os.path.join(
                os.path.expanduser("~"),
                "AppData",
                "Roaming",
                "Microsoft",
                "Windows",
                "Start Menu",
                "Programs",
            )
        return os.path.join(start_dir, f"{APP_DISPLAY_NAME}.lnk")

    def _escape_ps(self, value: str) -> str:
        return value.replace("'", "''")

    def create_windows_shortcut(self, shortcut_path: str, silent: bool = False) -> bool:
        """Создает ярлык Windows (.lnk)."""
        try:
            try:
                os.makedirs(os.path.dirname(shortcut_path), exist_ok=True)
            except Exception:
                pass
            shortcut_exists = os.path.exists(shortcut_path)
            target_path = sys.executable
            args = ""
            try:
                if not getattr(sys, "frozen", False):
                    script_path = os.path.abspath(sys.argv[0])
                    args = f'"{script_path}"'
            except Exception:
                args = ""

            working_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            icon_path = _get_shortcut_icon_path()
            if not icon_path and shortcut_exists:
                # Не затираем уже существующий ярлык, если иконка временно недоступна.
                self.log_event(
                    f"Иконка ярлыка недоступна, сохраняю существующий ярлык без изменений: {shortcut_path}",
                    "INFO",
                )
                return True
            ps_target = self._escape_ps(target_path)
            ps_args = self._escape_ps(args)
            ps_workdir = self._escape_ps(working_dir)
            ps_shortcut = self._escape_ps(shortcut_path)
            ps_icon = self._escape_ps(icon_path) if icon_path else ""
            ps_script = (
                f"$WshShell = New-Object -ComObject WScript.Shell; "
                f"$Shortcut = $WshShell.CreateShortcut('{ps_shortcut}'); "
                f"$Shortcut.TargetPath = '{ps_target}'; "
                f"$Shortcut.Arguments = '{ps_args}'; "
                f"$Shortcut.WorkingDirectory = '{ps_workdir}'; "
                f"if (Test-Path '{ps_icon}') {{ $Shortcut.IconLocation = '{ps_icon},0'; }} "
                f"$Shortcut.Save();"
            )

            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                if not silent:
                    QMessageBox.warning(self, "Ошибка", f"Не удалось создать ярлык: {result.stderr}")
                self.log_event(f"Ошибка создания ярлыка: {result.stderr}", "ERROR")
                return False
            return True
        except Exception as exc:
            if not silent:
                QMessageBox.warning(self, "Ошибка", f"Не удалось создать ярлык: {exc}")
            self.log_event(f"Ошибка создания ярлыка: {exc}", "ERROR")
            return False

    def remove_windows_shortcut(self, shortcut_path: str, silent: bool = False) -> bool:
        """Удаляет ярлык Windows (.lnk)."""
        try:
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
            return True
        except Exception as exc:
            if not silent:
                QMessageBox.warning(self, "Ошибка", f"Не удалось удалить ярлык: {exc}")
            self.log_event(f"Ошибка удаления ярлыка: {exc}", "ERROR")
            return False

    def apply_shortcut_settings(self, silent: bool = False):
        """Применяет настройки ярлыков без лишних уведомлений."""
        if self.desktop_shortcut_enabled:
            self.create_windows_shortcut(self.get_desktop_shortcut_path(), silent=True)
        else:
            self.remove_windows_shortcut(self.get_desktop_shortcut_path(), silent=True)
        if self.start_menu_shortcut_enabled:
            self.create_windows_shortcut(self.get_start_menu_shortcut_path(), silent=True)
        else:
            self.remove_windows_shortcut(self.get_start_menu_shortcut_path(), silent=True)
        if not silent:
            self.status_bar.showMessage("Настройки ярлыков применены")

    def toggle_desktop_shortcut(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.desktop_shortcut_enabled = enabled
        if enabled:
            ok = self.create_windows_shortcut(self.get_desktop_shortcut_path())
        else:
            ok = self.remove_windows_shortcut(self.get_desktop_shortcut_path())
        if ok:
            self.save_settings()

    def toggle_start_menu_shortcut(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.start_menu_shortcut_enabled = enabled
        if enabled:
            ok = self.create_windows_shortcut(self.get_start_menu_shortcut_path())
        else:
            ok = self.remove_windows_shortcut(self.get_start_menu_shortcut_path())
        if ok:
            self.save_settings()
