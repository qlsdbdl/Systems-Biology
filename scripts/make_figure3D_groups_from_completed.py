from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path("/Users/iyubin/Documents/Codex/2026-06-05/pdf")
TABLE_S3 = Path("/Users/iyubin/Downloads/Table S3.xlsx")
RUN_DIR = ROOT / "outputs/figure3/runs"
OUTPUT_DIR = ROOT / "outputs/figure3"
LEGACY_OUTPUT_DIR = ROOT / "outputs"


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


F_PANEL = font(40, True)
F_TITLE = font(30)
F_LABEL = font(28)
F_TICK = font(22)
F_SMALL = font(20)
F_BOLD = font(22, True)

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


def draw_rotated(img: Image.Image, text: str, xy: tuple[int, int]) -> None:
    tmp = Image.new("RGBA", (360, 58), (255, 255, 255, 0))
    td = ImageDraw.Draw(tmp)
    td.text((0, 0), text, font=F_LABEL, fill=(25, 25, 25))
    img.alpha_composite(tmp.rotate(270, expand=True), xy)


def read_measured() -> pd.DataFrame:
    return pd.read_excel(TABLE_S3, sheet_name="single-hit").rename(columns={"expression level": "measured"})


def score_path_for(rates_path: Path) -> Path:
    return rates_path.with_name(rates_path.name.replace("_rates.txt", "_score.txt"))


def parse_total_score(path: Path) -> float:
    if not path.exists():
        return float("nan")
    score = pd.read_csv(path, sep=r"\s+", skiprows=1, names=["name", "score", "count"])
    total = score.loc[score["name"] == "Total", "score"]
    return float(total.iloc[0]) if len(total) else float("nan")


def pearson_from_rates(measured: pd.DataFrame, rates_path: Path) -> tuple[float, float]:
    rates = pd.read_csv(rates_path, sep=r"\s+").rename(columns={"id": "name", "HEK293_MPRA": "predicted"})
    df = measured.merge(rates, on="name")
    wt = df.loc[df["name"] == "synCRE_Promega_0"].iloc[0]
    use = df["name"] != "synCRE_Promega_0"
    x = np.log2(df.loc[use, "measured"].to_numpy(float) / float(wt["measured"]))
    y = np.log2(df.loc[use, "predicted"].to_numpy(float) / float(wt["predicted"]))
    return float(np.corrcoef(x, y)[0, 1]), float(np.sqrt(np.mean((y - x) ** 2)))


def collect_metrics() -> pd.DataFrame:
    measured = read_measured()
    rows: list[dict[str, object]] = []

    for rates_path in sorted(RUN_DIR.glob("self_on_n*_rates.txt")):
        match = re.search(r"self_on_n(\d{2})_(.+)_seed(\d+)_rates\.txt$", rates_path.name)
        if not match:
            continue
        n_tf = int(match.group(1))
        combo = match.group(2)
        seed = int(match.group(3))
        r, rmse = pearson_from_rates(measured, rates_path)
        rows.append(
            {
                "run": rates_path.name.replace("_rates.txt", ""),
                "n_tf": n_tf,
                "combo": combo,
                "seed": seed,
                "pearson_r": r,
                "rmse": rmse,
                "score": parse_total_score(score_path_for(rates_path)),
                "source": "figure3_run",
            }
        )

    # Existing long 7TF fits can populate only n=7. They are useful while
    # the representative 1TF-6TF runs are still missing.
    for rates_path in sorted(LEGACY_OUTPUT_DIR.glob("kang2024_fit_*_rates.txt")):
        match = re.search(r"kang2024_(fit_\d+)_rates\.txt$", rates_path.name)
        if not match:
            continue
        run = match.group(1)
        r, rmse = pearson_from_rates(measured, rates_path)
        rows.append(
            {
                "run": run,
                "n_tf": 7,
                "combo": "combo127_CREB1-CREB3-CREB5-CREM-ATF1-ATF4-ATF7",
                "seed": run.replace("fit_", ""),
                "pearson_r": r,
                "rmse": rmse,
                "score": parse_total_score(LEGACY_OUTPUT_DIR / f"kang2024_{run}_score.txt"),
                "source": "existing_7tf_fit",
            }
        )

    out = pd.DataFrame(rows).sort_values(["n_tf", "source", "run"])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_DIR / "figure3D_completed_group_metrics.csv", index=False)
    return out


def nice_axis(values: np.ndarray) -> tuple[float, float, float]:
    if len(values) == 0:
        return 0.0, 1.0, 0.2
    lo = max(-0.2, float(values.min()) - 0.08)
    hi = min(1.0, float(values.max()) + 0.08)
    if hi - lo < 0.2:
        mid = (hi + lo) / 2
        lo, hi = mid - 0.1, mid + 0.1
    step = 0.05 if hi - lo <= 0.35 else 0.1
    return lo, hi, step


def ymap(value: float, top: int, bottom: int, lo: float, hi: float) -> int:
    return int(bottom - (value - lo) / (hi - lo) * (bottom - top))


def draw_box_or_dot(
    draw: ImageDraw.ImageDraw,
    values: np.ndarray,
    cx: int,
    top: int,
    bottom: int,
    lo: float,
    hi: float,
    color: tuple[int, int, int],
) -> None:
    if len(values) >= 2:
        q1, med, q3 = np.percentile(values, [25, 50, 75])
        iqr = q3 - q1
        low = max(float(values.min()), q1 - 1.5 * iqr)
        high = min(float(values.max()), q3 + 1.5 * iqr)
        draw.line((cx, ymap(low, top, bottom, lo, hi), cx, ymap(high, top, bottom, lo, hi)), fill=color, width=4)
        draw.line((cx - 26, ymap(low, top, bottom, lo, hi), cx + 26, ymap(low, top, bottom, lo, hi)), fill=color, width=4)
        draw.line((cx - 26, ymap(high, top, bottom, lo, hi), cx + 26, ymap(high, top, bottom, lo, hi)), fill=color, width=4)
        draw.rectangle(
            (cx - 42, ymap(q3, top, bottom, lo, hi), cx + 42, ymap(q1, top, bottom, lo, hi)),
            fill=color + (190,),
            outline=color,
            width=3,
        )
        draw.line((cx - 42, ymap(med, top, bottom, lo, hi), cx + 42, ymap(med, top, bottom, lo, hi)), fill=(255, 255, 255), width=5)

    offsets = np.linspace(-36, 36, len(values)) if len(values) > 1 else np.array([0])
    for offset, value in zip(offsets, values):
        px = int(cx + offset)
        py = ymap(float(value), top, bottom, lo, hi)
        draw.ellipse((px - 6, py - 6, px + 6, py + 6), fill=(40, 40, 40))

    mean = float(values.mean())
    py = ymap(mean, top, bottom, lo, hi)
    draw.ellipse((cx - 8, py - 8, cx + 8, py + 8), fill=(0, 0, 0))


def plot(df: pd.DataFrame) -> None:
    values = df["pearson_r"].to_numpy(float)
    lo, hi, step = nice_axis(values)

    img = Image.new("RGBA", (1500, 1180), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    left, top, right, bottom = 220, 130, 1345, 850
    width = right - left

    draw.text((70, 58), "D", font=F_PANEL, fill=(0, 0, 0))
    draw.text((132, 62), "with self-competition: single-hit fitting", font=F_TITLE, fill=(0, 0, 0))

    draw.line((left, bottom, right, bottom), fill=(40, 40, 40), width=3)
    draw.line((left, top, left, bottom), fill=(40, 40, 40), width=3)

    tick_start = np.ceil(lo / step) * step
    for val in np.arange(tick_start, hi + step / 2, step):
        yy = ymap(float(val), top, bottom, lo, hi)
        draw.line((left, yy, right, yy), fill=(226, 226, 226), width=2)
        label = f"{val:.2f}" if step < 0.1 else f"{val:.1f}"
        draw.text((left - 82, yy - 13), label, font=F_TICK, fill=(80, 80, 80))

    x_pos = {n: int(left + (n - 0.5) / 7 * width) for n in range(1, 8)}
    present = set(df["n_tf"].astype(int))

    for n in range(1, 8):
        x = x_pos[n]
        draw.line((x, bottom, x, bottom + 12), fill=(45, 45, 45), width=3)
        center(draw, (x, bottom + 42), str(n), F_TICK, fill=(70, 70, 70) if n in present else (170, 170, 170))
        sub = df.loc[df["n_tf"] == n, "pearson_r"].to_numpy(float)
        if len(sub):
            draw_box_or_dot(draw, sub, x, top, bottom, lo, hi, COLORS[n])

    paper_ref = 0.88
    if lo <= paper_ref <= hi:
        yy = ymap(paper_ref, top, bottom, lo, hi)
        for sx in range(left, right, 32):
            draw.line((sx, yy, sx + 16, yy), fill=(75, 75, 75), width=3)
        draw.text((left + 18, yy + 12), "paper 7-family model reference R≈0.88", font=F_SMALL, fill=(75, 75, 75))

    center(draw, ((left + right) // 2, bottom + 84), "number of TFs", F_LABEL)
    draw_rotated(img, "Pearson's R", (78, top + 260))

    missing = [str(n) for n in range(1, 8) if n not in present]
    if missing:
        note = f"Missing n={', '.join(missing)} fit results. Run outputs/figure3/run_figure3D_representative_7groups.sh to fill one representative result per group."
    else:
        note = "All 1TF-7TF groups have at least one completed XML fit. Full paper reproduction needs all 7Cn combinations and repeated seeds."
    draw.text((left, 1002), note, font=F_SMALL, fill=(60, 60, 60))

    out_png = OUTPUT_DIR / "figure3D_groups_from_completed_fits.png"
    out_pdf = OUTPUT_DIR / "figure3D_groups_from_completed_fits.pdf"
    rgb = img.convert("RGB")
    rgb.save(out_png)
    rgb.save(out_pdf, "PDF", resolution=300.0)
    print(df.to_string(index=False))
    print(f"wrote {out_png}")
    print(f"wrote {out_pdf}")


def main() -> None:
    df = collect_metrics()
    if df.empty:
        raise SystemExit("No completed rate files found.")
    plot(df)


if __name__ == "__main__":
    main()
