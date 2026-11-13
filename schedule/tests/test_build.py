# -*- coding: utf-8 -*-
import copy, json, pathlib, sys, unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from build_schedule import bars_for_site, wrap_name, render  # noqa: E402

SAMPLE = json.loads((HERE.parent / "sample_data.json").read_text(encoding="utf-8"))


class BuildTest(unittest.TestCase):
    def test_site_without_periods_gets_single_bar(self):
        b = bars_for_site({"name": "都営保木間第５アパート除却工事", "status": "現場休止中",
                           "start": "2026-05-26", "end": "2027-03-31"}, [])
        self.assertEqual([(x["kind"], x["start"], x["end"]) for x in b], [("休止中", "2026-05-26", "2027-03-31")])
        b = bars_for_site({"name": "新しい現場", "status": "近日着工予定",
                           "start": "2026-12-01", "end": "2026-12-20"}, [])
        self.assertEqual(b[0]["kind"], "着工予定")

    def test_site_without_dates_gets_no_bar(self):
        self.assertEqual(bars_for_site({"name": "日付なし", "status": "近日着工予定", "start": "", "end": ""}, []), [])

    def test_long_site_name_wraps(self):
        lines = wrap_name("（仮称）世田谷区砧6-25 自走式立体駐車場解体工事")
        self.assertTrue(len(lines) >= 2 and all(len(l) <= 14 for l in lines))
        self.assertEqual("".join(lines), "（仮称）世田谷区砧6-25 自走式立体駐車場解体工事")

    def test_render_contents(self):
        h = render(SAMPLE)
        for s in ["2026-11-13 時点", "九段南計画解体工事", "地下解体", "休止中", "オペ必要人数", "使える人数",
                  "冬季休暇", "CAT325", "width=device-width", "は工程表がまだありません"]:
            self.assertIn(s, h)
        for s in ["見習い", "user-scalable=no", "元請", 'class="cell short"']:
            self.assertNotIn(s, h)
        self.assertIn('class="cell full"', h)      # 8人に対して8台＝ちょうど

    def test_short_is_marked_red(self):
        d = copy.deepcopy(SAMPLE)
        d["periods"][0]["ope_manual"] = 6           # 九段南を6人に手直し → 11月中旬は 6+2+3=11 > 8
        self.assertIn('class="cell short"', render(d))

    def test_text_is_escaped(self):
        d = copy.deepcopy(SAMPLE)
        d["periods"][0]["memo"] = "A<B&C"
        h = render(d)
        self.assertIn("A&lt;B&amp;C", h)
        self.assertNotIn("A<B&C", h)


if __name__ == "__main__":
    unittest.main()
