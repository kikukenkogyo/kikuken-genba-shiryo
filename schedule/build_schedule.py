# -*- coding: utf-8 -*-
"""現場スケジュール表のページ（genba-schedule.html）を作る。
使い方: python schedule/build_schedule.py schedule/data.json
表は1枚のSVG（拡大しても字がくっきり）。集計は calc.py。"""
import html, json, pathlib, sys
from datetime import date, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from calc import (jun_list, to_date, to_int, norm, sites_of, site_name, ope_of, valid_periods,  # noqa: E402
                  required_ope, required_on, available_ope, level, warnings)

ROOT = pathlib.Path(__file__).resolve().parent.parent
# 色は、いつも作っている工程表（0工程表）の色合いにそろえる（2026-11-28 酒井さん：前の色は見づらい）。
# 白地・灰色がかった青の見出し・細い線・落ち着いた色の棒。元の色は mitsumori-teian の build_kotei_html.py。
COLORS = {"内装解体": "#5E9E3A", "上屋解体": "#3C7DBF", "基礎解体": "#8D6E63", "地下解体": "#7B3FA0",
          "外構解体": "#00796B", "着工予定": "#D5D8DC", "休止中": "#D5D8DC"}
MACHINE = "#A9D6D0"             # 大型・特殊重機の棒（工程表の「使用重機」の色）
LITE = {"#D5D8DC", MACHINE}     # 薄い色の棒。中の字は白ではなく濃い色で書く
OTHER = "#6B6B6B"               # 種類が決まりに無い作業の棒
HEAD, HEAD2 = "#EDF1F5", "#EAF0F6"                  # 見出しの地の色（左の欄／月）
LINE, LINE_SOFT, LINE_MONTH = "#8F99A3", "#DBE0E5", "#8F99A3"   # 枠の線／旬の線／月の線
INK, INK_SUB = "#111", "#4A4A4A"                    # 字の色（本文／小さい説明）
RED, YEL, NAVY, TEAL = "#C62828", "#F2C94C", "#2E3F8F", "#00796B"
LEGEND = ["内装解体", "上屋解体", "基礎解体", "地下解体", "外構解体", "着工予定"]
LEFT, CELL = 170, 34            # 左の欄の幅、旬1つの幅
TOP_H, MONTH_H, JUN_H = 18, 26, 20
FIRST_VIEW = 9                  # 最初の画面に見せる旬の数（3か月）。残りは横にスクロール
FIRST_VIEW_PHONE = 7            # スマホ・Notionの埋め込みの幅（700px以下）では2か月と少し（字を大きく見せる）
MAX_SCALE = 1.3                 # パソコンで大きくなりすぎないための上限
LANE_H, ROW_PAD = 32, 10        # 棒1本の段の高さ、行の上下の余白
SUM_H = 28                      # 下の段の1行の高さ
esc = html.escape


def wrap_name(name: str, width: int = 10) -> list:
    """長い現場名を、だいたい同じ長さの行に分ける（最後の行に1文字だけ残さない）。"""
    if not name:
        return [""]
    n = -(-len(name) // width)          # 行の数（切り上げ）
    w = -(-len(name) // n)              # 1行の字数
    return [name[i:i + w] for i in range(0, len(name), w)]


def bars_for_site(site: dict, periods: list) -> list:
    """その現場の棒。作業期間が無い現場は、着工〜完了の1本（休止中 or 着工予定）。"""
    key = norm(site_name(site))
    mine = [p for p in periods if norm(p.get("site")) == key]
    if mine:
        return [{"kind": p.get("kind") or "", "start": p["start"], "end": p["end"], "ope": ope_of(p),
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


def bar_label(b: dict) -> str:
    """棒に書く字（作業の種類・オペ人数・メモ）。"""
    ope = None if b.get("kind") == "休止中" else b.get("ope")     # 休止中は「休止中」だけ（2026-11-13 酒井さん）
    return (b.get("kind") or "") + (f" オペ{ope}" if ope is not None else "") + (f" {b['memo']}" if b.get("memo") else "")


def label_place(x0, x1, label, axis):
    """字をどこに書くか。(置き方, 棒と字が使う左端, 右端)。置き方は in＝棒の中／right＝棒の右／left＝棒の左。"""
    need = len(label) * 12 + 10
    if x1 - x0 >= need:
        return "in", x0, x1
    if x1 + need <= axis.x1:
        return "right", x0, x1 + need
    return "left", x0 - need, x1


def lanes(bars, axis):
    """重なる棒を段に分ける。棒の外に出る字の幅も含めて、重なりを見る。[(段, 左, 右, 棒)]"""
    ends, out = [], []
    for b in bars:
        sp = axis.span(b["start"], b["end"])
        if sp is None:
            continue
        _, lo, hi = label_place(sp[0], sp[1], bar_label(b), axis)
        for n, e in enumerate(ends):
            if lo >= e - 0.01:
                ends[n] = hi
                break
        else:
            n = len(ends)
            ends.append(hi)
        out.append((n, sp[0], sp[1], b))
    return out, max(1, len(ends))


def text(x, y, s, size=12, fill="#222", anchor="start", bold=False, extra=""):
    w = ' font-weight="bold"' if bold else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"{w}{extra}>{esc(str(s))}</text>'


def bar_svg(x0, x1, y, h, color, label, axis):
    out = [f'<rect x="{x0:.1f}" y="{y:.1f}" width="{max(x1 - x0, 3):.1f}" height="{h}" rx="2" fill="{color}" '
           f'stroke="#000" stroke-opacity="0.28" stroke-width="0.6"/>']
    mode, _, _ = label_place(x0, x1, label, axis)
    if mode == "in":
        out.append(text(x0 + 6, y + h / 2 + 4.5, label, 12, "#2F3438" if color in LITE else "#fff", bold=True))
    elif mode == "right":
        out.append(text(x1 + 5, y + h / 2 + 4.5, label, 12, INK, bold=True))
    else:
        out.append(text(x0 - 5, y + h / 2 + 4.5, label, 12, INK, "end", True))
    return out


def special_rows(data: dict, periods: list) -> list:
    """大型・特殊重機の段の行。[(重機の名前, 今ある場所, [その重機を使う作業期間])]
    data["special_machines"] の重機はいつも出す。作業期間にだけ名前がある重機も足す。"""
    use = {}
    for p in periods:
        for name in str(p.get("special") or "").replace(",", "、").split("、"):
            if name.strip():
                use.setdefault(norm(name), (name.strip(), []))[1].append(p)
    rows, seen = [], set()
    for m in data.get("special_machines") or []:
        if isinstance(m, dict) and str(m.get("name") or "").strip():
            key = norm(m["name"])
            seen.add(key)
            rows.append((str(m["name"]).strip(), str(m.get("where") or ""), use.get(key, ("", []))[1]))
    for key, (name, ps) in use.items():
        if key not in seen:
            rows.append((name, "", ps))
    return rows


# ===== カーソルを合わせた日の説明の窓（2026-11-28 酒井さん） =====
# 表の上にカーソルを合わせる（スマホ・タブレットはタッチする）と、その日に進行中の現場と、オペ必要人数を小さな窓に出す。
NOT_RUNNING = ("休止中", "着工予定")     # 棒はあるが「進行中」には数えない種類


def hover_data(juns, periods, sites, avail) -> dict:
    """説明の窓が使うデータ。日は「表の最初の日から何日目か」で持つ。人数の数え方は calc.py と同じ。"""
    first, last = juns[0].start, juns[-1].end
    total = (last - first).days + 1
    bars = []
    for i, s in enumerate(sites):
        for b in bars_for_site(s, periods):
            bs, be = to_date(b["start"]), to_date(b["end"])
            if bs is None or be is None or be < first or bs > last:
                continue
            bars.append({"site": i, "s": max(0, (bs - first).days), "e": min(total - 1, (be - first).days),
                         "label": bar_label(b), "color": COLORS.get(b["kind"], OTHER),
                         "on": b["kind"] not in NOT_RUNNING})
    return {"y": first.year, "m": first.month, "d": first.day,
            "js": [(j.start - first).days for j in juns] + [total],        # 旬ごとの最初の日（最後に全部の日数）
            "sites": [site_name(s) for s in sites], "bars": bars, "avail": avail,
            "need": [required_on(periods, first + timedelta(days=k)) for k in range(total)],   # 日ごとのオペ必要人数
            "jun_need": [required_ope(periods, j) for j in juns]}                              # 表に出ている旬ごとの数字


TIP_CSS = """
.hint { margin: 0 4px 6px; font-size: 12px; color: #6B7480; }
.embedded .hint { display: none; }
#tip { position: fixed; z-index: 50; display: none; max-width: min(340px, calc(100vw - 16px)); box-sizing: border-box; padding: 9px 11px 10px;
  border: 1px solid #8F99A3; border-radius: 6px; background: #fff; box-shadow: 0 6px 18px rgba(15,23,42,.28);
  font-size: 13px; line-height: 1.45; color: #111; pointer-events: none; }
#tip .tip-date { margin: -9px -11px 0; padding: 6px 11px; border-radius: 5px 5px 0 0; background: #EDF1F5; border-bottom: 1px solid #C9D2DB;
  font-size: 14px; font-weight: bold; color: #2E3F8F; }
#tip .tip-h { margin-top: 6px; font-size: 12px; font-weight: bold; color: #4A4A4A; }
#tip .tip-site { margin-top: 5px; }
#tip .tip-site b { display: block; }
#tip .tip-site span { display: block; padding-left: 2px; color: #333; }
#tip .tip-site i { display: inline-block; width: 11px; height: 11px; margin-right: 5px; border-radius: 2px; vertical-align: -1px;
  border: 1px solid rgba(0,0,0,.28); box-sizing: border-box; }
#tip .tip-site.off { color: #777; }
#tip .tip-site.off b { font-weight: normal; }
#tip .tip-site.off span { color: #777; }
#tip .tip-none { margin-top: 5px; color: #777; }
#tip .tip-sum { margin-top: 7px; padding-top: 6px; border-top: 1px solid #DBE0E5; }
#tip .tip-sum b { font-size: 16px; }
#tip .tip-lv { display: inline-block; margin-top: 4px; padding: 1px 8px; border-radius: 4px; font-weight: bold; }
#tip .tip-lv.short { background: #C62828; color: #fff; }
#tip .tip-lv.full { background: #F2C94C; color: #111; }
#tip .tip-note { margin-top: 4px; font-size: 11.5px; color: #777; }
"""

TIP_JS = """
// 表の上にカーソルを合わせた日（スマホ・タブレットはタッチした日）の、進行中の現場とオペ必要人数を小さな窓に出す
(function () {
  var D = window.SCHED;
  var svg = document.querySelector("svg.right"), tip = document.getElementById("tip"), guide = document.getElementById("guide");
  if (!D || !svg || !tip || !guide) return;
  var scroller = svg.parentNode, WD = ["日", "月", "火", "水", "木", "金", "土"], lastType = "mouse";
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }
  // 画面の横の位置 → 何旬目の、何日目か
  function dayAt(clientX) {
    var r = svg.getBoundingClientRect(), n = D.js.length - 1;
    if (!r.width) return null;
    var u = (clientX - r.left) / r.width * n;
    if (u < 0 || u >= n) return null;
    var i = Math.floor(u), a = D.js[i], len = D.js[i + 1] - a, k = Math.min(len - 1, Math.floor((u - i) * len));
    return { day: a + k, jun: i, x: D.left + D.cell * (i + (k + 0.5) / len) };
  }
  function html(p) {
    var dt = new Date(D.y, D.m - 1, D.d + p.day), groups = [], at = {}, on = 0;
    D.bars.forEach(function (b) {
      if (b.s > p.day || b.e < p.day) return;
      if (!(b.site in at)) { at[b.site] = groups.length; groups.push({ name: D.sites[b.site], items: [], on: false }); }
      var g = groups[at[b.site]];
      g.items.push(b);
      if (b.on) g.on = true;
    });
    groups.forEach(function (g) { if (g.on) on++; });
    var out = '<div class="tip-date">' + dt.getFullYear() + "年" + (dt.getMonth() + 1) + "月" + dt.getDate() + "日（" + WD[dt.getDay()] + "）</div>";
    out += '<div class="tip-h">進行中の現場　' + on + "件</div>";
    if (!on) out += '<div class="tip-none">この日に進行中の現場はありません</div>';
    [true, false].forEach(function (want) {
      groups.forEach(function (g) {
        if (g.on !== want) return;
        out += '<div class="tip-site' + (g.on ? "" : " off") + '"><b>' + esc(g.name) + "</b>";
        g.items.forEach(function (b) { out += '<span><i style="background:' + esc(b.color) + '"></i>' + esc(b.label) + "</span>"; });
        out += "</div>";
      });
    });
    var need = D.need[p.day] || 0, table = D.jun_need[p.jun] || 0;
    out += '<div class="tip-sum">オペ必要人数 <b>' + need + "</b>人　／　オペの人数 " + D.avail + "人</div>";
    if (need > D.avail) out += '<div class="tip-lv short">オペが' + (need - D.avail) + "人足りない</div>";
    else if (need === D.avail && need > 0) out += '<div class="tip-lv full">オペがちょうど</div>';
    if (table !== need) out += '<div class="tip-note">下の表の数字は、この旬でいちばん多い日の人数（' + table + "人）です</div>";
    return out;
  }
  function hide() { tip.style.display = "none"; guide.setAttribute("visibility", "hidden"); }
  function show(cx, cy) {
    var p = dayAt(cx);
    if (!p) { hide(); return; }
    guide.setAttribute("x1", p.x); guide.setAttribute("x2", p.x); guide.setAttribute("visibility", "visible");
    tip.innerHTML = html(p);
    tip.style.display = "block";
    var w = tip.offsetWidth, h = tip.offsetHeight, x = cx + 16, y = cy + 16;
    if (x + w > window.innerWidth - 4) x = cx - w - 16;
    if (x < 4) x = 4;
    if (y + h > window.innerHeight - 4) y = Math.max(4, window.innerHeight - h - 4);
    tip.style.left = x + "px"; tip.style.top = y + "px";
  }
  svg.addEventListener("pointermove", function (e) { if (e.pointerType === "mouse") show(e.clientX, e.clientY); });
  svg.addEventListener("pointerleave", function (e) { if (e.pointerType === "mouse") hide(); });
  document.addEventListener("pointerdown", function (e) { lastType = e.pointerType || "mouse"; }, true);
  // 指でタッチしたとき：タッチした日を出す。表の外をタッチすると消える。
  // （ほかのページの中に埋め込まれているときは、タッチで画面いっぱいに開く動きを優先する）
  document.addEventListener("click", function (e) {
    if (lastType === "mouse") return;
    if (/(^| )embedded( |$)/.test(document.documentElement.className)) return;
    if (svg.contains(e.target)) show(e.clientX, e.clientY); else hide();
  });
  scroller.addEventListener("scroll", hide);
  window.addEventListener("scroll", hide);
})();
"""


def render(data: dict) -> str:
    """ページ全体。左の欄（現場名）は動かさず、右の表だけ横にスクロールする。
    お知らせ（warnings）はページに載せない（酒井さんにだけ伝える。main が画面に出す）。"""
    asof = to_date(data.get("asof")) or date.today()
    juns = jun_list(asof)
    axis = Axis(juns)
    periods, _ = valid_periods(data)
    sites = sites_of(data)
    avail = available_ope(data)
    W = axis.x1 + 2
    g = []          # SVGの部品
    late = []       # 今日の線より上に描く、棒の中の字
    y = TOP_H

    # 月と旬の見出し
    head_y = y
    for i in range(0, len(juns), 3):
        j = juns[i]
        x = LEFT + CELL * i
        g.append(f'<rect x="{x}" y="{y}" width="{CELL * 3}" height="{MONTH_H}" fill="{HEAD2}" stroke="{LINE}"/>')
        label = f"{j.year}年{j.month}月" if (i == 0 or j.month == 1) else f"{j.month}月"
        g.append(text(x + CELL * 1.5, y + 18, label, 13, INK, "middle", True))
    for i, j in enumerate(juns):
        x = LEFT + CELL * i
        g.append(f'<rect x="{x}" y="{y + MONTH_H}" width="{CELL}" height="{JUN_H}" fill="#FAFBFC" stroke="#C9D2DB"/>')
        g.append(text(x + CELL / 2, y + MONTH_H + 14, j.label[0], 11, "#666", "middle"))
    g.append(f'<rect x="0" y="{y}" width="{LEFT}" height="{MONTH_H + JUN_H}" fill="{HEAD}" stroke="{LINE}"/>')
    g.append(text(LEFT / 2, y + 29, "現　場", 13, INK, "middle", True))
    y += MONTH_H + JUN_H
    body_top = y

    # 現場の行
    rows = []
    for s in sites:
        placed, n = lanes(bars_for_site(s, periods), axis)
        names = wrap_name(site_name(s))
        h = max(n * LANE_H + ROW_PAD * 2, len(names) * 18 + 44)
        rows.append((s, placed, names, y, h))
        y += h
    body_bottom = y

    # 升目・休暇の帯（棒より下に描く）
    for s, placed, names, ry, h in rows:
        g.append(f'<rect x="0" y="{ry}" width="{W}" height="{h}" fill="#fff" stroke="{LINE}"/>')
        g.append(f'<rect x="0.5" y="{ry + 0.5}" width="{LEFT - 1}" height="{h - 1}" fill="#FAFBFC"/>')   # 左の欄は、ごく薄い地の色
    for i in range(len(juns) + 1):
        x = LEFT + CELL * i
        c = LINE_MONTH if i % 3 == 0 else LINE_SOFT
        g.append(f'<line x1="{x}" y1="{body_top}" x2="{x}" y2="{body_bottom}" stroke="{c}"/>')
    for hol in data.get("holidays") or []:
        if not isinstance(hol, dict):
            continue
        sp = axis.span(hol.get("start"), hol.get("end"))
        if sp and sp[1] > sp[0]:
            g.append(f'<rect x="{sp[0]:.1f}" y="{body_top}" width="{sp[1] - sp[0]:.1f}" height="{body_bottom - body_top}" fill="#5B6B7B" opacity="0.14"/>')
            g.append(text((sp[0] + sp[1]) / 2, body_top + 11, hol.get("name") or "", 10, INK_SUB, "middle"))

    # 現場名と棒
    for s, placed, names, ry, h in rows:
        ty = ry + 20
        for line in names:
            g.append(text(8, ty, line, 14, INK, bold=True))
            ty += 18
        g.append(text(8, ty, f"リーダー {s.get('leader') or '未定'}／メイン {s.get('main_machine') or '−'}", 11, INK_SUB))
        g.append(text(8, ty + 15, f"今ある重機 {to_int(s.get('machines_now')) or 0}台", 11, INK_SUB))
        top = max([p[0] for p in placed], default=0) + 1
        for n, x0, x1, b in placed:
            by = ry + ROW_PAD + n * LANE_H + (h - ROW_PAD * 2 - top * LANE_H) / 2
            parts = bar_svg(x0, x1, by + 3, LANE_H - 6, COLORS.get(b["kind"], OTHER), bar_label(b), axis)
            g.append(parts[0])
            late += parts[1:]

    # 下の段①：オペ必要人数・オペの人数（2026-11-28 酒井さん：「使える人数」は、使えない人もいるかのような誤解を生むので使わない）
    y += 8
    for title, fn in (("オペ必要人数", lambda j: required_ope(periods, j)), ("オペの人数", lambda j: avail)):
        g.append(f'<rect x="0" y="{y}" width="{LEFT}" height="{SUM_H}" fill="{HEAD}" stroke="{LINE}"/>')
        g.append(text(8, y + 19, title, 13, INK, bold=True))
        for i, j in enumerate(juns):
            v = fn(j)
            cls = level(required_ope(periods, j), avail) if title == "オペ必要人数" else "ok"
            fg = "#fff" if cls == "short" else INK
            g.append(f'<rect class="cell {cls}" x="{LEFT + CELL * i}" y="{y}" width="{CELL}" height="{SUM_H}"/>')
            g.append(text(LEFT + CELL * (i + .5), y + 19, v, 13, fg, "middle", cls != "ok"))
        y += SUM_H
    y += 8

    # 下の段②：大型・特殊重機（いつも出す）
    special = special_rows(data, periods)
    if special:
        short = {norm(site_name(s)): (s.get("location_name") or site_name(s)[:8]) for s in sites}
        g.append(f'<rect x="0" y="{y}" width="{W}" height="22" fill="{HEAD}" stroke="{LINE}"/>')
        g.append(text(8, y + 16, "大型・特殊重機の使用状況", 13, TEAL, bold=True))
        y += 22
        sp_top = y
        for name, where, ps in special:
            g.append(f'<rect x="0" y="{y}" width="{W}" height="{LANE_H}" fill="#fff" stroke="{LINE}"/>')
            g.append(f'<rect x="0.5" y="{y + 0.5}" width="{LEFT - 1}" height="{LANE_H - 1}" fill="#FAFBFC"/>')
            g.append(text(8, y + 14, name, 11, INK, bold=True))
            if where:
                g.append(text(8, y + 27, f"今：{where}", 10, INK_SUB))
            for p in ps:
                sp = axis.span(p["start"], p["end"])
                if sp:
                    late += bar_svg(sp[0], sp[1], y + 4, LANE_H - 8, MACHINE,
                                    short.get(norm(p.get("site")), str(p.get("site") or "")), axis)
            y += LANE_H
        for i in range(0, len(juns) + 1, 3):
            g.append(f'<line x1="{LEFT + CELL * i}" y1="{sp_top}" x2="{LEFT + CELL * i}" y2="{y}" stroke="{LINE_MONTH}"/>')
        y += 8

    # 今日の線（升目より上、棒の字より下）
    tx = axis.x(asof)
    g.append(f'<line x1="{tx:.1f}" y1="{head_y}" x2="{tx:.1f}" y2="{body_bottom}" stroke="{RED}" stroke-width="2"/>')
    g.append(text(tx, head_y - 4, "今日", 11, RED, "middle", True))
    g += late

    H = y
    body = "\n".join(g)
    hover = json.dumps(dict(hover_data(juns, periods, sites, avail), left=LEFT, cell=CELL),
                       ensure_ascii=False, separators=(",", ":"))
    for ch in "<>&":            # 現場名・メモに < > & があっても、ページの作りを壊さないようにする
        hover = hover.replace(ch, "\\u%04x" % ord(ch))
    guide = (f'<line id="guide" x1="{LEFT}" y1="{head_y}" x2="{LEFT}" y2="{H - 8:.0f}" stroke="{NAVY}" stroke-width="1.5" '
             f'stroke-dasharray="4 3" visibility="hidden" pointer-events="none"/>')
    legend = "".join(f'<span><i style="background:{COLORS[k]}"></i>{esc(k)}</span>' for k in LEGEND)
    view = LEFT + CELL * FIRST_VIEW          # 最初の画面に入れる幅（左の欄＋3か月）
    view_phone = LEFT + CELL * FIRST_VIEW_PHONE
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>全現場スケジュール表</title>
<link rel="icon" href="favicon.png">
<style>
:root {{ --u: min(calc((100vw - 12px) / {view}), {MAX_SCALE}px); }}
@media (max-width: 700px) {{ :root {{ --u: calc((100vw - 12px) / {view_phone}); }} }}
body {{ margin: 6px; background: #fff; font-family: "游ゴシック", "Yu Gothic", Meiryo, "Hiragino Kaku Gothic ProN", "Noto Sans JP", sans-serif; color: {INK}; }}
h1 {{ margin: 2px 4px 4px; padding: 3px 0 3px 10px; border-left: 6px solid {NAVY}; font-size: 20px; letter-spacing: .08em; color: {INK}; }}
.sub {{ margin: 2px 4px 6px; font-size: 13px; color: {INK_SUB}; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 4px 12px; margin: 0 4px 6px; font-size: 13px; }}
.legend span {{ display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; }}
.legend i {{ width: 14px; height: 14px; border-radius: 2px; display: inline-block; border: 1px solid rgba(0,0,0,.28); box-sizing: border-box; }}
.chart {{ display: flex; align-items: flex-start; }}
.scroll {{ overflow-x: auto; flex: 1; min-width: 0; -webkit-overflow-scrolling: touch; }}
svg {{ display: block; flex: none; height: auto; max-width: none; }}
svg.left {{ width: calc(var(--u) * {LEFT}); }}
svg.right {{ width: calc(var(--u) * {W - LEFT}); }}
svg text {{ font-family: "游ゴシック", "Yu Gothic", Meiryo, "Hiragino Kaku Gothic ProN", "Noto Sans JP", sans-serif; }}
.cell {{ fill: #fff; stroke: #C9D2DB; }}
.cell.short {{ fill: {RED}; }}
.cell.full {{ fill: {YEL}; }}
.tap {{ display: none; }}
/* Notionのページの中（埋め込み）で見ているとき：題名を出さず、表をタッチすると画面いっぱいに開く */
.embedded h1 {{ display: none; }}
.embedded .sub {{ margin-top: 0; }}
.embedded .tap {{ display: block; margin: 0 4px 6px; padding: 6px 10px; border-radius: 6px; background: {NAVY}; color: #fff; font-size: 14px; font-weight: bold; text-align: center; text-decoration: none; }}
.embedded .chart {{ cursor: pointer; }}
{TIP_CSS}</style>
</head>
<body>
<h1>全現場スケジュール表</h1>
<p class="sub">{asof.isoformat()} 時点　／　横に動かすと1年先まで見られます（指で広げて拡大もできます）</p>
<div class="legend">{legend}<span><i style="background:{RED}"></i>オペが足りない</span><span><i style="background:{YEL}"></i>オペがちょうど</span></div>
<p class="hint">表の上にカーソルを合わせる（スマホ・タブレットはタッチする）と、その日に進行中の現場とオペ必要人数が出ます</p>
<a class="tap" href="genba-schedule.html" target="_blank" rel="noopener">表をタッチすると、画面いっぱいに大きく開きます</a>
<div class="chart" id="chart">
<svg class="left" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {LEFT} {H:.0f}">
{body}
</svg>
<div class="scroll">
<svg class="right" xmlns="http://www.w3.org/2000/svg" viewBox="{LEFT} 0 {W - LEFT} {H:.0f}">
{body}
{guide}
</svg>
</div>
</div>
<div id="tip"></div>
<script>
// Notionのページの中（埋め込み）のときだけ、表をタッチすると新しい画面でこのページをいっぱいに開く
(function () {{
  var inFrame = false;
  try {{ inFrame = window.self !== window.top; }} catch (e) {{ inFrame = true; }}
  // 業務管理ダッシュボードのパネルの中（アドレスのうしろに ?full=1）では、埋め込みの扱いにしない（2026-11-28）
  if (/[?&]full=1(&|$)/.test(location.search)) inFrame = false;
  if (!inFrame) return;
  document.documentElement.className += " embedded";
  document.getElementById("chart").addEventListener("click", function () {{
    window.open(location.href.split("#")[0], "_blank", "noopener");
  }});
}})();
</script>
<script>window.SCHED = {hover};</script>
<script>{TIP_JS}</script>
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
