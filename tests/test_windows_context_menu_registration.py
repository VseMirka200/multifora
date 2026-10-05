import ast
import unittest
from pathlib import Path


class WindowsContextMenuRegistrationTests(unittest.TestCase):
    def test_multiselect_model_invokes_each_selected_path(self):
        source = Path("app/ui/mixins/windows_integration_mixin.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        values = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        values[target.id] = node.value

        value = values.get("_CONTEXT_MENU_MULTISELECT_MODEL")
        self.assertIsInstance(value, ast.Constant)
        self.assertEqual(value.value, "Document")

    def test_context_menu_passes_each_selected_path(self):
        source = Path("app/ui/mixins/windows_integration_mixin.py").read_text(encoding="utf-8")

        self.assertIn("return f'{base_cmd} \"%1\"'", source)
        self.assertNotIn('f"{base_cmd} %*"', source)

    def test_startup_refresh_checks_registered_command(self):
        source = Path("app/ui/mixins/windows_integration_mixin.py").read_text(encoding="utf-8")

        self.assertIn('root + r"\\command"', source)
        self.assertIn('winreg.QueryValueEx(key, "")', source)
        self.assertIn("command).strip() != expected_command", source)

    def test_startup_refreshes_enabled_context_menu_registration(self):
        source = Path("app/ui/ui_main.py").read_text(encoding="utf-8")
        load_pos = source.find("        self.load_settings()")
        ensure_pos = source.find("        self.ensure_context_menu_registration()")
        update_pos = source.find("        self.update_template_combo()")

        self.assertGreaterEqual(load_pos, 0)
        self.assertGreater(ensure_pos, load_pos)
        self.assertGreater(update_pos, ensure_pos)


if __name__ == "__main__":
    unittest.main()
