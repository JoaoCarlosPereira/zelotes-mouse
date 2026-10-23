import json
import os
import tempfile
import unittest
from pathlib import Path

from zelotes_mouse.i18n import assignment_label, profile_name, tr
from zelotes_mouse.launcher import autostart_path
from zelotes_mouse.preferences import load_preferences, save_preferences
from zelotes_mouse.preferences import Preferences


class PreferencesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._home = tempfile.TemporaryDirectory()
        self._old = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = self._home.name

    def tearDown(self) -> None:
        if self._old is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = self._old
        self._home.cleanup()

    def test_language_roundtrip(self) -> None:
        self.assertEqual(tr("pt-BR", "tab.settings"), "Configuração")
        self.assertEqual(tr("en", "tab.settings"), "Settings")
        self.assertEqual(assignment_label("en", "Clique"), "Click")
        self.assertEqual(assignment_label("pt-BR", "Space"), "Espaço")
        self.assertEqual(assignment_label("en", "click"), "Click")
        self.assertEqual(profile_name("en", "Padrão 1", 1), "Default 1")
        self.assertEqual(profile_name("pt-BR", "Meu jogo", 1), "Meu jogo")

    def test_autostart_follows_the_saved_choice(self) -> None:
        save_preferences(Preferences(idioma="en", iniciar_com_sistema=True))
        loaded = load_preferences()
        self.assertEqual(loaded.idioma, "en")
        self.assertTrue(loaded.iniciar_com_sistema)
        entry = autostart_path()
        text = entry.read_text(encoding="utf-8")
        self.assertIn("X-GNOME-Autostart-enabled=true", text)
        self.assertIn("Exec=", text)
        save_preferences(Preferences(idioma="pt-BR", iniciar_com_sistema=False))
        self.assertFalse(entry.exists())
        payload = json.loads(Path(self._home.name, "zelotes-mouse", "preferences.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["idioma"], "pt-BR")
        self.assertFalse(payload["iniciar_com_sistema"])

    def test_marker_positions_roundtrip(self) -> None:
        save_preferences(Preferences(marcadores={3: (0.695, 0.19), 11: (0.38, 0.42)}))
        loaded = load_preferences()
        self.assertIsNotNone(loaded.marcadores)
        assert loaded.marcadores is not None
        self.assertAlmostEqual(loaded.marcadores[3][0], 0.695)
        self.assertAlmostEqual(loaded.marcadores[11][1], 0.42)
        self.assertNotIn(4, loaded.marcadores)


if __name__ == "__main__":
    unittest.main()
