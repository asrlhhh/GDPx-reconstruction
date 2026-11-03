# Reconstruction notes: `latchbio/binding-arm-matched-pair`

This Harbor task was rebuilt from 12 agent rollouts in `latch-bio/` (claude-opus-5-5, gemini-4-argon,
glm-5-3 and gpt-6-astra, three runs each, four different harnesses). No original task files were available.
Every statement below is backed by trace evidence. The tooling and intermediate evidence live in
`../../recon_work/` (see "Tooling" at the end).

```
binding-arm-matched-pair/
├── instruction.md            verbatim agent prompt (byte-identical in the 9 non-Gemini rollouts)
├── task.toml                 Harbor config (6 CPU / 64 GiB / 6 h agent budget / no network)
├── environment/
│   ├── Dockerfile            faithful rebuild of the task image (validated on Modal)
│   ├── pyproject.toml        verbatim /root/pyproject.toml (1,565 B, md5 6429be1a…)
│   ├── known-versions.txt    85 package versions printed by the rollouts (used as lock constraints)
│   ├── dotfiles/             /root/.bash_profile (42 B) and a placeholder /root/.bashrc (84 B)
│   └── data/binding_panel_raw.xlsx   reconstructed workbook
├── solution/solve.sh, solve.py   oracle: cell-titration 4PL -> construct_05 + construct_10
└── tests/test.sh, test_outputs.py    order-insensitive check of matched_pair, writes /logs/verifier/reward.txt
```

## 1. Instruction
`instruction.md` is the first user turn of the rollouts, copied byte-for-byte: 2,691 B, identical in all 9
non-Gemini rollouts. The Gemini harness only wraps the same text in `<USER_REQUEST>` tags. The flattened copy in
`latch-bio/instruction.md` had lost its markdown (code fence, backticks, numbered list). The preamble
("You have 6 hours … 6 CPUs, 64 GiB …") and the IMPORTANT/completion-signal postamble appear to be a benchmark
template wrapped around the task text. They are kept because they are what the agents saw.

## 2. Data: `environment/data/binding_panel_raw.xlsx`

| sheet | rows | status |
|---|---|---|
| `sample_manifest` | 12 | **exact** (printed in full by many runs) |
| `run_conditions` | 13 | **exact** (all values are strings, as in the original) |
| `cell_titration_raw` | 780 | **exact to ±0.5 AFU**, see 2.1 |
| `chip_sensorgrams` | 31,402 | **structure exact, values reconstructed** (anchored and conditioned simulation), see 2.2 |

**Container.** Written the way the original was written: `pandas.DataFrame.to_excel(engine="openpyxl", index=False)`
with openpyxl 3.1.5. That means inline strings and no sharedStrings part, NaN written as empty inline-string cells,
the bold/bordered pandas header style, and 16-significant-digit float text (this is why the original XML shows
`96.59999999999999` and `557.3099999999999`). docProps creator is `openpyxl`, created 2026-08-12T23:42:59Z and
modified 23:43:01Z; the file mtime is set to epoch 0. Size: 1,386,757 B vs 1,387,104 B in the original (99.97 %).

### 2.1 Cell titration (essentially recovered)
* All 768 construct wells were printed as an integer-rounded pivot (claude-opus-5-5-3 #44). 184 rows were printed
  exactly with all columns, including the 12 secondary-only controls and the 8 `low_event_count` wells. Cross-check:
  0 mismatches between the two sources.
* The 184 exact rows keep their original sheet positions (pandas indices and openpyxl tuple order; 0 conflicts).
  The other 596 rows are shuffled with a fixed seed.
* The unknown parts are the 2-decimal fractions of 596 MFIs and 596 `cells_acquired` values. They were *solved*
  (`stat_solver.py`) so that every printed `describe()` reproduces to all printed digits:
  * MFI: mean 5841.188303, sd 6765.964716, quartiles 554.7525 / 1429.785 / 11212.5825, min/max;
  * `cells_acquired`: all 780 rows and the 772 unflagged rows, mean/sd/quartiles/min/max.
* Check: claude-opus-5-5-1's per-run 4PL table reproduces to within 0.02 % in EC50 (construct_01 exactly). Replaying
  that agent's entire cell pipeline on Modal reproduces 94-100 % of its printed numbers per command.

### 2.2 Chip sensorgrams (reconstructed)
Only about 3 % of the rows were ever printed verbatim, but more than 22,000 linear statistics of the data were
printed. These include phase means, first/last-k means, plateaus, double-referenced points, dissociation time
courses, baseline/post levels and reference shifts. The sheet is a calibrated simulation conditioned on all of them:
* **Exact structure**: 28 cycles. Series A = cycles 1-14, B = 15-28. Per series: one-arm S105, S111, S106, S103,
  S104, S101; two-arm S112, S109, S110, S102, S108, S107; then a one-arm-protocol blank and a two-arm-protocol blank.
  Time grids are 704/1,539 rows with 5 s / 1 s / 2 s / 5 s sampling, as in run_conditions. Phase labels and
  `step_conc_nM` are as printed (blanks have 0 nM in every row; verified by the printed describe() mean
  117.175976).
* **Generator** (`recon_work/tools/build_chip_v2.py` model, final sheet built by `build_chip_v3.py`; model from the chip synthesis):
  * binding = sum of independent 1:1 pools, integrated per sampling interval with the *previous* row's
    concentration (the "binding lags one sample, bulk does not" fingerprint);
  * bulk RI step on both channels: 0.0200 RU/nM (one-arm) and 0.0594 (two-arm, active gain 1.025);
  * common-mode Ornstein-Uhlenbeck wander (sd ~1.05 RU, ~360 s) plus active-only drift, both fitted on the blank
    cycles' targets;
  * heteroscedastic white noise: 0.31 RU plus 0.55 % (1 Hz) or 0.45 % (0.5 Hz) of the bound response on the
    active channel, plus 1 % of the bulk on the reference channel;
  * sparse 1.5-3.5 RU spikes on 0.4 % of the unanchored rows of sample cycles (none in blanks);
  * 5-dp rounding;
  * two pools for every two-arm sample except S107. S112 has a slow ~2.9 nM pool plus a ~165 nM pool. S109 has a
    ~62 nM main pool plus a fast, weak pool (≈0.055 RU/nM at 500 nM). S110, S102 and S108 have smaller fast pools.
* **Conditioning**: each cycle is a Matheron-rule draw from the Gaussian process conditioned on its linear targets.
  Blank-referenced (double-referenced) targets use the already-built blank, with their tolerance widened for
  unanchored blank points. 997+ exact 5-dp anchor values are written verbatim.
* **Extrema**: gemini-4-argon-1 #21 printed every cycle's exact max/min per channel. Overshooting rows are pulled
  inside, and the extremum is pinned on a row that the targets leave free (posterior sd > 0.25 RU). Both are done
  as extra GP constraints, so every other target still holds.
* **Calibration**: the main pool of each cycle is tuned (common random numbers) until claude-opus-5-5-1's exact
  1:1 SCK recipe (#75) returns the printed ka/kd/KD/Rmax. Degenerate weak series-B fits that hit the Rmax bound in
  the original were not tuned; they reproduce as degenerate.
* **Invariants preserved** (checked):
  * one-arm KD ≈ 45 / 67.5 / 88.5 nM (≈ 4.5 × cell EC50);
  * the S106/S109 naive 1:1 tie (88.0/88.9 vs 88.3/90.3 nM; the planted decoy);
  * S109 main site 62-69 nM once the fast pool is modelled;
  * S112 residue ≈ 94/60 RU with no carry-over;
  * weak one-arm Req500 20-34 RU, unidentifiable in series B;
  * two-arm blank drift ≈ -2.5 RU;
  * global describe(): exact `step_conc_nM` and `time_s` means; response min/max exact; means 40.4465 / 5.9959
    vs 40.44666 / 5.995948; sd 54.598 / 9.434 vs 54.598 / 9.436; nunique 31,277 / 30,995 vs 31,279 / 31,022;
  * every cycle's printed extremum (gemini-4-argon-1 #21) reproduced except cycle_004's minimum;
  * 98.7 % of 13,676 de-duplicated printed linear statistics satisfied to their printed precision;
  * claude-opus-5-5-1's per-cycle 1:1 KDs reproduced with median deviation 0.03 % (max 0.5 %).

## 3. Environment (`environment/Dockerfile`)
* **Base**: `python:3.12.14-bookworm` (full image).
  * *bookworm*, not trixie: the original `/root/.profile` is 161 B dated 2019-07-09, which is bookworm's stock file
    (trixie's is 132 B, checked on Modal).
  * The system interpreter has only pip 25.0.1, so `import numpy` fails outside the venv, exactly as every rollout
    found.
* **Node.js v26.3.1**: the node binary is 147,420,912 B with build time 2026-06-17 17:39, identical to the original
  listing. npm/npx are absolute symlinks; there is no corepack or yarn.
* **Analysis venv**: `/root/.venv` from `uv sync` of the virtual project at `/root`.
  * The original `uv.lock` (925,103 B) was not recoverable. It is re-resolved with
    `--exclude-newer 2026-07-24T01:58Z` (the original lock's mtime) under constraints for the 85 package versions
    printed by the rollouts.
  * The constraints go into a temporary pyproject; `/root/pyproject.toml` stays byte-identical.
  * Result: all 58 packages in the original `pip list` head match exactly (numpy 1.26.4, pandas 2.3.3,
    scipy 1.16.3, openpyxl 3.1.5, …).
  * `r-base-dev` is installed because rpy2's API-mode extension (present in the original venv) needs R at build
    time; `libgeos-dev` for pygeos.
* **Unknown and approximated**:
  * the content of the 84-B `/root/.bashrc`: a placeholder of the same size; the original did not put the venv on
    PATH;
  * versions of packages never printed;
  * the exact digest of the 2026-09-01 python image build.
  * Harness-specific paths (`/opt/harness`, `/logs/agent`, `rg`) are not part of the task image.

## 4. Answer key: `construct_05` + `construct_10` (order-insensitive)
The rollouts disagree. Their answers were 05/10 (4 runs), 02/09 (2), 11/12 (2), 11/09 (2), 07/12 (1) and 04/12 (1).
The dataset contains **two planted near-identities**:
* **cell EC50, construct_05 vs construct_10** (one-arm vs two-arm): about 380 vs 376 nM, within 1-3 % under every
  free-Hill 4PL.
* **naive chip 1:1 KD, construct_11 vs construct_12**: 88 vs 89 nM.

The key follows the cell assay. Reasons:
1. The prompt asks that "neither construct wins simply by binding harder" in an in vivo test of receptor
   engagement. The cell titration is the only assay run under one identical protocol for both formats: same
   plates, 4 °C, anti-Fc detection of one Fc per molecule.
2. `run_conditions` split the chip protocol by format: 120/600 s association, 1000/30 s dissociation,
   30/15 µL/min, and different concentration series. The receptor is immobilised, so two-arm analytes give
   avidity-distorted apparent KDs.
3. The 11/12 chip match exists only if S109's fast component is ignored, and that component scales with two-arm
   potency (c03 > c12 > c09 > c08 > c01 ≈ c10). It is a generic format-linked feature, so the chip KDs of two-arm
   constructs are not on the one-arm scale. The weak one-arm constructs cannot be measured on the chip at all.
4. On cells, construct_12 binds ~11× tighter than construct_11, which is exactly the outcome the prompt excludes.
5. The cell sheet carries decoys that only make sense if it is the arbiter:
   * Top tiers make 02/09 look visually perfect;
   * construct_05's shallow Hill (0.94) makes Hill-fixed or interpolation estimators land on 05/01;
   * c05 and c10 carry no low-event-count wells, while every rival construct does.

A five-judge adversarial panel came out unanimously for 05/10, with overall confidence ≈ 0.5. The judges' lenses
were generator forensics, in vivo pharmacology, SPR biophysics, a devil's advocate for the chip reading, and
within-cell robustness. Main alternative: the intrinsic-affinity reading 11/12 (≈ 0.2). Within-cell alternative:
05/01 (≈ 0.08), which only wins if Hill is fixed at 1. The oracle uses the standard free-Hill 4PL: 05/10 at an EC50
ratio of 1.03, next 05/01 at 1.06. **If you have reason to believe the original grader keyed the chip reading,
change `EXPECTED_PAIR` in `tests/test_outputs.py` to {construct_11, construct_12}.**

## 5. Validation (on Modal, profile `hs-research-team`, environment `relay-external-engagement`)
* The image builds from `environment/Dockerfile`. Smoke tests reproduce the original layout: bookworm, Python
  3.12.14, pip-only system site-packages, Node 26.3.1, venv not on PATH, `/workspace/data` file with mode 0644 and
  mtime 1970, `/root` listing incl. `.cache/` and `.config/` with matplotlib.
* Harbor flow in the built image (`recon_work/tools/modal_validate_task.py`):
  * `solution/` is uploaded to `/solution` and `solve.sh` run, then `tests/` is uploaded to `/tests` and `test.sh`
    run. The oracle writes `{"matched_pair": ["construct_05", "construct_10"]}` and pytest passes (2 tests), so
    **reward = 1**.
  * Negative controls: the chip decoy 11/12 gives 0, the near-miss 05/01 gives 0, a malformed value gives 0, and the
    reversed order 10/05 gives 1 (order-insensitive).
* **Replay of all 12 rollouts** (`recon_work/tools/modal_replay.py`). Every bash/exec command, file write, edit and
  codex patch from each trace was re-executed in order, inside the rebuilt image, against the rebuilt workbook. The
  table shows the share of the original's printed numbers reproduced within 2 % (or 0.05 absolute), split by the
  sheet the command touched (`analyze_replay.py`):

  | run | cell-assay numbers | chip numbers | all numbers |
  |---|---|---|---|
  | claude-opus-5-5-1 | 99.7 % of 2,244 | 97.0 % of 1,821 | 90.8 % |
  | claude-opus-5-5-2 | 100.0 % of 917 | 56.2 % of 3,105 (multistart bivalent / mass-transport fits) | 73.5 % |
  | claude-opus-5-5-3 | 99.5 % of 1,726 | 83.1 % of 5,403 | 78.8 % |
  | gemini-4-argon-1 | 99.9 % of 1,552 | 93.4 % of 23,021 | 94.2 % |
  | gemini-4-argon-2 | 99.7 % of 1,000 | 92.2 % of 17,775 | 80.6 % |
  | gemini-4-argon-3 | 99.7 % of 894 | 87.0 % of 13,321 | 88.1 % |
  | glm-5-3-1 | 100.0 % of 572 | 86.1 % of 3,614 | 87.8 % |
  | glm-5-3-2 | 100.0 % of 1,037 | 88.4 % of 1,337 | 78.3 % (polls of background jobs cannot replay) |
  | glm-5-3-3 | 100.0 % of 450 | 96.9 % of 1,306 | 94.8 % |
  | gpt-6-astra-1 | (none) | 82.8 % of 751 | 89.8 % |
  | gpt-6-astra-2 | 100.0 % of 84 | 99.8 % of 2,804 | 93.8 % |
  | gpt-6-astra-3 | (none) | 93.5 % of 2,892 | 94.1 % |

  "All numbers" includes environment listings, timings and harness-only files, which cannot match.

* **The decision-driving outputs reproduce**, so every trap still leads to the same wrong (or right) answer:
  * glm-5-3-3's summary table gives S106/S109 geometric-mean chip KD 88.43 / 89.29 nM (original 88.45 / 89.29),
    i.e. the 11/12 decoy;
  * gpt-6-astra-1's minimax ranking is still headed by 11/09 in every window variant, with the same runners-up;
  * gemini-4-argon-1's 1:1 + α fit gives construct_12 62.5 / 69.7 nM with α 0.053 / 0.034 (original 62.6 / 70.5,
    0.054 / 0.034) against construct_07 65.3 / 61.4, i.e. the 07/12 path;
  * all cell-assay EC50 rankings are unchanged: 05/10 < 05/01 < 02/09.

## Tooling (`recon_work/tools/`)
| file | purpose |
|---|---|
| `trace_lib.py` | parser for the normalized trace JSONL (all four harness formats) |
| `extract_rows.py`, `extract_positions.py`, `extract_chip_tables.py`, `parse_cell_pivot.py` | harvest exact rows, sheet positions and printed tables |
| `stat_solver.py`, `build_cell.py` | titration sheet with exact describe() reproduction |
| `chip_sim.py`, `gp_chip.py`, `chip_fit.py`, `chip_targets*.py`, `targets_*.py`, `calibrate_chip.py`, `build_chip_v2.py` | sensorgram generator, GP conditioning, more than 22k parsed linear targets, calibration |
| `write_workbook.py` | pandas/openpyxl writer with the original's fingerprints |
| `replay_actions.py`, `modal_env.py`, `modal_replay.py` | replay each rollout's commands in a Modal sandbox and score numeric agreement |
