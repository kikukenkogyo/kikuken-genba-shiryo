# -*- coding: utf-8 -*-
"""genba-schedule.html を、スマホの幅の画像（genba-schedule.png）にする。
使い方: python schedule/snapshot.py
Notionのページに貼る用。Notionの画像はタッチすると画面いっぱいに開いて、指で拡大できる
（埋め込みの中からは別の画面を開けなかったので、画像にした。2026-11-13）。
Edge（無ければ Chrome）を画面なしで動かして撮り、下の余白を切る。"""
import pathlib, subprocess, sys, tempfile, time

from PIL import Image, ImageChops

ROOT = pathlib.Path(__file__).resolve().parent.parent
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
WIDTH, HEIGHT, SCALE = 600, 2400, 2.5     # スマホの幅で撮る（700px以下＝字が大きい方の形）。拡大してもくっきり見えるよう2.5倍


def trim(img: Image.Image, margin: int = 16) -> Image.Image:
    """まわりの白い余白を切る（少しだけ残す）。"""
    rgb = img.convert("RGB")
    box = ImageChops.difference(rgb, Image.new("RGB", rgb.size, (255, 255, 255))).getbbox()
    if not box:
        return rgb
    return rgb.crop((0, 0, rgb.width, min(rgb.height, box[3] + margin)))


def snapshot(src: pathlib.Path, out: pathlib.Path) -> pathlib.Path:
    browser = next((b for b in BROWSERS if pathlib.Path(b).exists()), None)
    if browser is None:
        raise SystemExit("Edge も Chrome も見つかりません。画像は作れませんでした")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        raw = pathlib.Path(tmp) / "raw.png"
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        f"--user-data-dir={tmp}\\prof", f"--force-device-scale-factor={SCALE}",
                        f"--window-size={WIDTH},{HEIGHT}", f"--screenshot={raw}", src.resolve().as_uri() + "#shot"],
                       check=True, timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):                 # ブラウザは先に戻ってくることがあるので、画像ができるまで待つ
            if raw.exists() and raw.stat().st_size > 0:
                break
            time.sleep(0.5)
        else:
            raise SystemExit("画面写真が撮れませんでした")
        time.sleep(0.5)
        trim(Image.open(raw)).save(out, optimize=True)
    return out


if __name__ == "__main__":
    src = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "genba-schedule.html"
    out = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "genba-schedule.png"
    p = snapshot(src, out)
    w, h = Image.open(p).size
    print(f"作りました: {p}（{w}×{h}px・{p.stat().st_size // 1024}KB）")
