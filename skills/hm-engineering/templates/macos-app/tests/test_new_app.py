"""Tests for new_app.py (stdlib). Run: python3 -m unittest discover -s tests"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import new_app


class TargetNameTest(unittest.TestCase):
    def test_spaces_and_accents_become_a_swift_identifier(self) -> None:
        self.assertEqual(new_app.target_name("Análise Ção App"), "AnaliseCaoApp")
        self.assertEqual(new_app.target_name("meu app"), "MeuApp")
        self.assertEqual(new_app.target_name("3D Studio"), "App3DStudio")


class CreateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())

    def test_name_with_space_and_accent_generates_a_clean_project(self) -> None:
        dest = new_app.create("Análise Ção", "com.example.analise", self.root / "Análise Ção")
        self.assertTrue((dest / "Sources" / "AnaliseCao" / "main.swift").exists())
        self.assertTrue((dest / "Tests" / "AnaliseCaoTests" / "LayoutTests.swift").exists())
        pkg = (dest / "Package.swift").read_text(encoding="utf-8")
        self.assertIn('name: "AnaliseCao"', pkg)
        install = (dest / "scripts" / "install.sh").read_text(encoding="utf-8")
        self.assertIn('NAME="Análise Ção"', install)
        self.assertIn('BUNDLE_ID="com.example.analise"', install)
        self.assertTrue((dest / "scripts" / "install.sh").stat().st_mode & 0o111)  # stays executable
        self.assertTrue((dest / ".git").is_dir())  # born versioned, first commit made
        for f in dest.rglob("*"):
            if f.is_file():
                text = f.read_text(encoding="utf-8", errors="ignore")
                for token in ("__APP_NAME__", "__TARGET__", "__BUNDLE_ID__"):
                    self.assertNotIn(token, text, f"{token} left in {f}")
                    self.assertNotIn(token, str(f))

    def test_generated_app_carries_the_behaviors_three_apps_missed(self) -> None:
        # menu Editar (⌘V/⌘C), duplo clique na barra de título e mãozinha em todo clicável: cada um saiu
        # faltando em app gerado e foi reprovado pelo dono; o starter não pode voltar a nascer sem eles
        dest = self.root / "Comportamentos"
        new_app.create("Comportamentos", "com.example.comportamentos", dest)
        src = "\n".join(f.read_text(encoding="utf-8") for f in (dest / "Sources").rglob("*.swift"))
        for symbol in ("NSApp.mainMenu = main", "#selector(NSText.paste(_:))", "MainMenu.install(",
                       "enum TitleBand", "AppleActionOnDoubleClick", "addLocalMonitorForEvents(matching: .leftMouseDown)",
                       "struct ClickableStyle", ".pointerStyle(enabled ? .link : nil)"):
            self.assertIn(symbol, src)
        self.assertNotIn(".buttonStyle(.plain)", src)
        tests = (dest / "Tests" / "ComportamentosTests" / "LayoutTests.swift").read_text(encoding="utf-8")
        for name in ("doubleClickZoomsOnlyInTheFreeBandOfTheTitleBar", "menuBarCarriesTheEditShortcuts", "everyClickableUsesThePointerStyle"):
            self.assertIn(name, tests)

    def test_existing_destination_is_refused_and_untouched(self) -> None:
        dest = self.root / "existing"
        dest.mkdir()
        (dest / "keep.txt").write_text("user data", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            new_app.create("Algo", "com.example.algo", dest)
        self.assertEqual([p.name for p in dest.iterdir()], ["keep.txt"])
        self.assertEqual((dest / "keep.txt").read_text(encoding="utf-8"), "user data")

    def test_invalid_inputs_are_refused_before_writing(self) -> None:
        for name, bid in (("Ok", "semponto"), ("Ok", "com..x"), ("a/b", "com.example.x"), ("", "com.example.x")):
            with self.assertRaises(ValueError):
                new_app.create(name, bid, self.root / "never")
        self.assertFalse((self.root / "never").exists())

    def test_cli_returns_2_on_existing_destination(self) -> None:
        dest = self.root / "cli"
        dest.mkdir()
        self.assertEqual(new_app.main(["Algo", "com.example.algo", str(dest)]), 2)


if __name__ == "__main__":
    unittest.main()
