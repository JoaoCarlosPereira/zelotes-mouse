import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from zelotes_mouse.gui import PanelHandler


class GuiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), PanelHandler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_page_has_the_controls(self) -> None:
        with urllib.request.urlopen(self._url("/")) as response:
            html = response.read().decode("utf-8")
        self.assertIn("C-18", html)
        self.assertIn("Aplicar", html)
        self.assertIn("Polling", html)
        self.assertIn("/api/apply", html)

    def test_status_is_json(self) -> None:
        with urllib.request.urlopen(self._url("/api/status")) as response:
            data = json.load(response)
        self.assertIn(data["state"], {"ready", "denied", "absent", "error"})

    def test_apply_rejects_bad_polling(self) -> None:
        body = json.dumps({"perfil": 1, "hz": 2000}).encode()
        request = urllib.request.Request(
            self._url("/api/apply"),
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request)
        self.assertEqual(caught.exception.code, 400)

    def test_capabilities_lists_light_and_withholds_buttons(self) -> None:
        with urllib.request.urlopen(self._url("/api/capabilities")) as response:
            data = json.load(response)
        self.assertIn("luz", data["implementado"])
        self.assertTrue(data["ainda_nao_enviado"])
        self.assertIn("macro", data["nota"])

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"


if __name__ == "__main__":
    unittest.main()
