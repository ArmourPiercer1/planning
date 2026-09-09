"""Tests for the IoT service (all must keep passing)."""

import unittest

from iot import devices
from iot.gateway import EVENTS, Gateway
from iot.legacy_format import format_legacy
from iot.store import EventLog


class TestDevices(unittest.TestCase):
    def test_get_device(self):
        self.assertEqual(devices.get_device("dev1")["firmware"], "2021")
        self.assertIsNone(devices.get_device("nope"))

    def test_is_legacy(self):
        self.assertTrue(devices.is_legacy("dev2"))
        self.assertFalse(devices.is_legacy("dev1"))


class TestGateway(unittest.TestCase):
    def setUp(self):
        EVENTS.clear()

    def test_push_known_device(self):
        g = Gateway()
        r = g.push({"device_id": "dev1", "data": "x"})
        self.assertIsNone(r)  # V1: no receipt
        self.assertEqual(EVENTS[-1]["accepted"], True)

    def test_push_unknown_device_silently_ignored(self):
        g = Gateway()
        r = g.push({"device_id": "nope", "data": "x"})
        self.assertIsNone(r)
        self.assertEqual(EVENTS[-1]["accepted"], False)


class TestStore(unittest.TestCase):
    def test_record_and_events(self):
        log = EventLog()
        log.record({"a": 1})
        log.record({"a": 2})
        self.assertEqual([e["a"] for e in log.events()], [1, 2])


class TestLegacyFormat(unittest.TestCase):
    def test_format(self):
        self.assertEqual(
            format_legacy({"device_id": "dev2", "data": "abcd"}), "v1|dev2|4")


if __name__ == "__main__":
    unittest.main()
