# 各現場の資料（スマホで拡大して見る用）

現場の工程表・図面を、スマホで指で拡大して見るためのページ。Notion「各現場の資料」からリンクしている。

- 資料を足す: `render.py` の SOURCES に「キー: (元のPDF, svg か jpg)」を足す → `build.py` の SITES に名前を足す → `python render.py` → `python build.py` → commit・push
  - 字の多い資料（工程表・フロー図など）は svg（ベクター。拡大してもくっきり）
  - 線の多い CAD 図面（施工計画図など）は jpg（長い辺 7200px）。svg だと1ページ20MB超になりスマホで重い
- 3Dモデルなど HTML はそのまま置き、`build.py` の EXTRA に足す
- 社外秘の金額などは載せない（URLを知っていれば誰でも見られる）
