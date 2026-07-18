import unittest

from device_profiles import get_screen_preset, list_screen_presets


class DeviceProfilesTests(unittest.TestCase):
    def test_poco_f5_preset_exists(self):
        preset = get_screen_preset("poco_f5")
        self.assertEqual(preset["name"], "Poco F5")
        self.assertEqual(preset["resolution"], "2712x1220")

    def test_available_presets_include_poco_f5(self):
        presets = list_screen_presets()
        self.assertIn("poco_f5", presets)


if __name__ == "__main__":
    unittest.main()
