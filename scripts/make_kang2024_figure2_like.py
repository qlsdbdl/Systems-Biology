from __future__ import annotations

from pathlib import Path
import math
import re
import sys

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


TABLE_S2 = Path("/Users/iyubin/Downloads/Table S2.xlsx")
TABLE_S3 = Path("/Users/iyubin/Downloads/Table S3.xlsx")
RUN = sys.argv[1] if len(sys.argv) > 1 else "fit_01"
RATES = Path(f"outputs/kang2024_{RUN}_rates.txt")
OUTPUT_DIR = Path("outputs")

TF_NAMES = ["CREB1", "CREB3", "CREB5", "CREM", "ATF1", "ATF4", "ATF7"]
BASE_ORDER = ["A", "C", "G", "T"]
MUT_RE = re.compile(r"scanmut_single_pos_(\d+)_([ACGT])$")
REGIONS = [
    ("CRE1", 11, 18, (246, 95, 100, 90), (210, 0, 0)),
    ("CRE2", 35, 42, (246, 95, 100, 90), (210, 0, 0)),
    ("CRE3", 47, 54, (246, 95, 100, 90), (210, 0, 0)),
    ("cryptic", 63, 66, (90, 115, 255, 90), (20, 55, 210)),
    ("CRE4", 69, 76, (246, 95, 100, 90), (210, 0, 0)),
]
BASE_COLORS = {
    "A": (35, 160, 75),
    "C": (35, 90, 205),
    "G": (230, 145, 20),
    "T": (210, 40, 55),
}


def get_font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if mono:
        candidates = [
            "/System/Library/Fonts/Menlo.ttc",
            "/System/Library/Fonts/Supplemental/Courier New.ttf",
        ]
    else:
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


F_TITLE = get_font(44, True)
F_PANEL = get_font(34, True)
F_AXIS = get_font(25)
F_SMALL = get_font(21)
F_TINY = get_font(17)
F_SEQ = get_font(27, mono=True)
F_SEQ_LABEL = get_font(35)
F_BASE = get_font(76, True)


def complement(seq: str) -> str:
    return seq.translate(str.maketrans("ACGT", "TGCA"))


def read_data() -> pd.DataFrame:
    single = pd.read_excel(TABLE_S3, sheet_name="single-hit").rename(columns={"expression level": "measured_expression"})
    rates = pd.read_csv(RATES, sep=r"\s+").rename(columns={"id": "name", "HEK293_MPRA": "predicted_expression"})
    df = single.merge(rates, on="name", how="inner")
    if len(df) != len(single):
        raise RuntimeError("rate output does not match Table S3 single-hit rows")
    wt = df.loc[df["name"] == "synCRE_Promega_0"].iloc[0]
    wt_measured = float(wt["measured_expression"])
    wt_predicted = float(wt["predicted_expression"])
    df["measured_delta"] = np.log2(df["measured_expression"] / wt_measured)
    df["predicted_delta"] = np.log2(df["predicted_expression"] / wt_predicted)
    parsed = df["name"].map(parse_name)
    df["position"] = [p[0] if p else np.nan for p in parsed]
    df["mut_base"] = [p[1] if p else "" for p in parsed]
    df["is_mutant"] = df["position"].notna()
    return df


def parse_name(name: str) -> tuple[int, str] | None:
    match = MUT_RE.match(str(name))
    if not match:
        return None
    return int(match.group(1)), match.group(2)


def load_pssms() -> dict[str, list[list[float]]]:
    raw = pd.read_excel(TABLE_S2, header=None)
    pssms: dict[str, list[list[float]]] = {}
    for row_idx, row in raw.iterrows():
        tf = row.iloc[0]
        if not isinstance(tf, str) or tf not in TF_NAMES:
            continue
        bases = {}
        for offset, base in enumerate(BASE_ORDER):
            bases[base] = raw.iloc[row_idx + offset, 2:].dropna().astype(float).tolist()
        npos = len(bases["A"])
        pssms[tf] = [[bases["A"][i], bases["C"][i], bases["G"][i], bases["T"][i]] for i in range(npos)]
    return pssms


def text_center(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill=(25, 25, 25)) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text((xy[0] - (bbox[2] - bbox[0]) / 2, xy[1] - (bbox[3] - bbox[1]) / 2), text, font=font, fill=fill)


def draw_sequence_panel(base: Image.Image, draw: ImageDraw.ImageDraw, scanned_seq: str) -> None:
    draw.text((120, 60), "A", font=F_PANEL, fill=(0, 0, 0))
    x0, y0 = 210, 125
    char_w = 23
    draw.text((x0 - 70, y0), "5'-", font=F_SEQ, fill=(30, 30, 30))
    draw.text((x0 - 70, y0 + 36), "3'-", font=F_SEQ, fill=(30, 30, 30))
    draw.text((x0 + len(scanned_seq) * char_w + 4, y0), "-3'", font=F_SEQ, fill=(30, 30, 30))
    draw.text((x0 + len(scanned_seq) * char_w + 4, y0 + 36), "-5'", font=F_SEQ, fill=(30, 30, 30))
    for i, base_char in enumerate(scanned_seq):
        draw.text((x0 + i * char_w, y0), base_char, font=F_SEQ, fill=(30, 30, 30))
        draw.text((x0 + i * char_w, y0 + 36), complement(base_char), font=F_SEQ, fill=(30, 30, 30))
    for label, start, end, _, outline in REGIONS:
        sx = x0 + start * char_w - 3
        ex = x0 + (end + 1) * char_w + 2
        draw.rectangle((sx, y0 - 5, ex, y0 + 69), outline=outline, width=4)
        text_center(draw, ((sx + ex) // 2, y0 - 30), label, F_SEQ_LABEL)


def region_x_ranges(plot_x: int, plot_w: int) -> list[tuple[int, int, tuple[int, int, int, int]]]:
    out = []
    for _, start, end, fill, _ in REGIONS:
        sx = int(plot_x + start / 87 * plot_w)
        ex = int(plot_x + (end + 1) / 87 * plot_w)
        out.append((sx, ex, fill))
    return out


def draw_bar_panel(
    base: Image.Image,
    draw: ImageDraw.ImageDraw,
    df: pd.DataFrame,
    x: int,
    y: int,
    w: int,
    h: int,
    mut_base: str,
    value_col: str,
    bar_color: tuple[int, int, int],
    label_base: bool = True,
    show_metrics: bool = False,
) -> None:
    plot_left = x + 62
    plot_right = x + w - 12
    plot_top = y + 12
    plot_bottom = y + h - 36
    zero = int(plot_top + (2.2 / 4.4) * (plot_bottom - plot_top))
    plot_w = plot_right - plot_left

    overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
    od = ImageDraw.Draw(overlay)
    for sx, ex, fill in region_x_ranges(plot_left, plot_w):
        od.rectangle((sx, plot_top, ex, plot_bottom), fill=fill)
    base.alpha_composite(overlay)

    # Grid and axes.
    for val in [-2, -1, 0, 1, 2]:
        yy = map_y(val, plot_top, plot_bottom)
        draw.line((plot_left, yy, plot_right, yy), fill=(225, 225, 225), width=2)
        draw.text((x + 23, yy - 12), f"{val:g}", font=F_TINY, fill=(45, 45, 45))
    for tick in range(0, 90, 10):
        xx = int(plot_left + tick / 87 * plot_w)
        draw.line((xx, plot_top, xx, plot_bottom), fill=(235, 235, 235), width=1)
        if tick <= 80:
            draw.line((xx, plot_bottom, xx, plot_bottom + 10), fill=(45, 45, 45), width=2)
            text_center(draw, (xx, plot_bottom + 28), str(tick), F_TINY)
    draw.rectangle((plot_left, plot_top, plot_right, plot_bottom), outline=(45, 45, 45), width=3)
    draw.line((plot_left, zero, plot_right, zero), fill=(0, 0, 0), width=3)

    rows = df[(df["is_mutant"]) & (df["mut_base"] == mut_base)]
    bar_w = max(3, int(plot_w / 87 * 0.72))
    for _, row in rows.iterrows():
        pos = int(row["position"])
        val = float(row[value_col])
        xx = int(plot_left + (pos + 0.5) / 87 * plot_w)
        yy = map_y(val, plot_top, plot_bottom)
        if val >= 0:
            draw.rectangle((xx - bar_w // 2, yy, xx + bar_w // 2, zero), fill=bar_color)
        else:
            draw.rectangle((xx - bar_w // 2, zero, xx + bar_w // 2, yy), fill=bar_color)

    if label_base:
        draw.text((plot_left + 12, plot_top + 7), f"\u2192 {mut_base}", font=F_AXIS, fill=(0, 0, 0))
    if show_metrics:
        merged = df[(df["is_mutant"]) & (df["mut_base"] == mut_base)]
        r, rmse = corr_rmse(merged["measured_delta"].to_numpy(float), merged["predicted_delta"].to_numpy(float))
        txt = f"R= {r:.2f}   R$^2$= {r*r:.2f}   rmse= {rmse:.2f}"
        draw.text((plot_right - 515, plot_top + 10), txt.replace("$^2$", "2"), font=F_SMALL, fill=(0, 0, 0))


def map_y(val: float, top: int, bottom: int) -> int:
    val = max(-2.2, min(2.2, val))
    return int(bottom - (val + 2.2) / 4.4 * (bottom - top))


def corr_rmse(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    r = float(np.corrcoef(x, y)[0, 1])
    rmse = float(np.sqrt(np.mean((y - x) ** 2)))
    return r, rmse


def draw_bar_group(base: Image.Image, draw: ImageDraw.ImageDraw, df: pd.DataFrame) -> None:
    left_x, right_x = 210, 1460
    panel_w, panel_h, gap = 990, 245, 42
    top = 420
    draw.text((left_x + 335, top - 52), "Measured mRNA", font=F_AXIS, fill=(0, 0, 0))
    draw.text((right_x + 310, top - 52), f"7 CREB family model ({RUN})", font=F_AXIS, fill=(0, 0, 0))
    draw.text((110, top - 5), "B", font=F_PANEL, fill=(0, 0, 0))
    draw.text((1320, top + 365), "VS", font=F_AXIS, fill=(0, 0, 0))
    draw.text((1350, top - 5), "C", font=F_PANEL, fill=(0, 0, 0))
    for idx, mut_base in enumerate(BASE_ORDER):
        yy = top + idx * (panel_h + gap)
        draw_bar_panel(base, draw, df, left_x, yy, panel_w, panel_h, mut_base, "measured_delta", (0, 30, 255))
        draw_bar_panel(base, draw, df, right_x, yy, panel_w, panel_h, mut_base, "predicted_delta", (255, 28, 28), show_metrics=True)
    text_center(draw, (left_x + panel_w // 2, top + 4 * (panel_h + gap) - 5), "position", F_AXIS, fill=(70, 70, 70))
    text_center(draw, (right_x + panel_w // 2, top + 4 * (panel_h + gap) - 5), "position", F_AXIS, fill=(70, 70, 70))
    draw_vertical_label(base, "Delta activity(log2)", (100, top + 500), F_AXIS)


def draw_vertical_label(base: Image.Image, text: str, xy: tuple[int, int], font) -> None:
    temp = Image.new("RGBA", (420, 55), (255, 255, 255, 0))
    td = ImageDraw.Draw(temp)
    td.text((0, 0), text, font=font, fill=(0, 0, 0))
    rot = temp.rotate(270, expand=True)
    base.alpha_composite(rot, xy)


def pssm_to_logo_heights(vals: list[float], h: int) -> np.ndarray:
    arr = np.array(vals, dtype=float)
    # Table S2 stores PSSM-like scores, not probabilities. Softmax converts the
    # relative scores into a PWM-like distribution for visualization only.
    temp = 1.35
    z = (arr - arr.max()) / temp
    probs = np.exp(z)
    probs = probs / probs.sum()
    entropy = -float(np.sum(probs * np.log2(np.clip(probs, 1e-12, 1))))
    information = max(0.0, 2.0 - entropy)
    return probs * (information / 2.0) * h


def render_letter(base_char: str, width: int, height: int) -> Image.Image:
    width = max(3, width)
    height = max(3, height)
    temp = Image.new("RGBA", (130, 130), (255, 255, 255, 0))
    td = ImageDraw.Draw(temp)
    bbox = td.textbbox((0, 0), base_char, font=F_BASE)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    td.text(((130 - tw) / 2 - bbox[0], (130 - th) / 2 - bbox[1]), base_char, font=F_BASE, fill=BASE_COLORS[base_char] + (255,))
    alpha_bbox = temp.getbbox()
    if alpha_bbox:
        temp = temp.crop(alpha_bbox)
    return temp.resize((width, height), Image.Resampling.BICUBIC)


def draw_logo(base_img: Image.Image, draw: ImageDraw.ImageDraw, pssm: list[list[float]], x: int, y: int, w: int, h: int) -> None:
    draw.line((x, y + h, x + w, y + h), fill=(0, 0, 0), width=3)
    draw.line((x, y, x, y + h), fill=(0, 0, 0), width=3)
    n = len(pssm)
    col_w = w / n
    for i, vals in enumerate(pssm):
        heights = pssm_to_logo_heights(vals, h)
        order = np.argsort(heights)
        yy = y + h
        for idx in order:
            base_char = BASE_ORDER[idx]
            hh = int(round(heights[idx]))
            if hh < 7:
                continue
            letter = render_letter(base_char, max(5, int(col_w * 0.92)), hh)
            base_img.alpha_composite(letter, (int(x + i * col_w), int(yy - hh)))
            yy -= hh


def draw_logos(base_img: Image.Image, draw: ImageDraw.ImageDraw, pssms: dict[str, list[list[float]]]) -> None:
    x, y0 = 2630, 240
    draw.text((2550, 200), "D", font=F_PANEL, fill=(0, 0, 0))
    draw_vertical_text = False
    draw.text((2580, 925), "Bits", font=F_AXIS, fill=(0, 0, 0))
    for idx, tf in enumerate(TF_NAMES):
        y = y0 + idx * 205
        text_center(draw, (x + 155, y - 35), tf, F_SEQ_LABEL)
        draw_logo(base_img, draw, pssms[tf], x, y, 330, 135)


def make_figure() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = read_data()
    wt_seq = str(df.loc[df["name"] == "synCRE_Promega_0", "sequence"].iloc[0])
    scanned_seq = wt_seq[20:107]
    pssms = load_pssms()

    canvas = Image.new("RGBA", (3050, 2140), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    draw_sequence_panel(canvas, draw, scanned_seq)
    draw_bar_group(canvas, draw, df)
    draw_logos(canvas, draw, pssms)

    caption_y = 1905
    draw.text((110, caption_y), "Figure 2. A CRE enhancer and its mutational activities", font=get_font(27, True), fill=(160, 60, 60))
    caption = (
        "(A) Synthetic CRE enhancer sequence used for Kang 2024 Table S3. Red boxes indicate CRE sites and the blue box represents the cryptic region.\n"
        f"(B) MPRA single-hit experimental Delta activity. (C) {RUN} prediction from the modified Kim 2013/transcpp 7 ATF/CREB family model.\n"
        "(D) Motif-logo style summaries of Table S2 PWMs used in the 7TF model."
    )
    draw.multiline_text((110, caption_y + 42), caption, font=F_SMALL, fill=(0, 0, 0), spacing=10)

    out_png = OUTPUT_DIR / f"kang2024_{RUN}_figure2_reproduction.png"
    out_pdf = OUTPUT_DIR / f"kang2024_{RUN}_figure2_reproduction.pdf"
    rgb = canvas.convert("RGB")
    rgb.save(out_png)
    rgb.save(out_pdf, "PDF", resolution=300.0)
    print(f"wrote {out_png}")
    print(f"wrote {out_pdf}")


if __name__ == "__main__":
    make_figure()
