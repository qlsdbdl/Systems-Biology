from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path("/Users/iyubin/Documents/Codex/2026-06-05/pdf")
FIG3 = ROOT / "outputs" / "figure3"


def has_output(path: Path) -> bool:
    try:
        return "<Output" in path.read_text(errors="ignore")
    except UnicodeDecodeError:
        return False


def is_locked(path: Path) -> bool:
    return (FIG3 / "locks" / f"{path.stem}.lock").exists()


def patch_thresholds(path: Path) -> bool:
    tree = ET.parse(path)
    root = tree.getroot()
    changed = False
    for tf in root.findall(".//TF"):
        if tf.get("name") == "TBP":
            continue
        threshold = tf.find("threshold")
        if threshold is not None and threshold.get("value") != "0":
            threshold.set("value", "0")
            changed = True
    if changed:
        tree.write(path, encoding="utf-8", xml_declaration=True)
    return changed


def main() -> None:
    changed = 0
    skipped_locked = 0
    skipped_completed = 0

    targets = list((FIG3 / "templates").glob("*/*.xml"))
    targets.extend((FIG3 / "runs").glob("*_seed*.xml"))

    for path in sorted(targets):
        if path.parent.name == "runs" and is_locked(path):
            skipped_locked += 1
            continue
        if path.parent.name == "runs" and has_output(path):
            skipped_completed += 1
            continue
        if patch_thresholds(path):
            changed += 1

    print(f"patched XMLs: {changed}")
    print(f"skipped locked active runs: {skipped_locked}")
    print(f"skipped completed runs: {skipped_completed}")


if __name__ == "__main__":
    main()
