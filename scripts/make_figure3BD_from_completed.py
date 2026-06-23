from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path("/Users/iyubin/Documents/Codex/2026-06-05/pdf")
RESULTS = ROOT / "outputs/figure3/figure3_completed_results.csv"
OUT_DIR = ROOT / "outputs/figure3"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


F_PANEL = font(34, True)
F_LABEL = font(26)
F_TICK = font(20)
F_SMALL = font(18)

COLORS = {
    1: (149, 179, 224),
    2: (230, 126, 34),
    3: (76, 120, 168),
    4: (89, 161, 79),
    5: (72, 173, 213),
    6: (110, 122, 145),
    7: (92, 62, 150),
}


def center(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fnt, fill=(40, 40, 40)) -> None:
    bbox = draw.textbbox((0, 0), text, font=fnt)
    draw.text((xy[0] - (bbox[2] - bbox[0]) / 2, xy[1] - (bbox[3] - bbox[1]) / 2), text, font=fnt, fill=fill)


def rotated_label(img: Image.Image, text: str, xy: tuple[int, int]) -> None:
    tmp = Image.new("RGBA", (330, 52), (255, 255, 255, 0))
    td = ImageDraw.Draw(tmp)
    td.text((0, 0), text, font=F_LABEL, fill=(30, 30, 30))
    img.alpha_composite(tmp.rotate(270, expand=True), xy)


def ymap(value: float, top: int, bottom: int, lo: float = -0.35, hi: float = 1.05) -> int:
    return int(bottom - (value - lo) / (hi - lo) * (bottom - top))


def draw_boxplot(draw: ImageDraw.ImageDraw, values: np.ndarray, cx: int, top: int, bottom: int, color: tuple[int, int, int]) -> None:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return
    if len(values) >= 2:
        q1, med, q3 = np.percentile(values, [25, 50, 75])
        iqr = q3 - q1
        low = max(float(values.min()), q1 - 1.5 * iqr)
        high = min(float(values.max()), q3 + 1.5 * iqr)
        box_w = 54
        draw.line((cx, ymap(low, top, bottom), cx, ymap(high, top, bottom)), fill=color, width=3)
        draw.line((cx - 18, ymap(low, top, bottom), cx + 18, ymap(low, top, bottom)), fill=color, width=3)
        draw.line((cx - 18, ymap(high, top, bottom), cx + 18, ymap(high, top, bottom)), fill=color, width=3)
        draw.rectangle(
            (cx - box_w // 2, ymap(q3, top, bottom), cx + box_w // 2, ymap(q1, top, bottom)),
            fill=color + (185,),
            outline=color,
            width=2,
        )
        draw.line((cx - box_w // 2, ymap(med, top, bottom), cx + box_w // 2, ymap(med, top, bottom)), fill=(255, 255, 255), width=4)

    rng = np.random.default_rng(1000 + len(values) + cx)
    for value in values:
        px = int(cx + rng.uniform(-23, 23))
        py = ymap(float(value), top, bottom)
        draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=color)

    mean_y = ymap(float(values.mean()), top, bottom)
    draw.ellipse((cx - 5, mean_y - 5, cx + 5, mean_y + 5), fill=(25, 25, 25))


def draw_panel(draw: ImageDraw.ImageDraw, img: Image.Image, df: pd.DataFrame, condition: str, panel: str, title: str, box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    draw.text((left - 55, top - 55), panel, font=F_PANEL, fill=(0, 0, 0))
    draw.text((left, top - 48), title, font=F_SMALL, fill=(40, 40, 40))
    draw.line((left, bottom, right, bottom), fill=(45, 45, 45), width=2)
    draw.line((left, top, left, bottom), fill=(45, 45, 45), width=2)

    for val in np.arange(-0.2, 1.01, 0.2):
        yy = ymap(float(val), top, bottom)
        draw.line((left, yy, right, yy), fill=(230, 230, 230), width=2)
        draw.text((left - 58, yy - 12), f"{val:.1f}", font=F_TICK, fill=(85, 85, 85))

    width = right - left
    sub_all = df[df["condition"] == condition]
    for n in range(1, 8):
        cx = int(left + (n - 0.5) / 7 * width)
        draw.line((cx, bottom, cx, bottom + 10), fill=(45, 45, 45), width=2)
        center(draw, (cx, bottom + 35), str(n), F_TICK)
        values = sub_all.loc[sub_all["n_tf"] == n, "pearson_r"].to_numpy(float)
        values = values[np.isfinite(values)]
        if len(values):
            draw_boxplot(draw, values, cx, top, bottom, COLORS[n])

    center(draw, ((left + right) // 2, bottom + 78), "number of TFs", F_LABEL)
    rotated_label(img, "Pearson's R", (left - 115, top + 132))


def main() -> None:
    if not RESULTS.exists():
        raise SystemExit(f"missing {RESULTS}")
    df = pd.read_csv(RESULTS)
    if df.empty:
        raise SystemExit("no completed Figure 3 results yet")

    img = Image.new("RGBA", (1550, 900), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw_panel(draw, img, df, "self_off", "B", "without self-competition: single-hit fitting", (180, 125, 740, 675))
    draw_panel(draw, img, df, "self_on", "D", "with self-competition: single-hit fitting", (930, 125, 1490, 675))

    completed = len(df)
    draw.text((180, 805), f"Completed XML fits included: {completed}. Full Figure 3B/D requires 2032 single-hit fits across self-off/self-on conditions.", font=F_SMALL, fill=(65, 65, 65))

    out_png = OUT_DIR / "figure3BD_singlehit_from_completed.png"
    out_pdf = OUT_DIR / "figure3BD_singlehit_from_completed.pdf"
    rgb = img.convert("RGB")
    rgb.save(out_png)
    rgb.save(out_pdf, "PDF", resolution=300.0)
    print(f"wrote {out_png}")
    print(f"wrote {out_pdf}")


if __name__ == "__main__":
    main()
