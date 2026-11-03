"""Reference (oracle) solution for the binding-arm matched-pair task.

Reasoning encoded here:
  * The in vivo comparison must not be won "simply by binding harder", i.e. the two constructs must engage the
    receptor on cells equally. The cell titration is the only assay run under one identical protocol for both
    formats (same plates, 4 C / 30 min, anti-Fc detection that sees one Fc per molecule in either format).
  * The chip (SCK) data cannot arbitrate across formats: run_conditions split the protocol by format
    (120/600 s association, 1000/30 s dissociation, 30/15 uL/min, different concentration series), the receptor
    is immobilised so two-arm analytes give avidity-distorted apparent KDs, the weak one-arm binders are far
    below saturation at 500 nM, and the near-identical naive 1:1 KD of construct_11 vs construct_12 (S106/S109)
    only exists if S109's fast extra component is ignored. It is a decoy.
Method: background-subtract each run with its secondary-only control, drop low_event_count wells, fit a 4PL with
free Hill slope per construct (both runs and technical wells pooled), and pick the one-arm/two-arm pair with the
smallest EC50 ratio.
"""
from __future__ import annotations

import itertools
import json
import sys

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

DATA = "/workspace/data/binding_panel_raw.xlsx"
OUT = "/workspace/analysis_output.json"


def fit_4pl(x: np.ndarray, y: np.ndarray) -> dict:
    lx = np.log10(x)

    def model(p, lxx):
        bottom, top, lec50, hill = p
        return bottom + (top - bottom) / (1.0 + 10.0 ** (hill * (lec50 - lxx)))

    best = None
    for lec in np.linspace(lx.min() + 1, lx.max() - 1, 9):
        for hill in (0.7, 1.0, 1.4):
            p0 = [min(y.min(), 0.0), y.max(), lec, hill]
            try:
                r = least_squares(lambda p: model(p, lx) - y, p0,
                                  bounds=([-5e3, 0.0, lx.min() - 3, 0.2], [5e3, 1e6, lx.max() + 3, 5.0]))
            except Exception:  # noqa: BLE001
                continue
            if best is None or r.cost < best.cost:
                best = r
    bottom, top, lec50, hill = best.x
    return dict(bottom=bottom, top=top, ec50=10 ** lec50, hill=hill)


def main(path: str = DATA, out: str = OUT) -> list[str]:
    book = pd.read_excel(path, sheet_name=None)
    cell = book["cell_titration_raw"]
    manifest = book["sample_manifest"]
    arms = dict(zip(manifest.construct_id, manifest.n_target_binding_arms))

    bg = cell[cell.construct_id == "secondary_only_control"].groupby("run_id").mfi_gmean.mean()
    wells = cell[(cell.construct_id != "secondary_only_control") & cell.qc_flag.isna() & cell.mfi_gmean.notna()
                 & cell.conc_nM.notna()].copy()
    wells["signal"] = wells.mfi_gmean - wells.run_id.map(bg)

    ec50 = {}
    for cid, d in wells.groupby("construct_id"):
        f = fit_4pl(d.conc_nM.to_numpy(float), d.signal.to_numpy(float))
        ec50[cid] = f["ec50"]
        print(f"{cid}  arms={arms[cid]}  EC50={f['ec50']:9.3f} nM  Hill={f['hill']:.3f}  top={f['top']:.0f}")

    one = [c for c in ec50 if arms[c] == 1]
    two = [c for c in ec50 if arms[c] == 2]
    ranked = sorted(((abs(np.log(ec50[a] / ec50[b])), a, b) for a, b in itertools.product(one, two)))
    for d, a, b in ranked[:5]:
        print(f"  {a} / {b}: EC50 ratio {np.exp(d):.3f}")
    _, a, b = ranked[0]
    pair = [a, b]
    with open(out, "w") as fh:
        json.dump({"matched_pair": pair}, fh)
    print("matched_pair:", pair)
    return pair


if __name__ == "__main__":
    main(*sys.argv[1:])
