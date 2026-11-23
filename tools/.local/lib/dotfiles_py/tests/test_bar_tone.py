from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotfiles_tools import bar_tone


class ToneTest(unittest.TestCase):
    def test_contrast_matches_wcag_reference_values(self) -> None:
        self.assertAlmostEqual(bar_tone.contrast(bar_tone.luminance("#ffffff"), bar_tone.luminance("#000000")), 21.0, places=1)
        self.assertAlmostEqual(bar_tone.luminance("#808080"), 0.2159, places=3)

    def test_dark_strips_keep_accent_text_and_light_strips_do_not(self) -> None:
        self.assertEqual(bar_tone.tone_for(0.10, 0.2)[0], "dark")
        self.assertEqual(bar_tone.tone_for(0.45, 0.2)[0], "dark")
        self.assertEqual(bar_tone.tone_for(0.55, 0.2)[0], "light")
        self.assertEqual(bar_tone.tone_for(0.90, 0.2)[0], "light")

    def test_a_more_opaque_bar_tolerates_lighter_wallpapers(self) -> None:
        self.assertEqual(bar_tone.tone_for(0.63, 0.2)[0], "light")
        self.assertEqual(bar_tone.tone_for(0.63, 0.6)[0], "dark")

    def test_mean_grey_of_a_ppm(self) -> None:
        white_black = b"P6\n2 1\n255\n" + bytes([255, 255, 255, 0, 0, 0])
        self.assertAlmostEqual(bar_tone.mean_grey(white_black), 0.5, places=3)
        with self.assertRaises(ValueError):
            bar_tone.mean_grey(b"not an image")

    def test_bar_alpha_is_read_from_colors_css(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            css = Path(tmp) / "colors.css"
            css.write_text("@define-color background #000003;\n@define-color background rgba(0,0,3, 0.35);\n")
            self.assertEqual(bar_tone.bar_alpha(css), 0.35)
            css.write_text("@define-color foreground #ffffff;\n")
            self.assertEqual(bar_tone.bar_alpha(css), bar_tone.DEFAULT_ALPHA)


if __name__ == "__main__":
    unittest.main()
