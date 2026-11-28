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
        for s in ["2026-11-13 時点", "九段南計画解体工事", "地下解体", "休止中", "オペ必要人数", "オペの人数",
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


class KyushiLabelTest(unittest.TestCase):
    """2026-11-13 酒井さん: 休止中の棒には「オペ0」と書かない。「休止中」だけ。"""

    def test_kyushi_bar_has_no_ope(self):
        from build_schedule import bar_label
        self.assertEqual(bar_label({"kind": "休止中", "ope": 0, "memo": ""}), "休止中")
        self.assertEqual(bar_label({"kind": "上屋解体", "ope": 5, "memo": ""}), "上屋解体 オペ5")


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
        self.assertIn("(100vw - 12px) / 476", h)        # 左の欄170＋3か月(9旬×34)＝476 が画面の幅
        self.assertIn("(100vw - 12px) / 408", h)        # スマホ・埋め込みは 170＋7旬＝408（字を大きく）

    def test_tap_opens_full_screen_only_when_embedded(self):
        h = render(SAMPLE)                               # 2026-11-13 酒井さん：表をタッチで画面いっぱいに
        self.assertIn('id="chart"', h)
        self.assertIn("window.self !== window.top", h)
        self.assertIn('window.open(location.href', h)
        self.assertIn(".tap { display: none; }", h)       # ふつうに開いたときは案内を出さない

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

    def test_empty_leader_shows_mitei(self):
        d = copy.deepcopy(SAMPLE)
        d["sites"][3]["leader"] = None            # リーダーが決まっていない現場（2026-11-13 保木間）
        self.assertIn("リーダー 未定／", render(d))

    def test_title_says_all_sites(self):
        h = render(SAMPLE)                         # 題名は「全現場スケジュール表」（2026-11-13 酒井さん）
        self.assertIn("<h1>全現場スケジュール表</h1>", h)
        self.assertIn("<title>全現場スケジュール表</title>", h)


class HoverTest(unittest.TestCase):
    """2026-11-28 酒井さん：表の上にカーソルを合わせると、その日に進行中の現場とオペ必要人数を小さな窓に出す。"""

    def _sched(self, d):
        import re
        m = re.search(r"window\.SCHED = (\{.*?\});</script>", render(d))
        return json.loads(m.group(1))

    def test_hover_data_matches_table(self):
        from datetime import date
        from calc import jun_list, valid_periods, required_ope, available_ope
        s = self._sched(SAMPLE)
        juns = jun_list(date(2026, 11, 13))
        p, _ = valid_periods(SAMPLE)
        self.assertEqual((s["y"], s["m"], s["d"]), (2026, 11, 1))
        self.assertEqual(len(s["js"]), len(juns) + 1)
        self.assertEqual(len(s["need"]), s["js"][-1])                    # 日ごとの人数は、表の日数ぶん
        self.assertEqual(s["jun_need"], [required_ope(p, j) for j in juns])
        for i in range(len(juns)):                                       # 旬の数字＝その旬でいちばん多い日
            self.assertEqual(max(s["need"][s["js"][i]:s["js"][i + 1]]), s["jun_need"][i])
        self.assertEqual(s["avail"], available_ope(SAMPLE))
        self.assertEqual(s["sites"], [x["name"] for x in SAMPLE["sites"]])

    def test_hover_bars_and_running_flag(self):
        s = self._sched(SAMPLE)
        day = 12                                                          # 2026-11-13
        today = [b for b in s["bars"] if b["s"] <= day <= b["e"]]
        self.assertEqual(sum(1 for b in today if b["on"]), 3)              # 九段南・砧・東大
        off = [b for b in today if not b["on"]]
        self.assertEqual([b["label"] for b in off], ["休止中"])            # 休止中は「進行中」に数えない
        self.assertTrue(all(0 <= b["s"] <= b["e"] < s["js"][-1] for b in s["bars"]))

    def test_hover_parts_are_in_page(self):
        h = render(SAMPLE)
        for x in ['id="tip"', 'id="guide"', "pointermove", "進行中の現場", 'class="hint"']:
            self.assertIn(x, h)
        self.assertEqual(h.count('id="guide"'), 1)                         # 目印の線は右の表にだけ

    def test_hover_text_cannot_break_page(self):
        d = copy.deepcopy(SAMPLE)
        d["sites"][0]["name"] = d["periods"][0]["site"] = "A</script><b>&"
        h = render(d)
        self.assertEqual(h.count("</script>"), 3)                          # 足した文字で script が切れない
        self.assertEqual(self._sched(d)["sites"][0], "A</script><b>&")


class KoteiColorTest(unittest.TestCase):
    """2026-11-28 酒井さん：見た目は、いつも作っている工程表（0工程表）の色合いにそろえる。"""

    def test_no_old_pink_or_bright_colors(self):
        h = render(SAMPLE)
        for old in ["#FCE4EC", "#C2185B", "#E53935", "#FFEB3B", "#2196F3", "#4CAF50", "#FF9800", "#9C27B0"]:
            self.assertNotIn(old, h)
        for new in ["#EDF1F5", "#EAF0F6", "#8F99A3", "#C62828", "#F2C94C"]:   # 見出しの地・枠の線・足りない・ちょうど
            self.assertIn(new, h)

    def test_light_bar_has_dark_text(self):
        from datetime import date
        from build_schedule import Axis, bar_svg, COLORS, MACHINE
        from calc import jun_list
        axis = Axis(jun_list(date(2026, 11, 13)))
        self.assertIn('fill="#2F3438"', bar_svg(200, 500, 0, 26, COLORS["休止中"], "休止中", axis)[1])   # 薄い棒は濃い字
        self.assertIn('fill="#2F3438"', bar_svg(200, 500, 0, 26, MACHINE, "保木間", axis)[1])
        self.assertIn('fill="#fff"', bar_svg(200, 500, 0, 26, COLORS["上屋解体"], "上屋解体 オペ5", axis)[1])
