# 各現場の資料ページを作る（img/ の画像から index.html と資料ごとのページを生成）
# 資料を足すときは SITES に足して、img/ に「キー-ページ番号.jpg」を置いてから python build.py
import pathlib, html, json

ROOT = pathlib.Path(__file__).parent
SITES = [
    ("江東区福住4階建建物解体工事", [
        ("fukuzumi-koutei", "工程表"),
        ("fukuzumi-kasetsu", "仮設計画図（修正版）"),
        ("fukuzumi-sekou", "施工計画図"),
    ]),
    ("九段南計画解体工事", [
        ("kudan-koutei", "工程表（地下解体）"),
        ("kudan-flow", "作業フロー図（地下解体）"),
        ("kudan-step", "解体の流れ・ステップ図（地下解体）"),
    ]),
    ("都営保木間第５アパート除却工事", [
        ("hokima-annai", "現場案内図"),
        ("hokima-sekou", "施工計画図"),
    ]),
    ("（仮称）世田谷区砧6-25 自走式立体駐車場解体工事", [
        ("kinuta-koutei", "工程表（10/28着工）"),
    ]),
]

# 一覧ページ（index.html）に出すのは、菊建ページ（Notion「各現場の資料」）に載せている資料だけ。
# 見積段階・提案用の3D/動画（extra.json・videos.json で足されるもの）は、ページは作るが一覧には出さない
# （2026-10-25 酒井さん：決まっていない仕事が職人さんに見えると混乱する）。一覧に出すときはここに足す
INDEX_SITES = [s for s, _ in SITES]
INDEX_LINKS = {"kudan-3d.html", "kinuta-rittyu-3d.html", "kinuta-rittyu-video.html"}
# 現場ごとの「LINEで送る用」のページ（その現場の資料だけを並べる。元請様・協力会社さんにも送れる）。{"ファイル名": "現場名"}
SHARE_PAGES = {"kinuta-rittyu.html": "（仮称）世田谷区砧6-25 自走式立体駐車場解体工事"}  # 2026-10-27 酒井さん
# 酒井さん専用の一覧（見積段階の3D・動画も含めて全部。iPad のホーム画面用）。名前は推測されにくくしてある
ALL_INDEX = "sakai-c9521c84.html"
# 酒井さん専用の一覧は「受注した工事」と「見積段階」に分けて出す（2026-10-29 酒井さん）。受注したら、ここに現場名を足す
# （菊建ページ＝Notion に載せている現場は受注した工事。それ以外は見積段階として下に出る）
UKEOI_SITES = set(INDEX_SITES)

# 説明資料の PDF（ステップ図・フロー図・0工程表・足場計画図など）は docs.json に書く（mitsumori-teian/scripts/publish_docs.py が自動で足す 2026-10-26）
#   {"現場名": [["キー", "表示名"], ...]}。画像は img/ の「キー-番号.svg/jpg」
_dj = ROOT / "docs.json"
for _site, _items in (json.loads(_dj.read_text(encoding="utf-8")) if _dj.exists() else {}).items():
    _s = next((x for x in SITES if x[0] == _site), None)
    if _s is None: SITES.append((_site, [])); _s = SITES[-1]
    _have = {k for k, _ in _s[1]}
    _s[1].extend(tuple(i) for i in _items if i[0] not in _have)

# そのまま置いた HTML（build.py では作らない。ファイルは手で置く）
EXTRA = {}
# 3Dモデルなどは extra.json に書く（mitsumori-teian/scripts/publish_3d.py が自動で足す）。{"現場名": [["ファイル.html", "表示名"], ...]}
_ej = ROOT / "extra.json"
for _site, _items in (json.loads(_ej.read_text(encoding="utf-8")) if _ej.exists() else {}).items():
    EXTRA.setdefault(_site, []).extend(tuple(i) for i in _items)
# 図面の資料がまだ無く、3Dだけある現場も一覧に出す
for _site in EXTRA:
    if _site not in [s_ for s_, _ in SITES]: SITES.append((_site, []))

# 動画（video/ に mp4 を置く。スマホ用に 960×540 へ軽くしたもの）。ページは build.py が作る
VIDEOS = {}
# 動画は videos.json に書く（publish_3d.py --video が自動で足す）。{"現場名": [["ページのキー", "video/….mp4", "表示名"], ...]}
_vj = ROOT / "videos.json"
for _site, _items in (json.loads(_vj.read_text(encoding="utf-8")) if _vj.exists() else {}).items():
    VIDEOS.setdefault(_site, []).extend(tuple(i) for i in _items)
    if _site not in [s_ for s_, _ in SITES]: SITES.append((_site, []))

HEAD = """<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="icon" type="image/png" href="favicon.png">
<link rel="manifest" href="manifest.json">
<meta name="apple-mobile-web-app-title" content="現場資料">
<meta name="theme-color" content="#e4007f">
<title>{title}</title>
<style>
body{{margin:0;font-family:system-ui,sans-serif;background:#f4f4f4;color:#222}}
header{{background:#e4007f;color:#fff;padding:14px 16px;font-size:18px;font-weight:bold}}
h2{{font-size:17px;margin:20px 16px 8px}}
a.btn{{display:block;margin:8px 16px;padding:16px;background:#fff;border-radius:10px;
  color:#222;text-decoration:none;font-size:17px;box-shadow:0 1px 3px rgba(0,0,0,.15)}}
p.note{{margin:10px 16px;font-size:14px;color:#555}}
img{{display:block;width:100%;height:auto;margin:0 0 12px;background:#fff}}
h2.grp{{margin:22px 12px 6px;padding:8px 12px;background:#e4007f;color:#fff;border-radius:8px;font-size:16px}}
h2.grp.mitsu{{background:#6c757d}}
details.site{{margin:8px 12px;background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.15)}}
details.site>summary{{list-style:none;cursor:pointer;padding:16px 44px 16px 16px;font-size:17px;font-weight:bold;position:relative}}
details.site>summary::-webkit-details-marker{{display:none}}
details.site>summary::after{{content:"▼";position:absolute;right:16px;top:50%;transform:translateY(-50%) rotate(-90deg);color:#e4007f;font-size:14px;transition:transform .15s}}
details.site[open]>summary::after{{transform:translateY(-50%)}}
details.site[open]>summary{{border-bottom:1px solid #eee;color:#e4007f}}
details.site a.btn{{margin:8px 10px;background:#fafafa}}
details.site>div{{padding:2px 0 8px}}
div.ret{{margin:10px 16px;padding:12px 14px;background:#fff4d6;border:2px solid #f0b400;
  border-radius:10px;font-size:15px;line-height:1.6}}
</style></head><body>
"""

# Notion への戻り方（Notion アプリの中に開く画面なので、左上の ✕ で閉じる。iPhone で確認 2026-10-23）
RETURN = ('<div class="ret"><b>見終わったら</b><br>'
          '画面の一番左上の <b>✕</b> をタッチすると菊建ページに戻ります</div>')

def pages(key):
    # img/ の「キー-番号.svg / .jpg」をページ順に返す（render.py が作る）
    files = [f for f in (ROOT / "img").glob(f"{key}-*.*") if f.suffix in (".svg", ".jpg")]
    return sorted(files, key=lambda f: int(f.stem.rsplit("-", 1)[1]))

def page_count(key):
    return len(pages(key))

out = [HEAD.format(title="各現場の資料"), "<header>各現場の資料（菊建興業）</header>",
       '<p class="note">現場名をタッチすると資料が出ます → 資料をタッチ → 画像を指で広げると拡大できます。</p>', RETURN]
# ホーム画面に追加したとき、この一覧が開くように manifest を外す（iPhone は manifest があると start_url＝入口の一覧を開いてしまう。2026-10-25 確認）
# manifest が無ければ、iPhone は開いているページの URL をそのまま登録する
allout = [HEAD.format(title="全部の資料（見積段階も含む）").replace('<link rel="manifest" href="manifest.json">', "").replace('content="現場資料"', 'content="全部の資料"'), "<header>全部の資料（見積段階も含む）</header>",
          '<p class="note">見積段階の資料も入っています。URL を社外の人に送らないでください。<br>現場名をタッチすると資料が出ます。</p>']
all_uke, all_mitsu = [], []
for site, docs in SITES:
    links = []  # 一覧に出すボタン（INDEX_SITES / INDEX_LINKS にあるものだけ）
    all_links = []  # 酒井さん専用の一覧（全部）
    for key, name in docs:
        n = page_count(key)
        label = name + (f"（{n}枚）" if n > 1 else "")
        b = f'<a class="btn" href="{key}.html">📄 {html.escape(label)}</a>'
        all_links.append(b)
        if site in INDEX_SITES:
            links.append(b)

        pg = [HEAD.format(title=f"{name}｜{site}"), f"<header>{html.escape(name)}</header>",
              f'<p class="note">{html.escape(site)}<br>指で広げると拡大できます。</p>', RETURN]
        for i, f in enumerate(pages(key), 1):
            pg.append(f'<img src="img/{f.name}" alt="{html.escape(name)} {i}ページ" loading="lazy">')
        pg.append(RETURN + '</body></html>')
        (ROOT / f"{key}.html").write_text("\n".join(pg), encoding="utf-8")
    # 画像にしない資料（3Dモデルなど、そのまま置いた HTML）
    for href, label in EXTRA.get(site, []):
        b = f'<a class="btn" href="{href}">{html.escape(label)}</a>'
        all_links.append(b)
        if href in INDEX_LINKS:
            links.append(b)
    for key, src, label in VIDEOS.get(site, []):
        b = f'<a class="btn" href="{key}.html">{html.escape(label)}</a>'
        all_links.append(b)
        if f"{key}.html" in INDEX_LINKS:
            links.append(b)
        pg = [HEAD.format(title=f"{label}｜{site}"), f"<header>{html.escape(label[2:])}</header>",
              f'<p class="note">{html.escape(site)}<br>▶をタッチすると再生します。音が出ます。</p>', RETURN,
              f'<video src="{src}" controls playsinline preload="metadata" style="display:block;width:100%;height:auto;background:#000"></video>',
              RETURN + '</body></html>']
        (ROOT / f"{key}.html").write_text("\n".join(pg), encoding="utf-8")
    # 現場名のトグル（タッチで開くと資料が並ぶ）。現場が増えて一覧が長くなったため（2026-10-29 酒井さん）
    if links:
        out.append(f'<details class="site"><summary>{html.escape(site)}</summary><div>')
        out.extend(links); out.append("</div></details>")
    if all_links:
        grp = all_uke if site in UKEOI_SITES else all_mitsu
        grp.append(f'<details class="site"><summary>{html.escape(site)}</summary><div>')
        grp.extend(all_links); grp.append("</div></details>")
for _fn, _site in SHARE_PAGES.items():
    _b = []
    for site, docs in SITES:
        if site != _site: continue
        for key, name in docs:
            n = page_count(key)
            _b.append(f'<a class="btn" href="{key}.html">📄 {html.escape(name + (f"（{n}枚）" if n > 1 else ""))}</a>')
        _b += [f'<a class="btn" href="{h}">{html.escape(l)}</a>' for h, l in EXTRA.get(site, [])]
        _b += [f'<a class="btn" href="{k}.html">{html.escape(l)}</a>' for k, _, l in VIDEOS.get(site, [])]
    (ROOT / _fn).write_text("\n".join([HEAD.format(title=_site).replace('<link rel="manifest" href="manifest.json">', ""),
        f"<header>{html.escape(_site)}</header>", '<p class="note">資料をタッチすると開きます。図面は指で広げると拡大できます。3Dモデルは指で回せます。</p>'] + _b + ["</body></html>"]), encoding="utf-8")
out.append("</body></html>")
(ROOT / "index.html").write_text("\n".join(out), encoding="utf-8")
allout += ['<h2 class="grp">🏗 受注した工事</h2>'] + all_uke + ['<h2 class="grp mitsu">📝 見積段階</h2>'] + all_mitsu
allout.append("</body></html>")
(ROOT / ALL_INDEX).write_text("\n".join(allout), encoding="utf-8")
print("ok")
