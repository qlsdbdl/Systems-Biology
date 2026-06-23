from __future__ import annotations

from itertools import combinations
from pathlib import Path
import csv
import sys
import xml.etree.ElementTree as ET

import pandas as pd

import build_kang2024_xml as kang


FAMILY_TFS = ["CREB1", "CREB3", "CREB5", "CREM", "ATF1", "ATF4", "ATF7"]
KEY_4TF = ["CREB1", "CREM", "ATF1", "ATF7"]
OUT_DIR = Path("outputs/figure3")


def set_mode_value(root: ET.Element, tag: str, value: str) -> None:
    node = root.find(f"./Mode/{tag}")
    if node is None:
        raise RuntimeError(f"missing Mode/{tag}")
    node.set("value", value)


def build_one_xml(family_tfs: list[str], self_competition: bool, output: Path) -> None:
    selected = ["TBP", *family_tfs]
    kang.TF_NAMES = selected
    pssms = kang.load_pssms()
    single_hit = pd.read_excel(kang.TABLE_S3, sheet_name="single-hit")
    root = ET.Element("Root")
    kang.add_mode(root)
    set_mode_value(root, "SelfCompetition", "true" if self_competition else "false")
    # Keep inter-TF competition enabled. Figure 3 varies self-competition, not
    # cross-TF competition.
    set_mode_value(root, "Competition", "true")
    kang.add_input(root, pssms, single_hit)
    kang.indent(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)


def combo_name(family_tfs: list[str]) -> str:
    return "-".join(family_tfs)


def iter_combos(pilot_only: bool) -> list[list[str]]:
    if pilot_only:
        return [["CREB1"], KEY_4TF, FAMILY_TFS]
    out: list[list[str]] = []
    for n in range(1, len(FAMILY_TFS) + 1):
        for combo in combinations(FAMILY_TFS, n):
            out.append(list(combo))
    return out


def write_runner_scripts(manifest_rows: list[dict[str, str]]) -> None:
    pilot_runs = [
        row
        for row in manifest_rows
        if row["family_tfs"] in {"CREB1", combo_name(KEY_4TF), combo_name(FAMILY_TFS)}
    ]

    pilot_script = OUT_DIR / "run_figure3_pilot.sh"
    with pilot_script.open("w") as fh:
        fh.write("#!/usr/bin/env bash\n")
        fh.write("set -euo pipefail\n")
        fh.write("cd /Users/iyubin/Documents/Codex/2026-06-05/pdf\n")
        fh.write("mkdir -p outputs/figure3/runs outputs/figure3/logs\n")
        fh.write("# Pilot set: CREB1-only, paper 4TF, and full 7TF; selfCompetition on/off.\n")
        for row in pilot_runs:
            base = f"{row['condition']}_n{int(row['n_tf']):02d}_{row['combo_id']}"
            template = row["template_xml"]
            run_xml = f"outputs/figure3/runs/{base}_seed00.xml"
            fh.write(f"cp {template} {run_xml}\n")
            fh.write(f"work/transcpp/transcpp {run_xml}\n")
            fh.write(f"work/transcpp/unfold -i {run_xml} -s Output --rate --invert > outputs/figure3/runs/{base}_seed00_rates.txt\n")
            fh.write(f"work/transcpp/unfold -i {run_xml} -s Output --score > outputs/figure3/runs/{base}_seed00_score.txt\n")

    full_script = OUT_DIR / "make_all_figure3_run_files.sh"
    with full_script.open("w") as fh:
        fh.write("#!/usr/bin/env bash\n")
        fh.write("set -euo pipefail\n")
        fh.write("cd /Users/iyubin/Documents/Codex/2026-06-05/pdf\n")
        fh.write("mkdir -p outputs/figure3/runs\n")
        fh.write("# This creates 8 run XMLs per TF-combination and condition.\n")
        fh.write("# It does not fit them. Fitting all files is computationally expensive.\n")
        for row in manifest_rows:
            base = f"{row['condition']}_n{int(row['n_tf']):02d}_{row['combo_id']}"
            template = row["template_xml"]
            fh.write(f"cp {template} outputs/figure3/runs/{base}_seed00.xml\n")
            for seed in range(1, 8):
                fh.write(
                    f"work/transcpp/scramble {template} "
                    f"outputs/figure3/runs/{base}_seed{seed:02d}.xml\n"
                )

    fit_script = OUT_DIR / "fit_completed_figure3_runs.sh"
    with fit_script.open("w") as fh:
        fh.write("#!/usr/bin/env bash\n")
        fh.write("set -euo pipefail\n")
        fh.write("cd /Users/iyubin/Documents/Codex/2026-06-05/pdf\n")
        fh.write("for f in outputs/figure3/runs/*.xml; do\n")
        fh.write("  if grep -q '<Output' \"$f\"; then\n")
        fh.write("    echo \"skip completed $f\"\n")
        fh.write("    continue\n")
        fh.write("  fi\n")
        fh.write("  work/transcpp/transcpp \"$f\"\n")
        fh.write("  work/transcpp/unfold -i \"$f\" -s Output --rate --invert > \"${f%.xml}_rates.txt\"\n")
        fh.write("  work/transcpp/unfold -i \"$f\" -s Output --score > \"${f%.xml}_score.txt\"\n")
        fh.write("done\n")

    for script in [pilot_script, full_script, fit_script]:
        script.chmod(0o755)


def main() -> None:
    pilot_only = "--pilot-only" in sys.argv
    combos = iter_combos(pilot_only)
    manifest_rows: list[dict[str, str]] = []
    for self_competition in [False, True]:
        condition = "self_on" if self_competition else "self_off"
        for idx, family_tfs in enumerate(combos, start=1):
            n_tf = len(family_tfs)
            combo_id = f"combo{idx:03d}_{combo_name(family_tfs)}"
            output = OUT_DIR / "templates" / condition / f"n{n_tf:02d}_{combo_id}.xml"
            build_one_xml(family_tfs, self_competition, output)
            manifest_rows.append(
                {
                    "condition": condition,
                    "self_competition": "true" if self_competition else "false",
                    "n_tf": str(n_tf),
                    "combo_id": combo_id,
                    "family_tfs": combo_name(family_tfs),
                    "template_xml": str(output),
                }
            )

    manifest = OUT_DIR / "figure3_xml_manifest.csv"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with manifest.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(manifest_rows[0].keys()))
        writer.writeheader()
        writer.writerows(manifest_rows)
    write_runner_scripts(manifest_rows)
    print(f"wrote {len(manifest_rows)} XML templates")
    print(f"manifest: {manifest}")
    print(f"pilot runner: {OUT_DIR / 'run_figure3_pilot.sh'}")


if __name__ == "__main__":
    main()
