# 各現場の資料ページを作る（img/ の画像から index.html と資料ごとのページを生成）
# 資料を足すときは SITES に足して、img/ に「キー-ページ番号.jpg」を置いてから python build.py
import pathlib, html

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
]

HEAD = """<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{title}</title>
<style>
body{{margin:0;font-family:system-ui,sans-serif;background:#f4f4f4;color:#222}}
header{{background:#e4007f;color:#fff;padding:14px 16px;font-size:18px;font-weight:bold}}
h2{{font-size:17px;margin:20px 16px 8px}}
a.btn{{display:block;margin:8px 16px;padding:16px;background:#fff;border-radius:10px;
  color:#222;text-decoration:none;font-size:17px;box-shadow:0 1px 3px rgba(0,0,0,.15)}}
p.note{{margin:10px 16px;font-size:14px;color:#555}}
img{{display:block;width:100%;height:auto;margin:0 0 12px;background:#fff}}
div.ret{{margin:10px 16px;padding:12px 14px;background:#fff4d6;border:2px solid #f0b400;
  border-radius:10px;font-size:15px;line-height:1.6}}
</style></head><body>
"""

# Notion への戻り方（Notion アプリの中に開く画面なので、左上の ✕ で閉じる。iPhone で確認 2026-10-23）
RETURN = ('<div class="ret"><b>見終わったら</b><br>'
          '画面の一番左上の <b>✕</b> をタッチすると Notion に戻ります</div>')

def page_count(key):
    return len(list((ROOT / "img").glob(f"{key}-*.jpg")))

out = [HEAD.format(title="各現場の資料"), "<header>各現場の資料（菊建興業）</header>",
       '<p class="note">資料をタッチ → 画像を指で広げると拡大できます。</p>', RETURN]
for site, docs in SITES:
    out.append(f"<h2>{html.escape(site)}</h2>")
    for key, name in docs:
        n = page_count(key)
        label = name + (f"（{n}枚）" if n > 1 else "")
        out.append(f'<a class="btn" href="{key}.html">📄 {html.escape(label)}</a>')

        pg = [HEAD.format(title=f"{name}｜{site}"), f"<header>{html.escape(name)}</header>",
              f'<p class="note">{html.escape(site)}<br>指で広げると拡大できます。</p>', RETURN]
        for i in range(1, n + 1):
            src = f"img/{key}-{i}.jpg"
            pg.append(f'<img src="{src}" alt="{html.escape(name)} {i}ページ" loading="lazy">')
        pg.append(RETURN + '</body></html>')
        (ROOT / f"{key}.html").write_text("\n".join(pg), encoding="utf-8")
out.append("</body></html>")
(ROOT / "index.html").write_text("\n".join(out), encoding="utf-8")
print("ok")
