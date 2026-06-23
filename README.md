# Kang 2024 CRE enhancer reproduction

This repository contains the files used to reproduce selected figures from:

**Kang and Kim, 2024. Deep molecular learning of transcriptional control of a synthetic CRE enhancer and its variants. iScience.**

The main goal was to reproduce Figure 2 and Figure 3 using the `transcpp` thermodynamic modeling pipeline.  
We used `kim2013.xml` as a transcpp-compatible template, but replaced its biological input with Kang 2024 data.

## Folder structure

```text
data/
  raw/                         # Put Table S2.xlsx and Table S3.xlsx here if redistributing data is allowed
  README.md                    # Data source and expected files

external_tools/
  README_transcpp.md           # How transcpp was used

inputs/
  xml/
    kang2024_template.xml
    kang2024_singlehit_from_kim2013.xml
    kang2024_fit_02.xml

scripts/
  build_kang2024_xml.py
  make_kang2024_figure2_like.py
  build_figure3_xmls.py
  collect_figure3_results.py
  make_figure3A_reduced_family_only.py
  make_figure3BD_from_completed.py
  make_figure3C_multihit_prediction.py
  make_figure3D_groups_from_completed.py
  patch_figure3_threshold_init.py

run_scripts/
  fit_one_figure3_xml.sh
  run_full_figure3_queue.sh
  status_full_figure3_queue.sh
  run_seed00_parallel_queue.sh
  aws_fit_one_xml.sh
  aws_run_queue.sh
  aws_status.sh
  merge_aws_figure3d_results.sh

results/
  figure2/                     # Reproduced Figure 2 image/PDF
  figure3/                     # Reproduced Figure 3 panels
  metrics/                     # Pearson's R and summary CSV files
```

## Data used

The reproduction used:

- **Table S2**: TF PWM/PSSM motif data
- **Table S3**: enhancer variant sequences and MPRA expression values
- **kim2013.xml**: used only as the XML model template

Table S2 and S3 should be placed in `data/raw/` if another user wants to run the scripts again.

Expected files:

```text
data/raw/Table S2.xlsx
data/raw/Table S3.xlsx
```

Some scripts currently contain local absolute paths from the original laptop environment.  
Before rerunning, update `TABLE_S2`, `TABLE_S3`, and `ROOT` paths in the scripts.

## Figure 2 reproduction

Figure 2 compares measured single-hit mutation effects with the fitted 7 ATF/CREB family model.

Main script:

```bash
python scripts/make_kang2024_figure2_like.py fit_02
```

Main output:

```text
results/figure2/kang2024_fit_02_figure2_reproduction.png
```

The fitted XML used for this figure is:

```text
inputs/xml/kang2024_fit_02.xml
```

## Figure 3 reproduction

Figure 3 tests which TF combinations and self-competition settings improve model performance.

The 7 ATF/CREB family TFs were:

```text
CREB1, CREB3, CREB5, CREM, ATF1, ATF4, ATF7
```

All non-empty combinations were generated:

```text
7C1 + 7C2 + 7C3 + 7C4 + 7C5 + 7C6 + 7C7 = 127 combinations
```

Each combination was tested with:

```text
SelfCompetition = false
SelfCompetition = true
```

So the full Figure 3 design had 254 model settings.

Important outputs:

```text
results/figure3/figure3A_reduced_family_only.png
results/figure3/figure3B_reproduced_crop.png
results/figure3/figure3C_multihit_prediction_self_off.png
results/figure3/figure3D_groups_from_completed_fits.png
results/figure3/figure3E_multihit_prediction_self_on.png
results/figure3/figure3BD_singlehit_from_completed.png
```

## Notes on reproduction limits

- Figure 3A was reproduced as a reduced family-only version.
- Non-family TFs were not included because this reproduction used the ATF/CREB family PWM inputs prepared from Table S2.
- Self-competition ON fitting was computationally harder and less stable in our runs.
- Full repeated seed training from the paper was computationally expensive, so this repository mainly documents the reproducible workflow and completed representative runs.

## Python requirements

The scripts mainly use:

```text
pandas
numpy
pillow
matplotlib
openpyxl
```

Install with:

```bash
pip install -r requirements.txt
```

