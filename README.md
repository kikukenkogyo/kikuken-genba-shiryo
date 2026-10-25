# 各現場の資料（スマホで拡大して見る用）

現場の工程表・図面を、スマホで指で拡大して見るためのページ。Notion「各現場の資料」からリンクしている。

- 資料を足す: `render.py` の SOURCES に「キー: (元のPDF, svg か jpg)」を足す → `build.py` の SITES に名前を足す → `python render.py` → `python build.py` → commit・push
  - 字の多い資料（工程表・フロー図など）は svg（ベクター。拡大してもくっきり）
  - 線の多い CAD 図面（施工計画図など）は jpg（長い辺 7200px）。svg だと1ページ20MB超になりスマホで重い
- 3Dモデル（HTML）は `mitsumori-teian/scripts/publish_3d.py` で載せる（部品を中に入れる・extra.json に足す・build・push・公開の確認まで自動）。手で足すときは extra.json に書いて `python build.py`
- 社外秘の金額などは載せない（URLを知っていれば誰でも見られる）
- 動画は `video/` に mp4（スマホ用に 960×540・crf30 で軽くする。ffmpeg）を置き、`build.py` の VIDEOS に足す → `python build.py`
- アイコン：apple-touch-icon.png（180）・icon-192/512.png・favicon.png。元は「計画図＋3D」の案E（2026-10-23 酒井さん選択）
- KUDAN（九段南の資料の元）は 2026-10-26 から 元請様提出資料_20261022\説明資料一式 を読む（重機を新しい形にした版）
