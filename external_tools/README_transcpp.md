# transcpp

This reproduction used `transcpp` from Kenneth A. Barr's GitHub repository:

```text
https://github.com/kennethabarr
```

The original `transcpp` source code and compiled binaries were not copied into this clean GitHub upload folder because they are external dependencies and include many build files.

In the original local workflow, the main commands were:

```bash
work/transcpp/transcpp outputs/kang2024_singlehit_from_kim2013.xml
work/transcpp/unfold -i outputs/kang2024_fit_02.xml -s Output --rate --invert > outputs/kang2024_fit_02_rates.txt
```

For Figure 3, many XML files were generated and fitted with `transcpp`, then summarized using the Python scripts in `scripts/`.

