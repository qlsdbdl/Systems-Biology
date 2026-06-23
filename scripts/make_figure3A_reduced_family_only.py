from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path("/Users/iyubin/Documents/Codex/2026-06-05/pdf")
RESULTS = ROOT / "outputs/figure3/figure3_completed_results.csv"
OUT_DIR = ROOT / "outputs/figure3/figure3A_reduced"


GROUPS = [
    ("CREB1_self", "combo001_CREB1", "CREB1 self"),
    ("ATF1", "combo011_CREB1-ATF1", "CREB1 + ATF1"),
    ("ATF4", "combo012_CREB1-ATF4", "CREB1 + ATF4"),
    ("ATF7", "combo013_CREB1-ATF7", "CREB1 + ATF7"),
    ("CREB3", "combo008_CREB1-CREB3", "CREB1 + CREB3"),
    ("CREB5", "combo009_CREB1-CREB5", "CREB1 + CREB5"),
    ("CREM", "combo010_CREB1-CREM", "CREB1 + CREM"),
]


COLORS = {
    "CREB1_self": (130, 130, 130),
    "ATF1": (240, 142, 48),
    "ATF4": (238, 158, 34),
    "ATF7": (222, 164, 31),
    "CREB3": (65, 65, 65),
    "CREB5": (128, 171, 0),
    "CREM": (55, 55, 55),
}


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


F_PANEL = font(32, True)
F_LABEL = font(26)
F_TICK = font(22)
F_SMALL = font(18)
F_BOLD = font(20, True)


def ymap(value: float, top: int, bottom: int, lo: float = 0.4, hi: float = 0.9) -> int:
    return int(bottom - (value - lo) / (hi - lo) * (bottom - top))


def center(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fnt, fill=(40, 40, 40)) -> None:
    bbox = draw.textbbox((0, 0), text, font=fnt)
    draw.text((xy[0] - (bbox[2] - bbox[0]) / 2, xy[1] - (bbox[3] - bbox[1]) / 2), text, font=fnt, fill=fill)


def rotated_text(img: Image.Image, text: str, xy: tuple[int, int]) -> None:
    tmp = Image.new("RGBA", (320, 54), (255, 255, 255, 0))
    td = ImageDraw.Draw(tmp)
    td.text((0, 0), text, font=F_LABEL, fill=(30, 30, 30))
    img.alpha_composite(tmp.rotate(270, expand=True), xy)


def load_reduced_results() -> pd.DataFrame:
    df = pd.read_csv(RESULTS)
    rows: list[dict[str, object]] = []
    for label, combo_id, model in GROUPS:
        hit = df[(df["condition"] == "self_on") & (df["combo_id"] == combo_id) & (df["seed"] == 0)]
        if hit.empty:
            raise SystemExit(f"missing completed result for {combo_id}")
        row = hit.iloc[0]
        rows.append(
            {
                "group": label,
                "model": model,
                "combo_id": combo_id,
                "seed": int(row["seed"]),
                "pearson_r": float(row["pearson_r"]),
                "rmse_delta_log2": float(row["rmse_delta_log2"]),
                "rates_file": row["rates_file"],
            }
        )
    return pd.DataFrame(rows)


def draw_plot(results: pd.DataFrame) -> Image.Image:
    img = Image.new("RGBA", (1320, 850), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    left, top, right, bottom = 140, 105, 1230, 520

    draw.text((55, 42), "A", font=F_PANEL, fill=(0, 0, 0))
    draw.text((left, 48), "Family TFs added to CREB1_self model (seed00 representative)", font=F_SMALL, fill=(35, 35, 35))

    draw.rectangle((left, top, right, bottom), fill=(236, 236, 236))
    for value in np.arange(0.4, 0.91, 0.1):
        yy = ymap(float(value), top, bottom)
        draw.line((left, yy, right, yy), fill=(255, 255, 255), width=3)
        draw.text((left - 55, yy - 12), f"{value:.1f}", font=F_TICK, fill=(85, 85, 85))

    draw.line((left, bottom, right, bottom), fill=(35, 35, 35), width=2)
    draw.line((left, top, left, bottom), fill=(35, 35, 35), width=2)

    baseline = float(results.loc[results["group"] == "CREB1_self", "pearson_r"].iloc[0])
    yy = ymap(baseline, top, bottom)
    draw.line((left, yy, right, yy), fill=(230, 0, 0), width=4)
    draw.text((left + 18, yy - 28), f"CREB1_self R={baseline:.3f}", font=F_BOLD, fill=(180, 0, 0))

    width = right - left
    n = len(results)
    for idx, row in results.reset_index(drop=True).iterrows():
        cx = int(left + (idx + 0.5) / n * width)
        value = float(row["pearson_r"])
        cy = ymap(value, top, bottom)
        color = COLORS[str(row["group"])]
        draw.line((cx, bottom, cx, bottom + 9), fill=(35, 35, 35), width=2)
        draw.ellipse((cx - 13, cy - 13, cx + 13, cy + 13), fill=color, outline=(20, 20, 20), width=2)
        draw.text((cx - 34, cy - 42), f"{value:.3f}", font=F_SMALL, fill=(25, 25, 25))
        label = str(row["group"])
        tmp = Image.new("RGBA", (150, 34), (255, 255, 255, 0))
        td = ImageDraw.Draw(tmp)
        td.text((0, 0), label, font=F_TICK, fill=(80, 80, 80))
        img.alpha_composite(tmp.rotate(315, expand=True), (cx - 48, bottom + 18))

    center(draw, ((left + right) // 2, 780), "TF added to CREB1_self model", F_LABEL)
    rotated_text(img, "Pearson's R", (left - 110, top + 115))
    draw.text(
        (left, 690),
        "Reduced reproduction: one completed fit per group. Non-family TFs are not plotted because Table S2 contains only ATF/CREB family PWMs.",
        font=F_SMALL,
        fill=(75, 75, 75),
    )
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = load_reduced_results()
    csv_path = OUT_DIR / "figure3A_reduced_family_only_metrics.csv"
    results.to_csv(csv_path, index=False)
    img = draw_plot(results)
    out_png = OUT_DIR / "figure3A_reduced_family_only.png"
    out_pdf = OUT_DIR / "figure3A_reduced_family_only.pdf"
    rgb = img.convert("RGB")
    rgb.save(out_png)
    rgb.save(out_pdf, "PDF", resolution=300.0)
    print(results.to_string(index=False))
    print(f"wrote {csv_path}")
    print(f"wrote {out_png}")
    print(f"wrote {out_pdf}")


if __name__ == "__main__":
    main()
