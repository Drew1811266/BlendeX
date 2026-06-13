import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from blendex_protocol.errors import BlendexError

from blender_addon.blendex import server
from blender_addon.blendex.state import STATE


class AuthHeaderTests(unittest.TestCase):
    def setUp(self):
        self.original_session_token = STATE.session_token
        self.had_client_authenticated = hasattr(STATE, "client_authenticated")
        self.original_client_authenticated = getattr(STATE, "client_authenticated", None)
        self.had_last_auth_error = hasattr(STATE, "last_auth_error")
        self.original_last_auth_error = getattr(STATE, "last_auth_error", None)

        STATE.session_token = "secret-token"
        STATE.client_authenticated = False
        STATE.last_auth_error = ""

    def tearDown(self):
        STATE.session_token = self.original_session_token
        if self.had_client_authenticated:
            STATE.client_authenticated = self.original_client_authenticated
        else:
            delattr(STATE, "client_authenticated")
        if self.had_last_auth_error:
            STATE.last_auth_error = self.original_last_auth_error
        else:
            delattr(STATE, "last_auth_error")

    def test_validate_auth_headers_accepts_matching_token(self):
        server._validate_auth_headers({"x-blendex-token": "secret-token"})

        self.assertTrue(STATE.client_authenticated)
        self.assertEqual(STATE.last_auth_error, "")

    def test_validate_auth_headers_rejects_missing_token(self):
        with self.assertRaises(BlendexError) as raised:
            server._validate_auth_headers({})

        self.assertEqual(raised.exception.code, "AUTH_REQUIRED")
        self.assertFalse(STATE.client_authenticated)
        self.assertEqual(STATE.last_auth_error, "Missing BlendeX token.")

    def test_validate_auth_headers_rejects_wrong_token(self):
        with self.assertRaises(BlendexError) as raised:
            server._validate_auth_headers({"x-blendex-token": "wrong-token"})

        self.assertEqual(raised.exception.code, "AUTH_FAILED")
        self.assertFalse(STATE.client_authenticated)
        self.assertEqual(STATE.last_auth_error, "Invalid BlendeX token.")


if __name__ == "__main__":
    unittest.main()
