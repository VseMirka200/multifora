import builtins
import subprocess
import symtable
from pathlib import Path
import unittest


class RepositoryHygieneTests(unittest.TestCase):
    def test_gitattributes_has_no_global_text_disable(self):
        text = Path(".gitattributes").read_text(encoding="utf-8")

        self.assertNotIn("* -text", text)
        self.assertIn("*.py text eol=lf", text)

    def test_sources_do_not_contain_known_mojibake_markers(self):
        markers = (
            "????",
            "\u0420\u045f",
            "\u0420\u0402",
            "\u0420\u045a",
            "\u0420\u0458",
            "\u0420\u2018",
            "\u0420\u0408",
            "\u0420\u00a4",
            "\u0420\u201d",
            "\u0420\u2014",
            "\u0420\u0409",
            "\u0432\u0402",
        )
        paths = [Path(".gitattributes")]
        paths.extend(Path("app").rglob("*.py"))
        paths.extend(Path("core").rglob("*.py"))
        paths.append(Path("multifora_start.py"))

        offenders = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            if any(marker in text for marker in markers):
                offenders.append(str(path))

        self.assertEqual(offenders, [])

    def test_batch_launcher_uses_python_entrypoint(self):
        launcher = Path("start_multifora.bat").read_text(encoding="ascii")

        self.assertTrue(Path("multifora_start.py").is_file())
        self.assertFalse(Path("multifora_start.pyw").exists())
        self.assertIn('set "APP_ENTRY=multifora_start.py"', launcher)
        self.assertIn('"%VENV_PY%" "%~dp0%APP_ENTRY%" %*', launcher)
        self.assertNotIn(".pyw", launcher)

    def test_python_modules_have_no_unresolved_global_names(self):
        paths = list(Path("app").rglob("*.py"))
        paths.extend(Path("core").rglob("*.py"))
        paths.append(Path("multifora_start.py"))
        # Python 3.14 добавляет этот символ при отложенной обработке аннотаций.
        allowed_globals = {"__file__", "__conditional_annotations__"}
        builtin_names = set(dir(builtins))
        offenders = []

        for path in paths:
            source = path.read_text(encoding="utf-8")
            root = symtable.symtable(source, str(path), "exec")
            module_symbols = {symbol.get_name(): symbol for symbol in root.get_symbols()}

            def visit(table):
                for symbol in table.get_symbols():
                    name = symbol.get_name()
                    if (
                        symbol.is_referenced()
                        and symbol.is_global()
                        and name not in builtin_names
                        and name not in allowed_globals
                    ):
                        module_symbol = module_symbols.get(name)
                        is_defined = module_symbol is not None and (
                            module_symbol.is_imported()
                            or module_symbol.is_assigned()
                            or module_symbol.is_namespace()
                            or module_symbol.is_parameter()
                        )
                        if not is_defined:
                            offenders.append(f"{path}: {name}")

                for child in table.get_children():
                    visit(child)

            visit(root)

        self.assertEqual(offenders, [])

    def test_tracked_text_files_are_utf8_without_bom(self):
        tracked_files = subprocess.check_output(["git", "ls-files"], text=True, encoding="utf-8").splitlines()
        binary_suffixes = (
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".ico",
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".zip",
            ".tar.gz",
            ".7z",
            ".rar",
        )

        offenders = []
        for file_name in tracked_files:
            path = Path(file_name)
            if not path.exists():
                continue
            if path.suffix.lower() in binary_suffixes or path.name.endswith(".tar.gz"):
                continue

            data = path.read_bytes()
            if b"\x00" in data[:4096]:
                continue

            if data.startswith(b"\xef\xbb\xbf"):
                offenders.append(f"{file_name} (BOM)")
                continue

            try:
                data.decode("utf-8")
            except UnicodeDecodeError:
                offenders.append(f"{file_name} (non-utf8)")

        self.assertEqual(offenders, [])
