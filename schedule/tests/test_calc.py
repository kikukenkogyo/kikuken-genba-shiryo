# -*- coding: utf-8 -*-
import copy, json, pathlib, sys, unittest
from datetime import date

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from calc import jun_list, ope_of, valid_periods, required_ope, available_ope, level, warnings  # noqa: E402

SAMPLE = json.loads((HERE.parent / "sample_data.json").read_text(encoding="utf-8"))
KUDAN, KINUTA = SAMPLE["sites"][0]["name"], SAMPLE["sites"][1]["name"]
TODAI, HOKIMA = SAMPLE["sites"][2]["name"], SAMPLE["sites"][3]["name"]


class CalcTest(unittest.TestCase):
    def test_jun_boundaries(self):
        j = jun_list(date(2026, 11, 13))
        self.assertEqual((len(j), j[0].start, j[0].end), (36, date(2026, 11, 1), date(2026, 11, 10)))
        self.assertEqual(j[2].end, date(2026, 11, 30))
        self.assertEqual(j[11].end, date(2027, 2, 28))
        self.assertEqual((j[1].idx, j[1].label), (1, "中旬"))

    def test_manual_zero_is_used(self):
        self.assertEqual(ope_of({"ope_auto": 3, "ope_manual": 0}), 0)
        self.assertEqual(ope_of({"ope_auto": 3, "ope_manual": None}), 3)
        self.assertEqual(ope_of({"ope_auto": None, "ope_manual": None}), 0)

    def test_required_and_available(self):
        j = jun_list(date(2026, 11, 13))
        p, _ = valid_periods(SAMPLE)
        self.assertEqual(required_ope(p, j[1]), 8)
        self.assertEqual(available_ope(SAMPLE), 8)
        self.assertEqual(level(8, 8), "full")
        self.assertEqual(level(9, 8), "short")
        self.assertEqual(level(5, 8), "ok")

    def test_period_crossing_year_and_range(self):
        j = jun_list(date(2026, 11, 13))
        p, _ = valid_periods(SAMPLE)
        mar_late = [x for x in j if (x.year, x.month, x.idx) == (2027, 3, 2)][0]
        self.assertEqual(required_ope(p, mar_late), 3)      # 九段南は 2027-03-31 まで
        self.assertEqual(required_ope(p, j[-1]), 0)          # 2027年10月下旬は何も無い
        self.assertEqual(required_ope(p, j[3]), 5)           # 12月上旬：九段南3＋砧2（12/3まで）

    def test_broken_period_is_skipped_and_warned(self):
        d = copy.deepcopy(SAMPLE)
        d["periods"].append({"site": KUDAN, "kind": "基礎解体", "start": "", "end": "2026-12-01", "ope_auto": 5, "ope_manual": None})
        d["periods"].append({"site": KINUTA, "kind": "基礎解体", "start": "2026-12-10", "end": "2026-12-01", "ope_auto": 5, "ope_manual": None})
        p, msgs = valid_periods(d)
        self.assertEqual(len(p), 3)
        self.assertEqual(msgs, [f"「{KUDAN}」の作業期間に日付の抜け・逆転があります",
                                f"「{KINUTA}」の作業期間に日付の抜け・逆転があります"])
        self.assertIn(msgs[0], warnings(d))

    def test_warnings_texts(self):
        d = copy.deepcopy(SAMPLE)
        d["sites"][0]["machines_now"] = 2
        d["machines_other"] = 3
        w = warnings(d)
        self.assertIn(f"「{KUDAN}」工程表では3台、実際は2台です", w)
        self.assertIn("所在地が「その他」の重機が3台あります。日報の現場名が抜けていませんか", w)
        self.assertIn(f"「{HOKIMA}」は工程表がまだありません", w)
        self.assertIn(f"「{TODAI}」は所在地名が空です", w)
        self.assertEqual(len(w), 4)

    def test_no_warning_when_clean(self):
        d = copy.deepcopy(SAMPLE)
        d["sites"] = d["sites"][:2]
        d["periods"] = d["periods"][:2]
        self.assertEqual(warnings(d), [])


if __name__ == "__main__":
    unittest.main()
