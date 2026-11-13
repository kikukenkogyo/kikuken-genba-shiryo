# -*- coding: utf-8 -*-
"""現場スケジュール表の集計（旬の区切り・オペ人数・お知らせ）。
入力は data.json の形（sample_data.json が見本）。絵づくりは build_schedule.py。
Notionの空欄は null で来るので、どの項目も「無い・null・形が違う」で止まらないようにしてある。"""
import calendar
from datetime import date, timedelta
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


def to_int(v):
    """人数・台数を整数にする。空・文字（「2人」など）・マイナスは None。"""
    if v is None or isinstance(v, bool):
        return None
    try:
        n = int(round(float(str(v).strip())))
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def is_bad_number(v) -> bool:
    """何か入っているのに数字として読めない。"""
    return v is not None and str(v).strip() != "" and to_int(v) is None


def norm(name) -> str:
    """現場名を比べるための形（全角・半角のスペースの違いを無視する）。"""
    return "".join(str(name or "").split())


def sites_of(data: dict) -> list:
    return [s for s in (data.get("sites") or []) if isinstance(s, dict)]


def site_name(site: dict) -> str:
    return str(site.get("name") or "")


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
    """手直しに数字があればそちら（0 も「0人」として使う）。無ければ自動。どちらも読めなければ 0。"""
    manual = to_int(period.get("ope_manual"))
    if manual is not None:
        return manual
    auto = to_int(period.get("ope_auto"))
    return auto if auto is not None else 0


def valid_periods(data: dict):
    """使える作業期間だけ返す。飛ばした行（日付の抜け・逆転／現場一覧に無い現場名）は、お知らせの文にする。"""
    known = {norm(site_name(s)) for s in sites_of(data)}
    good, msgs = [], []

    def add(msg):
        if msg not in msgs:
            msgs.append(msg)

    for p in data.get("periods") or []:
        if not isinstance(p, dict):
            continue
        site = str(p.get("site") or "")
        if norm(site) not in known:
            add(f"作業期間の現場名「{site}」が現場一覧にありません")
            continue
        s, e = to_date(p.get("start")), to_date(p.get("end"))
        if s is None or e is None or e < s:
            add(f"「{site}」の作業期間に日付の抜け・逆転があります")
            continue
        good.append(p)
    return good, msgs


def overlaps(period: dict, start: date, end: date) -> bool:
    return to_date(period["start"]) <= end and to_date(period["end"]) >= start


def required_ope(periods: list, jun: Jun) -> int:
    """その旬の中で、いちばん人数が多い日のオペ人数（同じ日に重なる作業は足す）。
    同じ旬の中で作業が入れ替わるとき（例: 上屋解体が12日まで・外構解体が15日から）は足し算にしない（2026-11-13 酒井さん・保木間）。"""
    best, d = 0, jun.start
    while d <= jun.end:
        best = max(best, sum(ope_of(p) for p in periods if overlaps(p, d, d)))
        d += timedelta(days=1)
    return best


def available_ope(data: dict) -> int:
    """使える人数＝オペの人数 − 常用現場に出ている人数。"""
    o = data.get("operators") or {}
    return max(0, (to_int(o.get("total")) or 0) - (to_int(o.get("joyo")) or 0))


def level(required: int, available: int) -> str:
    """short＝足りない／full＝ちょうど／ok＝余裕あり。"""
    if required > available:
        return "short"
    return "full" if required == available and required > 0 else "ok"


def warnings(data: dict) -> list:
    """酒井さんに知らせること（表は勝手に直さない）。"""
    periods, out = valid_periods(data)
    asof = to_date(data.get("asof")) or date.today()
    sites = sites_of(data)
    all_rows = [p for p in (data.get("periods") or []) if isinstance(p, dict)]
    for s in sites:
        name = site_name(s)
        key = norm(name)
        mine = [p for p in periods if norm(p.get("site")) == key]
        any_row = [p for p in all_rows if norm(p.get("site")) == key]
        if not any_row:
            out.append(f"「{name}」は工程表がまだありません")
        elif mine:
            now = [p for p in mine if overlaps(p, asof, asof)]
            planned = sum(to_int(p.get("ope_auto")) or 0 for p in now)
            actual = to_int(s.get("machines_now")) or 0
            if now and planned != actual:
                out.append(f"「{name}」工程表では{planned}台、実際は{actual}台です")
        bad = is_bad_number(s.get("machines_now")) or any(
            is_bad_number(p.get("ope_auto")) or is_bad_number(p.get("ope_manual")) for p in any_row)
        if bad:
            out.append(f"「{name}」のオペ人数が数字ではありません")
        if not str(s.get("location_name") or "").strip():
            out.append(f"「{name}」は所在地名が空です")
    other = to_int(data.get("machines_other")) or 0
    if other > 0 and sites:
        out.append(f"所在地が「その他」の重機が{other}台あります。日報の現場名が抜けていませんか")
    return out
