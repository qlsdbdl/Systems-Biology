from __future__ import annotations

from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pandas as pd


TABLE_S2 = Path("/Users/iyubin/Downloads/Table S2.xlsx")
TABLE_S3 = Path("/Users/iyubin/Downloads/Table S3.xlsx")
OUTPUT = Path("outputs/kang2024_singlehit_from_kim2013.xml")

TF_NAMES = ["TBP", "CREB1", "CREB3", "CREB5", "CREM", "ATF1", "ATF4", "ATF7"]


def param(parent: ET.Element, tag: str, value: float, low: float, high: float, anneal: bool, move: str | None = None) -> None:
    attrs = {
        "value": f"{value:.8g}",
        "lim_low": f"{low:.8g}",
        "lim_high": f"{high:.8g}",
        "anneal": "true" if anneal else "false",
    }
    if move:
        attrs["move"] = move
    ET.SubElement(parent, tag, attrs)


def clean_xml_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:-]", "_", str(name))
    if not re.match(r"^[A-Za-z_]", cleaned):
        cleaned = f"g_{cleaned}"
    return cleaned


def load_pssms() -> dict[str, list[list[float]]]:
    raw = pd.read_excel(TABLE_S2, header=None)
    pssms: dict[str, list[list[float]]] = {}
    for row_idx, row in raw.iterrows():
        tf = row.iloc[0]
        if not isinstance(tf, str) or tf not in TF_NAMES:
            continue
        bases = {}
        for offset, base in enumerate(["A", "C", "G", "T"]):
            values = raw.iloc[row_idx + offset, 2:].dropna().astype(float).tolist()
            bases[base] = values
        npos = len(bases["A"])
        pssms[tf] = [[bases["A"][i], bases["C"][i], bases["G"][i], bases["T"][i]] for i in range(npos)]
    return pssms


def max_score(pssm: list[list[float]]) -> float:
    return sum(max(position) for position in pssm)


def add_mode(root: ET.Element) -> None:
    ET.SubElement(root, "annealer_input", {"init_T": "100000", "lambda": "0.0001", "init_loop": "100000"})
    ET.SubElement(root, "move", {"interval": "100", "gain": "3"})
    ET.SubElement(root, "count_criterion", {"freeze_crit": "1", "freeze_cnt": "5"})
    ET.SubElement(root, "mix", {"interval": "100", "adaptcoef": "10"})
    ET.SubElement(root, "lam", {"tau": "100", "memLength_mean": ".200", "memLength_sd": "100", "criterion": "1", "freeze_cnt": "5"})

    mode = ET.SubElement(root, "Mode")
    entries = [
        ("Schedule", "0"),
        ("Verbose", "1"),
        ("Profiling", "false"),
        ("ScoreFunction", "sse"),
        ("PThresh", "0"),
        ("ScaleData", "false"),
        ("PerGene", "false"),
        ("PerNuc", "false"),
        ("MinData", "0"),
        ("Competition", "true"),
        ("NumThreads", "8"),
        ("SelfCompetition", "true"),
        ("Precision", "16"),
        ("Seed", "0"),
        ("GCcontent", "0.41"),
    ]
    for tag, value in entries:
        attrs = {"value": value}
        if tag == "ScaleData":
            attrs.update({"type": "area", "scale_to": "2000"})
        if tag == "Competition":
            attrs.update({"window": "500", "shift": "50"})
        ET.SubElement(mode, tag, attrs)


def add_input(root: ET.Element, pssms: dict[str, list[list[float]]], single_hit: pd.DataFrame) -> None:
    input_node = ET.SubElement(root, "Input")

    distances = ET.SubElement(input_node, "Distances")
    quench = ET.SubElement(distances, "Distance", {"name": "Quenching", "distfunc": "Trapezoid"})
    param(quench, "A", 100, 100, 100, False, "Quenching")
    param(quench, "B", 50, 50, 50, False, "Quenching")
    dist = ET.SubElement(distances, "Distance", {"name": "TFIIDCoact", "distfunc": "Trapezoid"})
    param(dist, "A", 200, 1, 200, False, "Coeffect")
    param(dist, "B", 10, 10, 200, False, "Coeffect")

    promoters = ET.SubElement(input_node, "Promoters")
    promoter = ET.SubElement(promoters, "Promoter", {"name": "basic", "function": "Arrhenius2"})
    param(promoter, "Q", 1, 1, 1, False, "Promoter")
    param(promoter, "Rmax", 200, 200, 400, False, "Promoter")
    param(promoter, "Theta", 10.66, 5, 20, True, "Promoter")

    tfs = ET.SubElement(input_node, "TFs")
    for tf_name, pssm in pssms.items():
        score = max_score(pssm)
        tf = ET.SubElement(tfs, "TF", {"name": tf_name, "bsize": str(len(pssm)), "include": "true"})
        param(tf, "kmax", 1, 0.000001, 4, True, "Kmax")
        param(tf, "threshold", 0.6 * score, 0, score, True, "Sites")
        param(tf, "lambda", 1, 0.5, 5, True, "Lambda")
        coefs = ET.SubElement(tf, "Coefficients")
        coef = 0 if tf_name == "TBP" else 1
        param(coefs, "coef", coef, 0.0001 if tf_name != "TBP" else 0, 20, tf_name != "TBP", "Promoter")
        pwm = ET.SubElement(tf, "PWM", {"type": "PSSM", "source": "Kang2024_TableS2"})
        ET.SubElement(pwm, "base").text = "A C G T"
        for position in pssm:
            ET.SubElement(pwm, "position").text = "; ".join(f"{x:.9g}" for x in position)

    ET.SubElement(input_node, "Interactions")

    genes = ET.SubElement(input_node, "Genes")
    source = ET.SubElement(genes, "Source", {"name": "Kang2024_TableS3_single_hit", "type": "local"})

    gene_names = []
    for _, row in single_hit.iterrows():
        gene_name = clean_xml_name(row["name"])
        gene_names.append(gene_name)
        ET.SubElement(
            source,
            "Gene",
            {
                "name": gene_name,
                "header": gene_name,
                "right_bound": "-1",
                "TSS": "-1",
                "promoter": "basic",
                "scale": "default",
                "anneal": "false",
                "sequence": str(row["sequence"]),
            },
        )

    scales = ET.SubElement(input_node, "ScaleFactors")
    scale = ET.SubElement(scales, "ScaleFactor", {"name": "default"})
    param(scale, "A", 1, 1, 1, False, "Null")
    param(scale, "B", 0, 0, 0, False, "Null")

    rate_data = ET.SubElement(input_node, "RateData", {"row": "ID", "col": "gene"})
    rate_row = ET.SubElement(rate_data, "TableRow", {"ID": "HEK293_MPRA"})
    for gene_name, expression in zip(gene_names, single_hit["expression level"]):
        rate_row.set(gene_name, f"{float(expression):.10g}")

    tf_data = ET.SubElement(input_node, "TFData", {"row": "ID", "col": "TF"})
    tf_row = ET.SubElement(tf_data, "TableRow", {"ID": "HEK293_MPRA"})
    for tf_name in TF_NAMES:
        tf_row.set(tf_name, "100")


def indent(elem: ET.Element, level: int = 0) -> None:
    space = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = space + "  "
        for child in elem:
            indent(child, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = space
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = space


def main() -> None:
    pssms = load_pssms()
    single_hit = pd.read_excel(TABLE_S3, sheet_name="single-hit")
    root = ET.Element("Root")
    add_mode(root)
    add_input(root, pssms, single_hit)
    indent(root)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(OUTPUT, encoding="utf-8", xml_declaration=True)
    print(f"wrote {OUTPUT} with {len(single_hit)} single-hit genes and {len(pssms)} TF PWMs")


if __name__ == "__main__":
    main()
