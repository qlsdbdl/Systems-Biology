from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path("/Users/iyubin/Documents/Codex/2026-06-05/pdf")
TABLE_S3 = Path("/Users/iyubin/Downloads/Table S3.xlsx")
RUN_DIR = ROOT / "outputs/figure3/runs"
TRANSC_UNFOLD = ROOT / "work/transcpp/unfold"

CONDITION = "self_off"
FORCE = False
PANEL = "C"
TITLE = "without self-competition: multi-hit prediction"
OUT_DIR = ROOT / "outputs/figure3/multihit/self_off"
XML_DIR = OUT_DIR / "xmls"
PRED_DIR = OUT_DIR / "predictions"
RATE_RE = re.compile("")

COLORS = {
    1: (149, 179, 224),
    2: (230, 126, 34),
    3: (76, 120, 168),
    4: (89, 161, 79),
    5: (72, 173, 213),
    6: (110, 122, 145),
    7: (92, 62, 150),
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


F_PANEL = font(34, True)
F_LABEL = font(28)
F_TICK = font(22)
F_SMALL = font(20)


def configure(condition: str, force: bool = False) -> None:
    global CONDITION, FORCE, PANEL, TITLE, OUT_DIR, XML_DIR, PRED_DIR, RATE_RE
    if condition not in {"self_off", "self_on"}:
        raise SystemExit("usage: make_figure3C_multihit_prediction.py [self_off|self_on] [--force]")
    CONDITION = condition
    FORCE = force
    PANEL = "C" if condition == "self_off" else "E"
    TITLE = (
        "without self-competition: multi-hit prediction"
        if condition == "self_off"
        else "with self-competition: multi-hit prediction"
    )
    OUT_DIR = ROOT / f"outputs/figure3/multihit/{condition}"
    XML_DIR = OUT_DIR / "xmls"
    PRED_DIR = OUT_DIR / "predictions"
    RATE_RE = re.compile(
        rf"{condition}_n(?P<n_tf>\d+)_(?P<combo_id>combo\d+_.+)_seed(?P<seed>\d+)\.xml$"
    )


def indent(elem: ET.Element, level: int = 0) -> None:
    space = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = space + "  "
        for child in elem:
            indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = space
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = space


def replace_child(parent: ET.Element, tag: str, new_child: ET.Element) -> None:
    for idx, child in enumerate(list(parent)):
        if child.tag == tag:
            parent.remove(child)
            parent.insert(idx, new_child)
            return
    parent.append(new_child)


def build_genes_table(multihit: pd.DataFrame, section_name: str) -> ET.Element:
    genes = ET.Element("Genes")
    source_attrs = {"name": "Kang2024_TableS3_multi_hit", "type": "local"}
    if section_name == "Output":
        source_attrs = {"name": "local", "file": "local", "type": "local"}
    source = ET.SubElement(genes, "Source", source_attrs)
    for _, row in multihit.iterrows():
        seq = str(row["sequence"])
        attrs = {
            "name": str(row["name"]),
            "header": str(row["name"]),
            "right_bound": "-1",
            "TSS": "-1",
            "promoter": "basic",
            "scale": "default",
            "anneal": "false",
            "sequence": seq,
        }
        if section_name == "Output":
            attrs.update({"left_bound": f"-{len(seq)}", "weight": "1", "include": "true"})
        ET.SubElement(source, "Gene", attrs)
    return genes


def build_rate_data(multihit: pd.DataFrame) -> ET.Element:
    rate_data = ET.Element("RateData", {"row": "ID", "col": "gene"})
    attrs = {"ID": "HEK293_MPRA"}
    for _, row in multihit.iterrows():
        attrs[str(row["name"])] = f"{float(row['expression level']):.12g}"
    ET.SubElement(rate_data, "TableRow", attrs)
    return rate_data


def get_output_nproportionality(root: ET.Element) -> str:
    nprop = root.find("./Output/Competition/NProportionality")
    if nprop is None:
        return "sum"
    value = nprop.attrib.get("value", "sum")
    return value if value in {"sum", "product"} else "sum"


def build_output_competition(nproportionality: str) -> ET.Element:
    competition = ET.Element("Competition")
    values = [
        ("Window", "500", "Window"),
        ("Shift", "50", "Promoter"),
        ("Specificity", "1", "Promoter"),
        ("Threshold", "0", "Promoter"),
        ("Background", "0", "Promoter"),
        ("S", "1", "Promoter"),
        ("InteractionStrength", "1", "Promoter"),
    ]
    for tag, value, move in values:
        ET.SubElement(
            competition,
            tag,
            {"value": value, "lim_low": "0", "lim_high": "0", "anneal": "false", "move": move},
        )
    ET.SubElement(competition, "NProportionality", {"value": nproportionality})
    return competition


def patch_xml_for_multihit(fit_xml: Path, out_xml: Path, multihit: pd.DataFrame) -> None:
    tree = ET.parse(fit_xml)
    root = tree.getroot()
    nproportionality = get_output_nproportionality(root)
    for section_name in ["Input", "Output"]:
        section = root.find(section_name)
        if section is None:
            continue
        if section_name == "Output":
            replace_child(section, "Competition", build_output_competition(nproportionality))
        replace_child(section, "Genes", build_genes_table(multihit, section_name))
        replace_child(section, "RateData", build_rate_data(multihit))
    indent(root)
    out_xml.parent.mkdir(parents=True, exist_ok=True)
    tree.write(out_xml, encoding="utf-8", xml_declaration=True)


def generate_prediction_xmls(multihit: pd.DataFrame) -> list[Path]:
    xmls: list[Path] = []
    for fit_xml in sorted(RUN_DIR.glob(f"{CONDITION}*_seed00.xml")):
        if not fit_xml.with_name(f"{fit_xml.stem}_rates.txt").exists():
            continue
        match = RATE_RE.match(fit_xml.name)
        if not match:
            continue
        out_xml = XML_DIR / f"{fit_xml.stem}_multihit.xml"
        patch_xml_for_multihit(fit_xml, out_xml, multihit)
        xmls.append(out_xml)
    return xmls


def run_unfold(xmls: list[Path]) -> None:
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    for xml in xmls:
        out = PRED_DIR / f"{xml.stem}_rates.txt"
        if not FORCE and out.exists() and out.stat().st_size > 0:
            continue
        with out.open("w") as fh:
            subprocess.run(
                [str(TRANSC_UNFOLD), "-i", str(xml), "-s", "Output", "--rate", "--invert"],
                cwd=ROOT,
                check=True,
                stdout=fh,
            )


def parse_predictions(multihit: pd.DataFrame) -> pd.DataFrame:
    measured = multihit.rename(columns={"expression level": "measured"}).copy()
    wt_name = "synCRE_Promega_0_WT"
    wt_measured = float(measured.loc[measured["name"] == wt_name, "measured"].iloc[0])
    measured["measured_delta"] = np.log2(measured["measured"].astype(float) / wt_measured)
    rows: list[dict[str, object]] = []
    for path in sorted(PRED_DIR.glob(f"{CONDITION}*_multihit_rates.txt")):
        base = path.name.replace("_multihit_rates.txt", ".xml")
        match = RATE_RE.match(base)
        if not match:
            continue
        rates = pd.read_csv(path, sep=r"\s+").rename(columns={"id": "name", "HEK293_MPRA": "predicted"})
        wt_pred = float(rates.loc[rates["name"] == wt_name, "predicted"].iloc[0])
        rates["predicted_delta"] = np.log2(rates["predicted"].astype(float) / wt_pred)
        df = measured.merge(rates[["name", "predicted_delta"]], on="name")
        mutants = df[df["name"] != wt_name].copy()
        mutants = mutants.replace([np.inf, -np.inf], np.nan).dropna(subset=["measured_delta", "predicted_delta"])
        x = mutants["measured_delta"].to_numpy(float)
        y = mutants["predicted_delta"].to_numpy(float)
        pearson_r = float(np.corrcoef(x, y)[0, 1])
        rmse = float(np.sqrt(np.mean((y - x) ** 2)))
        groups = match.groupdict()
        rows.append(
            {
                "condition": CONDITION,
                "prediction_dataset": "multi-hit",
                "n_tf": int(groups["n_tf"]),
                "combo_id": groups["combo_id"],
                "seed": int(groups["seed"]),
                "pearson_r": pearson_r,
                "r_squared": pearson_r * pearson_r,
                "rmse_delta_log2": rmse,
                "n_points": len(mutants),
                "rates_file": str(path),
            }
        )
    return pd.DataFrame(rows).sort_values(["n_tf", "combo_id", "seed"])


def ymap(value: float, top: int, bottom: int, lo: float = -0.35, hi: float = 1.05) -> int:
    return int(bottom - (value - lo) / (hi - lo) * (bottom - top))


def center(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fnt, fill=(40, 40, 40)) -> None:
    bbox = draw.textbbox((0, 0), text, font=fnt)
    draw.text((xy[0] - (bbox[2] - bbox[0]) / 2, xy[1] - (bbox[3] - bbox[1]) / 2), text, font=fnt, fill=fill)


def rotated_label(img: Image.Image, text: str, xy: tuple[int, int]) -> None:
    tmp = Image.new("RGBA", (350, 56), (255, 255, 255, 0))
    td = ImageDraw.Draw(tmp)
    td.text((0, 0), text, font=F_LABEL, fill=(30, 30, 30))
    img.alpha_composite(tmp.rotate(270, expand=True), xy)


def draw_boxplot(draw: ImageDraw.ImageDraw, values: np.ndarray, cx: int, top: int, bottom: int, color: tuple[int, int, int]) -> None:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) >= 2:
        q1, med, q3 = np.percentile(values, [25, 50, 75])
        iqr = q3 - q1
        low = max(float(values.min()), q1 - 1.5 * iqr)
        high = min(float(values.max()), q3 + 1.5 * iqr)
        box_w = 58
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
    rng = np.random.default_rng(3000 + cx + len(values))
    for value in values:
        px = int(cx + rng.uniform(-23, 23))
        py = ymap(float(value), top, bottom)
        draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=color)
    if len(values):
        mean_y = ymap(float(values.mean()), top, bottom)
        draw.ellipse((cx - 5, mean_y - 5, cx + 5, mean_y + 5), fill=(25, 25, 25))


def plot_figure3(results: pd.DataFrame) -> None:
    img = Image.new("RGBA", (900, 760), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    left, top, right, bottom = 170, 120, 820, 585
    draw.text((75, 48), PANEL, font=F_PANEL, fill=(0, 0, 0))
    draw.text((left, 60), TITLE, font=F_SMALL, fill=(35, 35, 35))
    draw.line((left, bottom, right, bottom), fill=(45, 45, 45), width=2)
    draw.line((left, top, left, bottom), fill=(45, 45, 45), width=2)
    for val in np.arange(-0.2, 1.01, 0.2):
        yy = ymap(float(val), top, bottom)
        draw.line((left, yy, right, yy), fill=(230, 230, 230), width=2)
        draw.text((left - 65, yy - 12), f"{val:.1f}", font=F_TICK, fill=(85, 85, 85))
    width = right - left
    for n in range(1, 8):
        cx = int(left + (n - 0.5) / 7 * width)
        draw.line((cx, bottom, cx, bottom + 10), fill=(45, 45, 45), width=2)
        center(draw, (cx, bottom + 38), str(n), F_TICK)
        values = results.loc[results["n_tf"] == n, "pearson_r"].to_numpy(float)
        if len(values):
            draw_boxplot(draw, values, cx, top, bottom, COLORS[n])
    center(draw, ((left + right) // 2, bottom + 88), "number of TFs", F_LABEL)
    rotated_label(img, "Pearson's R", (left - 120, top + 105))
    out_png = OUT_DIR / f"figure3{PANEL}_multihit_prediction_{CONDITION}.png"
    out_pdf = OUT_DIR / f"figure3{PANEL}_multihit_prediction_{CONDITION}.pdf"
    rgb = img.convert("RGB")
    rgb.save(out_png)
    rgb.save(out_pdf, "PDF", resolution=300.0)
    print(f"wrote {out_png}")
    print(f"wrote {out_pdf}")


def main() -> None:
    args = sys.argv[1:]
    force = "--force" in args
    args = [arg for arg in args if arg != "--force"]
    configure(args[0] if args else "self_off", force=force)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    XML_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    multihit = pd.read_excel(TABLE_S3, sheet_name="multi-hit")
    xmls = generate_prediction_xmls(multihit)
    if len(xmls) != 127:
        print(f"warning: expected 127 {CONDITION} XMLs, found {len(xmls)}")
    run_unfold(xmls)
    results = parse_predictions(multihit)
    if results.empty:
        raise SystemExit("no multi-hit predictions were produced")
    result_path = OUT_DIR / f"figure3{PANEL}_multihit_prediction_metrics.csv"
    results.to_csv(result_path, index=False)
    summary = (
        results.groupby("n_tf")
        .agg(
            n_runs=("pearson_r", "size"),
            mean_r=("pearson_r", "mean"),
            median_r=("pearson_r", "median"),
            max_r=("pearson_r", "max"),
            min_r=("pearson_r", "min"),
        )
        .reset_index()
    )
    summary_path = OUT_DIR / f"figure3{PANEL}_multihit_prediction_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(summary.to_string(index=False))
    print(f"wrote {result_path}")
    print(f"wrote {summary_path}")
    plot_figure3(results)


if __name__ == "__main__":
    main()
