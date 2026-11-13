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
                  "冬季休暇", "CAT325", "width=device-width", "overflow-x", "大型・特殊重機の使用状況"]:
            self.assertIn(s, h)
        # お知らせはページに載せない（酒井さんにだけ伝える。2026-11-13 酒井さん）
        for s in ["見習い", "user-scalable=no", "元請", 'class="cell short"', "お知らせ", "工程表がまだありません", "所在地名が空"]:
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


class ReviewFixBuildTest(unittest.TestCase):
    """2026-11-13 点検で見つかった所。"""

    def test_short_bar_label_does_not_overlap_next_bar(self):
        from datetime import date
        from build_schedule import Axis, lanes
        from calc import jun_list
        axis = Axis(jun_list(date(2026, 11, 13)))
        bars = [{"kind": "内装解体", "start": "2026-11-09", "end": "2026-11-18", "ope": 1, "memo": ""},
                {"kind": "上屋解体", "start": "2026-11-19", "end": "2026-12-25", "ope": 2, "memo": ""}]
        placed, n = lanes(bars, axis)
        self.assertEqual(n, 2)                       # 字が外に出る短い棒の隣は、段を分ける
        self.assertNotEqual(placed[0][0], placed[1][0])

    def test_site_name_space_difference_still_draws_bar(self):
        d = copy.deepcopy(SAMPLE)
        d["periods"][1]["site"] = d["periods"][1]["site"].replace(" ", "　")
        h = render(d)
        self.assertIn("上屋解体 オペ2", h)
        self.assertNotIn("着工予定 ", h.split("</svg>")[0].split("現　場")[1])   # 灰色の棒に化けない

    def test_render_survives_nulls_and_bad_numbers(self):
        d = copy.deepcopy(SAMPLE)
        d["holidays"] = None
        d["operators"] = None
        d["periods"][0]["ope_manual"] = "2人"
        d["periods"][1]["kind"] = None
        d["sites"][2]["machines_now"] = "3台"
        d["sites"][3]["leader"] = None
        self.assertIn("現場スケジュール表", render(d))
        self.assertIn("現場スケジュール表", render({"asof": "2026-11-13", "sites": None, "periods": None}))


class LayoutTest(unittest.TestCase):
    """2026-11-13 酒井さんの指摘：最初の画面は3か月、残りは横スクロール。特殊重機の欄はいつも出す。"""

    def test_left_column_is_fixed_and_right_scrolls(self):
        h = render(SAMPLE)
        self.assertEqual(h.count("<svg "), 2)
        self.assertIn('<svg class="left"', h)
        self.assertIn('<div class="scroll">', h)
        self.assertIn("(100vw - 12px) / 526", h)        # 左の欄220＋3か月(9旬×34)＝526 が画面の幅

    def test_special_machines_always_listed(self):
        d = copy.deepcopy(SAMPLE)
        for p in d["periods"]:
            p["special"] = ""
        d["special_machines"] = [{"name": "SK350超ロング", "where": "アキコ"}, {"name": "PC450スタンダード", "where": "アキコ"}]
        h = render(d)
        for s in ["大型・特殊重機の使用状況", "SK350超ロング", "PC450スタンダード", "今：アキコ"]:
            self.assertIn(s, h)

    def test_special_machine_bar_shows_site(self):
        from build_schedule import special_rows
        from calc import valid_periods
        d = copy.deepcopy(SAMPLE)
        d["special_machines"] = [{"name": "SK350超ロング", "where": "九段南"}]
        d["periods"][0]["special"] = "SK350 超ロング、CAT325"
        rows = special_rows(d, valid_periods(d)[0])
        self.assertEqual([(r[0], len(r[2])) for r in rows], [("SK350超ロング", 1), ("CAT325", 1)])
