from notify import notify_nick
import unittest
from unittest import mock


class TestNotifyNick(unittest.TestCase):
    """Spec 06 contract + llama-failover.sh channel pattern (HTTP mocked)."""

    def test_invalid_urgency_raises(self):
        # urgency must be 'pause' or 'inform' (spec 06); anything else raises
        with self.assertRaises(ValueError):
            notify_nick("hello", "banana", "taza-ops")

    @mock.patch("notify._post", return_value=200)
    def test_primary_success_single_fire(self, post):
        # fires exactly once per call: no fallback attempt when primary 2xx
        result = notify_nick("GPU->CPU", "pause", "taza-ops")
        self.assertTrue(result["sent"])
        self.assertEqual(result["channel"], "primary")
        self.assertEqual(result["url"], "https://ntfy.sh/taza-ops")
        self.assertEqual(result["status"], 200)
        post.assert_called_once_with("https://ntfy.sh/taza-ops", "GPU->CPU", "pause")

    @mock.patch("notify._post", side_effect=[429, 200])
    def test_primary_non2xx_fallback_succeeds(self, post):
        # 429 quota-exhausted (observed 2026-08-01) -> self-hosted fallback
        result = notify_nick("DOWN", "pause", "taza-ops")
        self.assertTrue(result["sent"])
        self.assertEqual(result["channel"], "fallback")
        self.assertEqual(result["url"], "http://192.168.2.102:2586/taza-llama-alerts")
        self.assertEqual(post.call_count, 2)

    @mock.patch("notify._post", side_effect=[429, 0])
    def test_both_fail_reported(self, post):
        # both channels fail -> sent=False, channel=None, errors keyed per channel
        result = notify_nick("DOWN", "pause", "taza-ops")
        self.assertFalse(result["sent"])
        self.assertIsNone(result["channel"])
        self.assertEqual(result["errors"], {"primary": 429, "fallback": 0})
        self.assertEqual(post.call_count, 2)


if __name__ == "__main__":
    unittest.main()
