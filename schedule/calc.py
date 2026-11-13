# -*- coding: utf-8 -*-
"""現場スケジュール表の集計（旬の区切り・オペ人数・お知らせ）。
入力は data.json の形（sample_data.json が見本）。絵づくりは build_schedule.py。"""
import calendar
from datetime import date
from typing import NamedTuple

JUN_LABELS = ("上旬", "中旬", "下旬")


class Jun(NamedTuple):
    year: int
    month: int
    idx: int      # 0=上旬 1=中旬 2=下旬
    start: date
    end: date
    label: str


def to_date(s):
    """'2026-11-13' → date。空・形が違うものは None。"""
    try:
        return date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


def jun_list(asof: date, months: int = 12) -> list:
    """基準日の月から months か月ぶんの旬。上旬1〜10日・中旬11〜20日・下旬21日〜月末。"""
    out = []
    y, m = asof.year, asof.month
    for _ in range(months):
        last = calendar.monthrange(y, m)[1]
        for i, (a, b) in enumerate(((1, 10), (11, 20), (21, last))):
            out.append(Jun(y, m, i, date(y, m, a), date(y, m, b), JUN_LABELS[i]))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def ope_of(period: dict) -> int:
    """手直しに数字があればそちら（0 も「0人」として使う）。無ければ自動。どちらも無ければ 0。"""
    manual = period.get("ope_manual")
    if manual is not None and manual != "":
        return int(manual)
    auto = period.get("ope_auto")
    return int(auto) if auto not in (None, "") else 0


def valid_periods(data: dict):
    """日付がそろった作業期間だけ返す。飛ばした行は、お知らせの文にする。"""
    good, msgs = [], []
    for p in data.get("periods", []):
        s, e = to_date(p.get("start")), to_date(p.get("end"))
        if s is None or e is None or e < s:
            msg = f"「{p.get('site', '')}」の作業期間に日付の抜け・逆転があります"
            if msg not in msgs:
                msgs.append(msg)
            continue
        good.append(p)
    return good, msgs


def overlaps(period: dict, start: date, end: date) -> bool:
    return to_date(period["start"]) <= end and to_date(period["end"]) >= start


def required_ope(periods: list, jun: Jun) -> int:
    """その旬に1日でも重なる作業の、オペ人数の合計。"""
    return sum(ope_of(p) for p in periods if overlaps(p, jun.start, jun.end))


def available_ope(data: dict) -> int:
    """使える人数＝オペの人数 − 常用現場に出ている人数。"""
    o = data.get("operators", {})
    return max(0, int(o.get("total", 0)) - int(o.get("joyo", 0)))


def level(required: int, available: int) -> str:
    """short＝足りない／full＝ちょうど／ok＝余裕あり。"""
    if required > available:
        return "short"
    return "full" if required == available and required > 0 else "ok"


def warnings(data: dict) -> list:
    """酒井さんに知らせること（表は勝手に直さない）。"""
    periods, out = valid_periods(data)
    asof = to_date(data.get("asof")) or date.today()
    sites = data.get("sites", [])
    for s in sites:
        name = s["name"]
        mine = [p for p in periods if p.get("site") == name]
        if not mine:
            out.append(f"「{name}」は工程表がまだありません")
        else:
            now = [p for p in mine if overlaps(p, asof, asof)]
            planned = sum(int(p.get("ope_auto") or 0) for p in now)
            actual = int(s.get("machines_now") or 0)
            if now and planned != actual:
                out.append(f"「{name}」工程表では{planned}台、実際は{actual}台です")
        if not (s.get("location_name") or "").strip():
            out.append(f"「{name}」は所在地名が空です")
    other = int(data.get("machines_other") or 0)
    if other > 0 and sites:
        out.append(f"所在地が「その他」の重機が{other}台あります。日報の現場名が抜けていませんか")
    return out
