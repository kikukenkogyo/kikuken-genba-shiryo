# -*- coding: utf-8 -*-
"""現場スケジュール表のページ（genba-schedule.html）を作る。
使い方: python schedule/build_schedule.py schedule/data.json
表は1枚のSVG（拡大しても字がくっきり）。集計は calc.py。"""
import html, json, pathlib, sys
from datetime import date, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from calc import jun_list, to_date, ope_of, valid_periods, required_ope, available_ope, level, warnings  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
COLORS = {"内装解体": "#4CAF50", "上屋解体": "#2196F3", "基礎解体": "#FF9800", "地下解体": "#9C27B0",
          "着工予定": "#9E9E9E", "休止中": "#9E9E9E"}
LEGEND = ["内装解体", "上屋解体", "基礎解体", "地下解体", "着工予定"]
LEFT, CELL = 300, 34            # 左の欄の幅、旬1つの幅
TITLE_H, MONTH_H, JUN_H = 64, 26, 20
LANE_H, ROW_PAD = 32, 10        # 棒1本の段の高さ、行の上下の余白
SUM_H = 28                      # 下の段の1行の高さ
esc = html.escape


def wrap_name(name: str, width: int = 14) -> list:
    """長い現場名を、だいたい同じ長さの行に分ける（最後の行に1文字だけ残さない）。"""
    if not name:
        return [""]
    n = -(-len(name) // width)          # 行の数（切り上げ）
    w = -(-len(name) // n)              # 1行の字数
    return [name[i:i + w] for i in range(0, len(name), w)]


def bars_for_site(site: dict, periods: list) -> list:
    """その現場の棒。作業期間が無い現場は、着工〜完了の1本（休止中 or 着工予定）。"""
    mine = [p for p in periods if p.get("site") == site["name"]]
    if mine:
        return [{"kind": p.get("kind", ""), "start": p["start"], "end": p["end"], "ope": ope_of(p),
                 "memo": p.get("memo") or ""} for p in sorted(mine, key=lambda p: p["start"])]
    if to_date(site.get("start")) is None or to_date(site.get("end")) is None:
        return []
    kind = "休止中" if site.get("status") == "現場休止中" else "着工予定"
    return [{"kind": kind, "start": site["start"], "end": site["end"], "ope": None, "memo": ""}]


class Axis:
    """日付 → 横の位置。旬の幅はどれも同じ（日数が違っても）。"""

    def __init__(self, juns):
        self.juns = juns
        self.x0, self.x1 = LEFT, LEFT + CELL * len(juns)
        self.first, self.last = juns[0].start, juns[-1].end

    def x(self, d: date) -> float:
        if d <= self.first:
            return self.x0
        if d > self.last:
            return self.x1
        for i, j in enumerate(self.juns):
            if j.start <= d <= j.end:
                days = (j.end - j.start).days + 1
                return LEFT + CELL * (i + (d - j.start).days / days)
        return self.x1

    def span(self, start: str, end: str):
        """棒の左端と右端（表示の範囲に切りつめる）。範囲の外なら None。"""
        s, e = to_date(start), to_date(end)
        if s is None or e is None or e < self.first or s > self.last:
            return None
        return self.x(s), self.x(e + timedelta(days=1))


def lanes(bars, axis):
    """重なる棒を段に分ける。[(段, 左, 右, 棒)]"""
    ends, out = [], []
    for b in bars:
        sp = axis.span(b["start"], b["end"])
        if sp is None:
            continue
        for n, e in enumerate(ends):
            if sp[0] >= e - 0.01:
                ends[n] = sp[1]
                break
        else:
            n = len(ends)
            ends.append(sp[1])
        out.append((n, sp[0], sp[1], b))
    return out, max(1, len(ends))


def text(x, y, s, size=12, fill="#222", anchor="start", bold=False, extra=""):
    w = ' font-weight="bold"' if bold else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"{w}{extra}>{esc(str(s))}</text>'


def bar_svg(x0, x1, y, h, color, label, axis):
    out = [f'<rect x="{x0:.1f}" y="{y:.1f}" width="{max(x1 - x0, 3):.1f}" height="{h}" rx="4" fill="{color}"/>']
    need = len(label) * 12 + 10
    if x1 - x0 >= need:
        out.append(text(x0 + 6, y + h / 2 + 4.5, label, 12, "#fff", bold=True))
    elif x1 + need <= axis.x1:
        out.append(text(x1 + 5, y + h / 2 + 4.5, label, 12, "#222", bold=True))
    else:
        out.append(text(x0 - 5, y + h / 2 + 4.5, label, 12, "#222", "end", True))
    return out


def render(data: dict) -> str:
    asof = to_date(data.get("asof")) or date.today()
    juns = jun_list(asof)
    axis = Axis(juns)
    periods, _ = valid_periods(data)
    sites = data.get("sites", [])
    avail = available_ope(data)
    W = axis.x1 + 10
    g = []          # SVGの部品
    late = []       # 今日の線より上に描く、棒の中の字
    y = 0

    # 題と凡例
    g.append(text(12, 34, "現場スケジュール表", 24, "#C2185B", bold=True))
    g.append(text(12, 54, f"{asof.isoformat()} 時点　／　指で広げて拡大できます", 12, "#555"))
    lx = W - 10 - len(LEGEND) * 96
    for k in LEGEND:
        g.append(f'<rect x="{lx}" y="22" width="16" height="16" rx="3" fill="{COLORS[k]}"/>')
        g.append(text(lx + 21, 35, k, 12))
        lx += 96
    y = TITLE_H

    # 月と旬の見出し
    head_y = y
    for i in range(0, len(juns), 3):
        j = juns[i]
        x = LEFT + CELL * i
        g.append(f'<rect x="{x}" y="{y}" width="{CELL * 3}" height="{MONTH_H}" fill="#FCE4EC" stroke="#999"/>')
        label = f"{j.year}年{j.month}月" if (i == 0 or j.month == 1) else f"{j.month}月"
        g.append(text(x + CELL * 1.5, y + 18, label, 13, anchor="middle", bold=True))
    for i, j in enumerate(juns):
        x = LEFT + CELL * i
        g.append(f'<rect x="{x}" y="{y + MONTH_H}" width="{CELL}" height="{JUN_H}" fill="#fff" stroke="#bbb"/>')
        g.append(text(x + CELL / 2, y + MONTH_H + 14, j.label[0], 11, "#555", "middle"))
    g.append(f'<rect x="0" y="{y}" width="{LEFT}" height="{MONTH_H + JUN_H}" fill="#FCE4EC" stroke="#999"/>')
    g.append(text(LEFT / 2, y + 29, "現　場", 13, anchor="middle", bold=True))
    y += MONTH_H + JUN_H
    body_top = y

    # 現場の行
    rows = []
    for s in sites:
        placed, n = lanes(bars_for_site(s, periods), axis)
        names = wrap_name(s["name"])
        h = max(n * LANE_H + ROW_PAD * 2, len(names) * 18 + 30)
        rows.append((s, placed, names, y, h))
        y += h
    body_bottom = y

    # 升目・休暇の帯（棒より下に描く）
    for s, placed, names, ry, h in rows:
        g.append(f'<rect x="0" y="{ry}" width="{W - 10}" height="{h}" fill="#fff" stroke="#999"/>')
    for i in range(len(juns) + 1):
        x = LEFT + CELL * i
        c = "#999" if i % 3 == 0 else "#e3e3e3"
        g.append(f'<line x1="{x}" y1="{body_top}" x2="{x}" y2="{body_bottom}" stroke="{c}"/>')
    for hol in data.get("holidays", []):
        sp = axis.span(hol.get("start"), hol.get("end"))
        if sp:
            g.append(f'<rect x="{sp[0]:.1f}" y="{body_top}" width="{sp[1] - sp[0]:.1f}" height="{body_bottom - body_top}" fill="#000" opacity="0.10"/>')
            g.append(text((sp[0] + sp[1]) / 2, body_top + 11, hol.get("name", ""), 10, "#333", "middle"))

    # 現場名と棒
    for s, placed, names, ry, h in rows:
        ty = ry + 20
        for line in names:
            g.append(text(8, ty, line, 14, bold=True))
            ty += 18
        info = f"リーダー {s.get('leader') or '−'}／メイン {s.get('main_machine') or '−'}／今ある重機 {int(s.get('machines_now') or 0)}台"
        g.append(text(8, ty, info, 11, "#555"))
        for n, x0, x1, b in placed:
            label = b["kind"] + (f" オペ{b['ope']}" if b["ope"] is not None else "") + (f" {b['memo']}" if b["memo"] else "")
            by = ry + ROW_PAD + n * LANE_H + (h - ROW_PAD * 2 - (max(p[0] for p in placed) + 1) * LANE_H) / 2
            parts = bar_svg(x0, x1, by + 3, LANE_H - 6, COLORS.get(b["kind"], "#607D8B"), label, axis)
            g.append(parts[0])
            late += parts[1:]

    # 下の段①：オペ必要人数・使える人数
    y += 8
    for title, fn in (("オペ必要人数", lambda j: required_ope(periods, j)), ("使える人数", lambda j: avail)):
        g.append(f'<rect x="0" y="{y}" width="{LEFT}" height="{SUM_H}" fill="#F5F5F5" stroke="#999"/>')
        g.append(text(8, y + 19, title, 13, bold=True))
        for i, j in enumerate(juns):
            v = fn(j)
            cls = level(required_ope(periods, j), avail) if title == "オペ必要人数" else "ok"
            fg = "#fff" if cls == "short" else "#222"
            g.append(f'<rect class="cell {cls}" x="{LEFT + CELL * i}" y="{y}" width="{CELL}" height="{SUM_H}"/>')
            g.append(text(LEFT + CELL * (i + .5), y + 19, v, 13, fg, "middle", cls != "ok"))
        y += SUM_H
    g.append(text(8, y + 15, "赤＝オペが足りない　黄＝ちょうど（余裕なし）", 11, "#555"))
    y += 26

    # 下の段②：大型・特殊重機
    special = {}
    for p in periods:
        for name in str(p.get("special") or "").replace(",", "、").split("、"):
            if name.strip():
                special.setdefault(name.strip(), []).append(p)
    if special:
        g.append(f'<rect x="0" y="{y}" width="{W - 10}" height="22" fill="#FCE4EC" stroke="#999"/>')
        g.append(text(8, y + 16, "大型・特殊重機の使用状況", 13, bold=True))
        y += 22
        short = {s["name"]: (s.get("location_name") or s["name"][:8]) for s in sites}
        for name, ps in special.items():
            g.append(f'<rect x="0" y="{y}" width="{W - 10}" height="{LANE_H}" fill="#fff" stroke="#999"/>')
            g.append(text(8, y + 21, name, 13, bold=True))
            for p in ps:
                sp = axis.span(p["start"], p["end"])
                if sp:
                    g += bar_svg(sp[0], sp[1], y + 4, LANE_H - 8, "#607D8B", short.get(p.get("site"), p.get("site", "")), axis)
            y += LANE_H
        y += 8

    # 今日の線（いちばん上に描く）
    tx = axis.x(asof)
    g.append(f'<line x1="{tx:.1f}" y1="{head_y}" x2="{tx:.1f}" y2="{body_bottom}" stroke="#E53935" stroke-width="2"/>')
    g.append(text(tx, head_y - 4, "今日", 11, "#E53935", "middle", True))
    g += late

    H = y + 6
    notes = warnings(data)
    note_html = ""
    if notes:
        note_html = '<div class="notes"><b>お知らせ（確認してください）</b><ul>' + "".join(f"<li>{esc(n)}</li>" for n in notes) + "</ul></div>"
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>現場スケジュール表</title>
<link rel="icon" href="favicon.png">
<style>
body {{ margin: 6px; background: #fff; font-family: Meiryo, "Hiragino Kaku Gothic ProN", "Noto Sans JP", sans-serif; }}
svg {{ width: 100%; height: auto; display: block; }}
svg text {{ font-family: Meiryo, "Hiragino Kaku Gothic ProN", "Noto Sans JP", sans-serif; }}
.cell {{ fill: #fff; stroke: #bbb; }}
.cell.short {{ fill: #E53935; }}
.cell.full {{ fill: #FFEB3B; }}
.notes {{ margin: 10px 4px; padding: 8px 12px; border: 1px solid #E53935; border-radius: 6px; font-size: 14px; }}
.notes ul {{ margin: 4px 0 0; padding-left: 20px; }}
</style>
</head>
<body>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:.0f}">
{chr(10).join(g)}
</svg>
{note_html}
</body>
</html>
"""


def main():
    src = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "genba-schedule.html"
    data = json.loads(src.read_text(encoding="utf-8"))
    out.write_text(render(data), encoding="utf-8")
    print("作りました:", out)
    for n in warnings(data):
        print("お知らせ:", n)


if __name__ == "__main__":
    main()
