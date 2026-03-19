import unittest
from pathlib import Path

from electro_parse import parse_schedule_image


ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "images"


class ParserTests(unittest.TestCase):
    def test_parses_first_schedule(self) -> None:
        parsed = parse_schedule_image(IMAGES / "photo_2026-02-26.jpeg")
        self.assertEqual(
            parsed,
            {
                "1.1": {"off": ["11:00", "12:00", "13:00", "22:00", "23:00"], "maybe_off": []},
                "1.2": {"off": ["12:00", "13:00", "14:00", "20:00", "21:00"], "maybe_off": []},
                "2.1": {"off": ["08:00", "09:00", "10:00", "14:00", "15:00", "16:00"], "maybe_off": []},
                "2.2": {"off": ["09:00", "10:00", "11:00", "18:00", "19:00"], "maybe_off": []},
                "3.1": {"off": ["12:00", "13:00", "14:00", "18:00", "19:00"], "maybe_off": []},
                "3.2": {"off": ["15:00", "16:00", "17:00"], "maybe_off": []},
                "4.1": {"off": ["09:00", "10:00", "11:00", "15:00", "16:00", "17:00"], "maybe_off": []},
                "4.2": {"off": ["12:00", "13:00", "14:00"], "maybe_off": []},
                "5.1": {"off": ["09:00", "10:00", "11:00"], "maybe_off": []},
                "5.2": {"off": ["08:00", "09:00", "10:00", "15:00", "16:00", "17:00"], "maybe_off": []},
                "6.1": {"off": ["11:00", "12:00"], "maybe_off": []},
                "6.2": {"off": ["13:00", "14:00", "15:00"], "maybe_off": []},
            },
        )

    def test_parses_second_schedule(self) -> None:
        parsed = parse_schedule_image(IMAGES / "photo_2026-03-19.jpeg")
        self.assertEqual(
            parsed,
            {
                "1.1": {"off": ["17:00", "18:00", "19:00", "20:00"], "maybe_off": []},
                "1.2": {"off": ["17:00", "18:00", "19:00", "20:00"], "maybe_off": []},
                "2.1": {"off": ["11:00", "12:00", "13:00"], "maybe_off": []},
                "2.2": {"off": ["08:00", "09:00", "10:00"], "maybe_off": []},
                "3.1": {"off": ["08:00", "09:00", "10:00"], "maybe_off": []},
                "3.2": {"off": ["08:00", "09:00", "10:00"], "maybe_off": []},
                "4.1": {"off": ["11:00", "12:00", "13:00"], "maybe_off": []},
                "4.2": {"off": ["11:00", "12:00", "13:00"], "maybe_off": []},
                "5.1": {"off": ["14:00", "15:00", "16:00"], "maybe_off": []},
                "5.2": {"off": ["14:00", "15:00", "16:00"], "maybe_off": []},
                "6.1": {"off": [], "maybe_off": []},
                "6.2": {"off": ["14:00", "15:00", "16:00"], "maybe_off": []},
            },
        )


if __name__ == "__main__":
    unittest.main()
