# PDF → スマホ用の画像（img/）を作る
#   svg  … 字の多い資料。ベクターのまま（いくら拡大してもくっきり）
#   jpg  … 線の多い CAD 図面。SVG だと重すぎるので細かい画像（長い辺 7200px）
# 使い方: python render.py  → そのあと python build.py
import pathlib, fitz

ROOT = pathlib.Path(__file__).parent
DESK = pathlib.Path.home() / "OneDrive" / "Desktop"
KUDAN = DESK / "AI作業場" / "九段南_既存地下3Dモデル" / "スマホ公開用" / "データ便から取得_20261022修正版"

def kudan(prefix):
    return next(KUDAN.rglob(f"{prefix}_*.pdf"))

SOURCES = {
    # キー: (元の PDF, 形式)
    "fukuzumi-koutei":  (DESK / "現場/進行中現場/江東区福住/工程/工程表　福住.pdf", "svg"),
    "fukuzumi-kasetsu": (DESK / "現場/進行中現場/江東区福住/cad/仮設計画図（修正版）福住.pdf", "jpg"),
    "fukuzumi-sekou":   (DESK / "現場/進行中現場/江東区福住/cad/施工計画図　福住.pdf", "jpg"),
    "kudan-koutei":     (kudan("02"), "svg"),
    "kudan-flow":       (kudan("03"), "svg"),
    "kudan-step":       (kudan("04"), "svg"),
    "hokima-annai":     (DESK / "現場/進行中現場/都営保木間第５アパート/現場案内図（JKK保木間第５アパート）.pdf", "svg"),
    "hokima-sekou":     (DESK / "現場/進行中現場/都営保木間第５アパート/施工計画図　保木間第5アパート.pdf", "jpg"),
}
JPG_LONG_SIDE = 7200

out = ROOT / "img"
out.mkdir(exist_ok=True)
for key, (pdf, kind) in SOURCES.items():
    for old in out.glob(f"{key}-*.*"):
        old.unlink()
    doc = fitz.open(pdf)
    total = 0
    for i, page in enumerate(doc, 1):
        if kind == "svg":
            f = out / f"{key}-{i}.svg"
            f.write_text(page.get_svg_image(text_as_path=True), encoding="utf-8")
        else:
            z = JPG_LONG_SIDE / max(page.rect.width, page.rect.height)
            f = out / f"{key}-{i}.jpg"
            page.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False).save(f, jpg_quality=80)
        total += f.stat().st_size
    print(f"{key}: {doc.page_count}ページ {kind} 合計 {total / 1e6:.1f}MB")
