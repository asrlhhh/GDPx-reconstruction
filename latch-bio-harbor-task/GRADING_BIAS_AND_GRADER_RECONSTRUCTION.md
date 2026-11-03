# Grading-bias audit and grader-reconstruction requirements
Task: LatchBio "binding-arm matched pair" (reconstructed as `binding-arm-matched-pair/`).
Evidence: 12 rollouts in `latch-bio/` (claude-opus-5-5, gemini-4-argon, glm-5-3, gpt-6-astra; 3 runs each), plus the
reconstruction artefacts in `recon_work/`. Trace citations are `run #idx`, where `#idx` is the event index in the
normalized trace; any of them can be printed with `recon_work/tools/trace_lib.py`.

## Executive summary
* **The traces contain no rewards and no grader output.** Every session ends with `termination_reason = submitted`.
  Everything below is therefore conditional on the answer key and grader rules, which we do not have.
* **No output-mechanics difference separates the 12 runs.** All wrote `/workspace/analysis_output.json` containing only
  `matched_pair` with two valid, distinct IDs (verified by read-back for 9 runs, from the writing code for 3). All
  listed the one-arm construct first, issued the completion signal, and finished in 6.7-128 min of the 6-h budget.
  * A format or order rule therefore treats all 12 runs identically. It could zero everyone (two-arm-first ordering,
    a strict canonical format), but it cannot reorder them.
  * The *relative* grading bias among the runs comes only from the answer key and matching rule (D1-D3). Actual
    grader behaviour is unverified.
* **The dominant grading-bias defect is the undefined matching criterion.** "Binding strength" admits two scientifically
  defensible readings, and the dataset contains a near-match for each:
  * apparent cell binding: construct_05/construct_10;
  * a plain 1:1 chip fit: construct_11/construct_12.

  Whichever single key the grader used, a group of runs that cleanly followed the other reading would fail. That is
  2 runs if the key is 05/10, and 4 runs if the key is 11/12.
* **Secondary defects.**
  * An undefined generator feature (the two-arm "fast component") makes the choice among the 4 chip-based runs'
    answers (11/12, 07/12, 04/12) arbitrary.
  * The cell-assay key depends somewhat on the author's curve-fitting convention: 05/10 under a free-Hill 4PL, but
    05/01 under Hill = 1 or half-max interpolation. If the author's key were 05/01, all 12 runs would fail.
* **Some defects can reward correct answers for wrong reasons** (mislabelled post-regeneration rows, QC-flag placement).
  An answer-only grader cannot see this.
* **To reconstruct the grader exactly**, first establish *which system graded the runs*. The prompt's "calling program
  looks for results in /workspace/analysis_output.json" and the completion echo point to LatchBio's own harness, not
  necessarily a Harbor `tests/` verifier. Then obtain:
  * the grading code and its configuration at the run revision, plus the image digest if the verifier ran in the
    agent image;
  * the job/harness layer: reward semantics, error-vs-zero handling, attempts and aggregation, artifacts;
  * the 12 runs' recorded outcomes, logs and actual output files;
  * if the key is derived from the data, the original workbook, generator seeds and reference solution.

  Binary rewards on these 12 runs cannot separate several candidate rules (§3), so synthetic probes against the real
  grader are also needed (§4.6).

---

## 0. Evidence base and caveats
* All 12 sessions end with `termination_reason = submitted`. There are no verifier logs, `reward.txt`, ctrf reports or
  Harbor `result.json`. Which runs actually passed is **unknown**.
* The answer key used in the reconstruction (`{construct_05, construct_10}`) is an *inference*: a 5-judge adversarial
  panel gave it confidence ~0.5. The main alternative is `{construct_11, construct_12}` at ~0.2. See
  `binding-arm-matched-pair/RECONSTRUCTION.md` §4.
* "Pass/fail" below always means "would pass/fail under key X with rule Y".

## 1. What the 12 rollouts submitted

| run | harness | final `matched_pair` | basis of the choice | file format | completion signal | wall time |
|---|---|---|---|---|---|---|
| claude-opus-5-5-1 | Claude Code | construct_05, construct_10 | cell EC50, global 4PL, free Hill (#118); selected with a four-analysis agreement table (#139) | indent-2 JSON, only `matched_pair` (#139) | yes | 46.8 min |
| claude-opus-5-5-2 | Claude Code | construct_05, construct_10 | cell EC50, 4PL with power-0.71 variance weighting and a 600-draw bootstrap (#132) | indent-2 JSON, written at #132 and rewritten at #150 | yes | 64.2 min |
| claude-opus-5-5-3 | Claude Code | construct_05, construct_10 | cell EC50, joint log-4PL (#251) | one-line-array JSON (#272) | yes | 120.0 min |
| gemini-4-argon-1 | Gemini CLI-like | construct_07, construct_12 | chip: two-site fit, keeping the high-affinity site of S109 (62.1/70.3 nM; tool_call #361, result injected at #364) | one-line-array JSON (#421) | yes | 128.0 min |
| gemini-4-argon-2 | Gemini CLI-like | construct_02, construct_09 | cell EC50 plus Top (plateau) and Hill co-criteria (final message #449) | one-line-array JSON (#444) | yes | 111.5 min |
| gemini-4-argon-3 | Gemini CLI-like | construct_02, construct_09 | cell EC50 plus Top co-criterion (final message #301; "sole potent pairs" in reasoning #284) | one-line-array JSON (#293/#296) | yes | 68.6 min |
| glm-5-3-1 | zcode (Claude-Code-like) | construct_04, construct_12 | chip, "per-arm" fast pool of a two-pool model (#111, #135) | one-line-array JSON (#144) | yes | 42.4 min |
| glm-5-3-2 | zcode | construct_11, construct_12 | chip, naive 1:1 KD (#63, #183) | one-line-array JSON (#192) | yes | 56.0 min |
| glm-5-3-3 | zcode | construct_11, construct_12 | chip, naive 1:1 + steady state (#66, #91) | one-line-array JSON (#100) | yes | 15.8 min |
| gpt-6-astra-1 | Codex | construct_11, construct_09 | minimax over cell fold and chip fold (#38, #41) | `json.dumps(indent=2)` from code at #44 (no read-back) | yes | 6.8 min |
| gpt-6-astra-2 | Codex | construct_05, construct_10 | cell EC50, geometric mean of per-run 4PL (#29, #53) | `json.dumps(indent=2)` from code at #56 (no read-back) | yes | 6.7 min |
| gpt-6-astra-3 | Codex | construct_11, construct_09 | minimax over cell and chip, 24 settings (#62, #71) | `json.dumps(indent=2)` from code at #74 (no read-back) | yes | 13.3 min |

Format labels: "indent-2" means each array element on its own line. "One-line-array" means the object is indented
but the two IDs sit on one line. Wall time is the session span (`session_start` to `session_end`). The completion
echo appears after the final write in every run: cl1 #142, cl2 #153, cl3 #275, ge1 #424, ge2 #447, ge3 #299,
gl1 #147, gl2 #195, gl3 #106, gp1 #47, gp2 #59, gp3 #77.

Distribution: 05/10 ×4, 02/09 ×2, 11/12 ×2, 11/09 ×2, 07/12 ×1, 04/12 ×1. No pair is a majority, and the split is
not by model family alone (Gemini splits 07/12 vs 02/09; GLM splits 04/12 vs 11/12).

---

## 2. Defects that may have biased the grading (ranked by impact)

### D1. Undefined "binding strength", with a near-match for each reading. **Severity: high.**
Under a single key, 2 (key 05/10) or 4 (key 11/12) runs that cleanly followed the other reading would fail.
* **What.** The prompt asks for a pair that "match[es] on binding strength first, so that neither construct wins simply by
  binding harder", in order to "isolate the effect of arm number". Both of the following are textbook-defensible:
  * (a) **apparent/functional binding on cells**, avidity included: the format-fair cell titration;
  * (b) **intrinsic per-arm affinity**: SPR KD.
* **Near-matches.**
  * Reading (a): cell EC50 of construct_05 vs construct_10 is 389.7 vs 380.9 nM (claude-opus-5-5-1 #118). The ratio
    is 1.00-1.03 for pooled free-Hill fits, but 1.06 for a run-1-only fit (claude-opus-5-5-3 #226).
  * Reading (b): plain 1:1 chip KD of construct_11 vs construct_12 is 88.01 vs 88.29 nM in series A and 88.9 vs
    90.3 nM in series B (claude-opus-5-5-1 #75). That is agreement to 0.3 % and 1.6 %.
  * claude-opus-5-5-3 #262 also prints 88.48 vs 88.48, but that is a shared profile-grid point with a zero-width CI
    (the agent itself calls it a grid artefact). It is **not** evidence.
  * The chip match is model-dependent. It holds for plain 1:1 and steady-state fits of S109, which fit worse than
    S106 (1:1 rmse 2.55/1.86 vs 0.99/1.25, #75). Other models give construct_12 62-121 nM:
    * two-site main site 62.1/70.3 (gemini-4-argon-1 #364);
    * 1:1 + α 62.3/69.7 (gemini-4-argon-2 #199);
    * fits with drift terms 110-121 (gpt-6-astra-1 #41).

    So "planted" is likely but not proven for reading (b).
* **Effect** (conditional; the actual grades are unknown).
  * Key = 05/10: glm-5-3-2 and glm-5-3-3 would fail despite cleanly following reading (b). glm-5-3-1 and
    gemini-4-argon-1 also used the chip, but with the D2 treatments.
  * Key = 11/12: the three Claude runs and gpt-6-astra-2 would fail despite cleanly following reading (a).
    gemini-4-argon-2/3 (02/09) would fail under either key.
  * Either way, part of the grade measures agreement with the author's unstated interpretation rather than
    analysis quality.
* **Why the data do not settle it.** Both readings have support in the task text:
  * `run_conditions` split the chip protocol by format;
  * "binding harder" on a receptor-expressing line favours (a);
  * "isolate the effect of arm number" and the generator holding KD fixed under kinetic jitter favour (b).

  The reconstruction's adversarial panel split 0.52 / 0.21 (a/b), with the rest spread over within-reading variants.

### D2. Undefined meaning of the two-arm "fast component". **Severity: medium.**
Under a chip key it decides among the 4 chip-based runs (3 distinct answers).
* **What.** The high-avidity two-arm samples carry an extra fast, weak, concentration-proportional binding phase.
  * In gemini-4-argon-2's α table (script #198, results #199/#202), α×500 RU in series A/B is:

    | sample | α×500 RU (A/B) |
    |---|---|
    | c03 | 78.2/57.2 |
    | c12 (S109; α ≈ 0.054/0.034 RU/nM) | 26.8/17.0 |
    | c09 | 6.9/9.9 |
    | c08 | 6.2/3.5 |
    | c01 | 1.8/4.2 |
    | c10 | -5.3/0.8 |

    So roughly c03 > c12 ≫ c09 ≈ c08 > c01 ≈ c10 ≈ 0. One-arm values lie within about ±5 RU.
  * gemini-4-argon-1 used the same α model (#268, #293).
  * Neither the data nor the task text says whether the component is non-specific, monovalent (per-arm) binding or
    avidity.
* **Effect.** Under any chip-based key, three different "correct" answers follow from three treatments of the same
  feature:
  * ignore it → 11/12 (glm-5-3-2/3);
  * treat the fast pool as a second independent site and keep the high-affinity site → S109 62.1/70.3 nM → 07/12
    (gemini-4-argon-1, #361/#364);
  * take the fast pool as the per-arm interaction → ≈2.6 µM → 04/12 (glm-5-3-1, #135).

  Which of these runs a chip key rewards is arbitrary.
* Note: glm-5-3-1's "identical 2,610 nM" for c04 and c12 is a shared profile-grid point (#135), so that run is weak
  on its own terms, but it sits inside an undefined feature.

### D3. The cell-assay key depends somewhat on the author's curve-fitting convention. **Severity: medium (latent).**
* **What.** Within the cell assay the margin between the winner and the runner-up depends on the model.
  * Free-Hill fits: 05/10 1.03 vs 05/01 1.06 (pooled 4PL, oracle in the rebuilt task); 1.023 vs 1.092 (global
    log-space 4PL, claude-opus-5-5-1 #118).
  * Hill = 1, half-max interpolation and model-free estimators rank 05/01 first (claude-opus-5-5-2 #141;
    claude-opus-5-5-3 #226: interpolation 05/01 1.012).
  * The free-Hill ranking is consistent: 05/10 beats 05/01 in each run separately (run 1: 1.059 vs 1.069; run 2:
    1.005 vs 1.036; claude-opus-5-5-3 #226).
  * Hill = 1 is statistically rejected: claude-opus-5-5-2 #141 F-test for 9 of 12 constructs; claude-opus-5-5-1
    #136 for construct_05.
  * construct_05's run-to-run EC50 shift (397.7 vs 366.0 nM) is comparable to the margin but does not flip the
    ranking, because c10 and c01 shift in parallel.
* **Effect.** The best-supported cell model gives 05/10. But if the author's reference fixed Hill = 1 or interpolated,
  the key would be 05/01 and all 12 runs would fail. The four 05/10 runs' passes are therefore contingent on the
  author having used a free-Hill fit, which is the better-supported convention.

### D4. Defects that reward right answers for wrong reasons. **Severity: low for pass/fail, high for interpretability.**
* **Mislabelled post-regeneration rows.**
  * The rows labelled `post_regeneration` simply continue the C = 0 decay. S112 retains 94.1/60.5 RU at t = 3145
    (claude-opus-5-5-1 #91); S109 does so to a lesser extent (post_act 14.26 in cycle_008, #44).
  * The next cycle still starts at baseline: cycle_008's baseline net is -0.66 RU (#44).
  * In our reading this is inconsistent with "one regeneration per cycle" in `run_conditions`.
  * Several runs cited "incomplete regeneration" against the chip: claude-opus-5-5-1, claude-opus-5-5-2 #152,
    gemini-4-argon-3 #301, gpt-6-astra-3 #49. claude-opus-5-5-1 did so alongside "high-density amine coupling", which
    is not in `run_conditions` (only "amine-coupled", #22). Those runs reached 05/10 or other answers partly on that
    misreading.
* **QC-flag placement.**
  * All 8 `low_event_count` wells sit on members of the rival pairs: c01 ×3, c12 ×2, c02/c09/c11 ×1. None are on c05
    or c10 (claude-opus-5-5-1 #32).
  * claude-opus-5-5-1 printed the flag counts (#139) and cited "zero QC-flagged wells, unlike the runner-up
    construct_01" as supporting evidence in its final message (#141). Its main criterion was construct_05's Hill
    slope (#135).
  * Flags carry no binding information (the MFI is NaN). If deliberate this is a leak; if not, it is luck. Either way
    it could tip a borderline decision.
* **Injection order = potency order.** Within each format, chip injection order matches cell EC50 rank. This is a
  structural tell; no run was seen to exploit it.

### D5. Defects that invite (but do not force) errors. **Severity: low. Mostly agent responsibility.**
* **Incoherent cross-assay scales.**
  * Chip KD / cell EC50 is about 4.5 for strong one-arm constructs, 0.8-1.5 for weak two-arm ones and 13-49 for
    strong two-arm ones. If chip KDs were intrinsic, weak two-arm constructs would have an avidity gain below 1.
  * This invites "combine both assays" heuristics: gpt-6-astra-1/3 used minimax, arriving at 11/09.
* **Top-tier decoy and silence on potency.**
  * 02/09 has matched plateaus and Hill slopes, so the curves overlay visually, while 05/10 has a 1.7× plateau gap.
  * gemini-4-argon-2 added Top and Hill criteria (final message #449). gemini-4-argon-3 added Top (final message
    #301) and restricted itself to "potent pairs" (reasoning #284). The prompt asks for neither.
  * The decoy is a legitimate trap. The prompt's silence on any potency requirement is a mild fairness issue for an
    "in vivo" framing.
* **Weak one-arm constructs are unidentifiable on the chip** (top concentration 500 nM ≪ KD; series-B fits hit
  bounds). Any chip-based match involving c04/c05/c06 is noise, as in glm-5-3-1's 04/12.

### D6. Checked and ruled out as grading-bias sources for these 12 runs
| candidate issue | finding |
|---|---|
| Output schema / extra keys | All 12 files contain exactly `{"matched_pair": [id, id]}` with valid, distinct IDs: verified by read-back for 9/12, inferred from the writing code for the 3 GPT runs |
| ID order | All 12 list the one-arm construct first. Every answer except 11/09 is also in sorted order. A one-arm-first rule cannot change any outcome, and a sorted rule could only change 11/09. A two-arm-first rule would zero everyone equally (§3 #20) |
| Whitespace / formatting | Indent-2 vs compact arrays. Irrelevant to any JSON-parsing grader; only a byte-exact string grader would differ (implausible) |
| Output path | All wrote `/workspace/analysis_output.json` |
| Completion signal | All 12 issued `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` |
| Time limit | 6.7-128 min (session span) of 360. No run was cut off |
| Venv not on PATH | Cost early steps, but every run found `/root/.venv` |
| Harness output truncation (Gemini) | Lost middle-of-output data in some calls (e.g. gemini-4-argon-1 #203); no final answer traces back to it |
| Host vs. stated resources | `top` shows a 249,680 MiB host vs the stated 64 GiB; no run was resource-limited |

---

## 3. Outcomes of the 12 runs under candidate keys and grader rules
Rules:
* **S** = set equality (order-insensitive).
* **O1** = ordered, one-arm first. Every run wrote one-arm first, so O1 gives the same results as S.
* **O2** = ordered, two-arm first.
* **P** = 0.5 credit per correct ID.
* **T(x)** = accept any pair whose ratio on the named metric is ≤ x.

Ratios used for T: cell EC50 from the pooled free-Hill 4PL (05/10 1.033, 05/01 1.057, 02/09 1.124, 04/08 1.142,
06/08 1.156, 07/09 1.37, 11/09 1.72), and plain 1:1 chip KD from the A/B geometric means in glm-5-3-3 #91 (11/12
1.010, 07/12 1.30).
Reward vector order: cl1 cl2 cl3 ge1 ge2 ge3 gl1 gl2 gl3 gp1 gp2 gp3.

| # | candidate key / rule | reward vector | passes |
|---|---|---|---|
| 1 | {05,10}, S or O1 | 1 1 1 0 0 0 0 0 0 0 1 0 | 4 |
| 2 | {05,10}, P | 1 1 1 0 0 0 0 0 0 0 1 0 (no other run shares 05 or 10) | 4 |
| 3 | {11,12}, S or O1 | 0 0 0 0 0 0 0 1 1 0 0 0 | 2 |
| 4 | {11,12}, P | 0 0 0 .5 0 0 .5 1 1 .5 0 .5 | 2 (+4 half) |
| 5 | {05,01}, S or O1 (author fit with Hill = 1 or interpolation) | 0 0 0 0 0 0 0 0 0 0 0 0 | 0 |
| 6 | {05,01}, P | .5 .5 .5 0 0 0 0 0 0 0 .5 0 | 0 (+4 half) |
| 7 | {02,09}, S or O1 | 0 0 0 0 1 1 0 0 0 0 0 0 | 2 |
| 8 | {02,09}, P | 0 0 0 0 1 1 0 0 0 .5 0 .5 | 2 (+2 half) |
| 9 | {07,12}, S or O1 | 0 0 0 1 0 0 0 0 0 0 0 0 | 1 |
| 10 | {07,12}, P | 0 0 0 1 0 0 .5 .5 .5 0 0 0 | 1 (+3 half) |
| 11 | {04,12}, S or O1 | 0 0 0 0 0 0 1 0 0 0 0 0 | 1 |
| 12 | {04,12}, P | 0 0 0 .5 0 0 1 .5 .5 0 0 0 | 1 (+3 half) |
| 13 | {11,09}, S or O1 | 0 0 0 0 0 0 0 0 0 1 0 1 | 2 |
| 14 | accept-set {05/10, 11/12}, S | 1 1 1 0 0 0 0 1 1 0 1 0 | 6 |
| 15 | accept-set {05/10, 05/01}, S | same as #1 | 4 |
| 16 | accept-set {05/10, 05/01, 11/12}, S | same as #14 | 6 |
| 17 | T(1.10) on cell EC50 (accepts 05/10, 05/01) | same as #1 | 4 |
| 18 | T(1.15) on cell EC50 (adds 02/09, 04/08) | 1 1 1 0 1 1 0 0 0 0 1 0 | 6 |
| 19 | T(1.05) on plain 1:1 chip KD (accepts 11/12 only) | same as #3 | 2 |
| 20 | O2 (two-arm first required), any key | 0 0 0 0 0 0 0 0 0 0 0 0 | 0 |
| 21 | format-strict: extra required field, or byte-exact canonical serialization | 0 0 0 0 0 0 0 0 0 0 0 0 | 0 |

Consequences:
* **Several rules give identical outcomes**, so binary rewards on these 12 runs **cannot** distinguish:
  * key {05,10} (#1, #2) from accept-set {05/10, 05/01} (#15) or the tolerance rule T(1.10) (#17);
  * accept-set {05/10, 11/12} (#14) from {05/10, 05/01, 11/12} (#16).
* **An all-zero outcome** is consistent with many different causes (#5, #20, #21, any key that no run chose, or a
  verifier error); see §4.5.
* **Format and order rules (O2, strict formats)** would affect all 12 runs identically. They could zero everyone, but
  they cannot reorder the runs. So the *relative* bias among the runs comes only from the answer key and matching
  rule (D1-D3).

---

## 4. What we need to reconstruct the grader exactly
"Exact" means the same reward, or error state, for every possible agent output, under the same job configuration.

### 4.0 First establish which system graded the runs
* The prompt says "*The calling program looks for results in `/workspace/analysis_output.json`*" and requires a
  completion echo. Both point to LatchBio's own evaluation harness, not necessarily Harbor.
* The completion signal and `termination_reason` are harness-level concepts that a Harbor verifier would not see.
* So we need to know whether these 12 rollouts were graded:
  * by a Harbor `tests/` verifier;
  * by LatchBio's "calling program" (for example a script that reads the file inside or after the agent container);
  * or by both.
* **The Harbor port in this folder is a reconstruction.** Its `tests/` is our grader, not the original.

### 4.1 Tier A: primary artefacts of the grading code
1. **The grader code at the exact revision used for these runs.**
   * Harbor case: the full `tests/` directory (`test.sh`, any `test_*.py`, helpers, fixtures, expected-answer files)
     and any verifier `Dockerfile` / `docker-compose.yaml` under `tests/`.
   * LatchBio-harness case: the calling program's grading function and its config.
2. **The verifier configuration.**
   * `task.toml` `[verifier]`: `timeout_sec`, `env`, `user`, `environment_mode` (shared / separate),
     `network_mode`, `allowed_hosts`, `[verifier.environment]`;
   * top-level `artifacts`;
   * `[agent].timeout_sec`.
3. **The environment the verifier executes in.**
   * If the verifier runs in the agent image (shared, or a fresh copy), the grader can depend on that image: its
     Python, packages and baked-in files. We then also need `environment/` (Dockerfile and build context) at the same
     revision and **the image digest** actually used.
   * In shared mode the verifier also sees whatever files the agent left behind.
   * `tests/` alone is sufficient **only if** the verifier is self-contained (its own image, no dependence on agent
     files other than the answer).
4. **Source and version pointers**: repository or registry entry, task name/version, commit or content hash, so 1-3
   are fetched consistently.

### 4.2 Tier A (cont.): job and harness layer
Needed even with the grader code, because these change which reward is recorded:
1. **Reward semantics.**
   * `reward.txt` vs `reward.json` (Harbor prefers `reward.json` if both exist);
   * for `reward.json`, which label is the headline score and whether the job config selects one;
   * any post-hoc normalization or thresholding.
2. **Error handling.** How a verifier crash, a verifier timeout (Harbor default 600 s), a missing reward file or a
   missing output file is recorded: as an *error state* or as 0. Whether errored trials are retried, excluded from
   means, or counted as fail.
3. **Attempts and aggregation**: `n_attempts`, how rewards are combined (mean, max, pass@k), retry policy. Were
   these 12 rollouts separate trials of one job?
4. **Artifact collection.** Which paths are collected (is `/workspace/analysis_output.json` among them?), and whether
   the verifier sees the final file or a snapshot taken at a particular time (for example on timeout).
5. **Permissions.** The verifier user, whether it can read the agent's file, whether `/logs/verifier` is writable,
   and when `tests/` is uploaded.
6. **Versions** of Harbor and of each agent harness (Claude Code, Gemini CLI-like, zcode, Codex) used for these runs.

### 4.3 Tier B: behavioural specification (only if the code is unavailable)
1. **Answer key set.** One pair, or several acceptable pairs (accept-set), or a tolerance rule (§3 #14-#19)?
2. **Matching rules.**
   * set vs ordered, and in which orientation (one-arm first, two-arm first, sorted, as listed);
   * ID normalization (case, whitespace, `construct_5` vs `construct_05`);
   * duplicate handling.
3. **Schema strictness.**
   * Must the file contain only `matched_pair`? The prompt says "ONLY the JSON object with the required fields";
     are there other required fields?
   * Are extra keys tolerated?
   * Are markdown fences, trailing text, BOM or an empty file tolerated?
   * Must the value be a list, or is a string/tuple accepted?
4. **Reward computation**: binary, partial (per ID, per format) or continuous; and the value for invalid outputs.
5. **Process conditions.**
   * Is grading gated on the completion echo or on the harness termination reason (submitted vs timed out)?
   * Is the file read in place (the "calling program") or copied as an artifact?
6. **Verifier runtime**: interpreter and package versions (python, pytest, pytest-json-ctrf, uv/uvx if used), network
   access during verification (needed for `uvx`-style scripts), timeout, user.
7. **Grader type**: programmatic only, or with an LLM-judge / rubric step (e.g. on a rationale). The JSON-only prompt
   suggests programmatic, but this is unconfirmed.

### 4.4 Tier C: data-dependent grading
1. **How to tell whether the key is hard-coded or derived.**
   * Search `tests/` for the construct IDs, a workbook copy, or a call into `solution/`.
   * Check whether the grader recomputes the key from `/workspace/data/binding_panel_raw.xlsx` at test time.
2. **If the key is derived, we also need:**
   * the original workbook bytes (1,387,104 B) with sha256/md5. Our rebuild matches the titration sheet to ±0.5 AFU
     per well (see `binding-arm-matched-pair/RECONSTRUCTION.md` §2.1), but the chip sheet is a simulation;
   * the data-generator script and its seeds;
   * the reference solution (`solution/solve.sh` and helpers) with its exact fit settings (free Hill vs Hill = 1,
     weighting, background, tie rule, random seeds). This decides D3;
   * any tolerance or threshold used to accept a pair.

### 4.5 Tier D: ground truth and data to validate a reconstruction
1. **Actual outcomes of the 12 rollouts**: per-trial `result.json` (including any exception info), `reward.txt` /
   `reward.json`, verifier stdout/stderr and ctrf report, and the trial and job config.
2. **The 12 actual final `analysis_output.json` files**, or the final container state.
   * The traces show what each agent wrote; for the 3 GPT runs the content is inferred from code.
   * To re-run a recovered grader on the real outputs we need the files themselves, and to know whether the job can
     be regraded. Harbor supports regrading only with a separate verifier environment.
3. **The data file each agent saw.** Confirm (e.g. by hash) that it equals the one the grader used.
4. **How to read the outcomes** (they constrain the rules but rarely identify them uniquely):
   * **Only cl1/cl2/cl3/gp2 pass:** consistent with key 05/10. It does **not** exclude accept-set {05/10, 05/01} or
     T(1.10) (§3 #15, #17).
   * **Only gl2/gl3 pass:** consistent with key 11/12 or T(1.05) on chip KD.
   * **Both groups pass:** an accept-set or tolerance rule covering both readings (#14/#16).
   * **ge2/ge3 also pass with the 05/10 group:** T(1.15) on cell EC50 or a broader accept-set (#18).
   * **Half rewards:** partial credit, and the pattern of halves identifies the key (#4, #6, #8, #10, #12).
   * **Nobody passes:** uninformative until the logs show *real graded zeros* rather than errors or timeouts. Possible
     causes: a key nobody chose (05/01 is only one candidate), O2 ordering, a format-strict rule, a missing extra
     field, a path or harness mismatch, or a verifier crash. Use verifier stdout and `reward.json` labels to tell
     them apart.

### 4.6 Probes (run the original grader on synthetic outputs)
Needed even with rewards, because the 12 rollouts all used the same conventions. Record the reward **and** the logs
for each probe, and repeat each one to check determinism.
* **Pairs.** Ideally all 66 construct pairs in both orders (132 probes). At minimum, pairs near the candidate keys:
  05/10, 10/05, 05/01, 01/05, 11/12, 07/12, 04/12, 02/09, 04/08, 06/08, 11/09, and 05 with each other two-arm
  construct.
* **Format.**
  * an extra key (with and without a rationale);
  * a different case for the key `matched_pair`;
  * ID case and whitespace variants;
  * duplicate IDs; a 1- or 3-element list; an empty list;
  * a nested list; a string instead of a list; null or numeric IDs; a nonexistent ID;
  * markdown fences or trailing text around valid JSON;
  * a trailing newline vs none; a BOM; an empty file; a directory or symlink at the path.
* **Process.**
  * missing file; file at the wrong path (including the artifact directory);
  * run without the completion echo;
  * agent timeout with a valid file present.
* **Granularity.** Check whether rewards are binary, partial or continuous.

### 4.7 Minimum sufficient set
* **Best case:** the grading code and configuration (§4.0-§4.2) at the run revision, including the image digest when
  the verifier runs in the agent image. Use the 12 recorded outcomes and files (§4.5) as confirmation.
* **Otherwise:** the behavioural specification (§4.3) plus the 12 outcomes, logs and files (§4.5), plus the probe
  results (§4.6). Add Tier C (§4.4) if the key is derived from data.

## 5. Recommendations if the task is re-issued
1. **Define the criterion** in the prompt: "match apparent binding on the receptor-expressing cells (EC50)" or "match
   intrinsic per-arm affinity". Alternatively, accept both planted pairs and document why.
2. **Widen the winning margin** (≥ 1.5× to the runner-up under any reasonable fit), or state the fitting model
   (free-Hill 4PL) in the prompt.
3. **Fix generator artefacts.**
   * Make `post_regeneration` reflect an actual regeneration step.
   * Remove QC-flag placement and injection order as tells.
   * Either define the two-arm fast component or remove it.
4. **Record verifier provenance** (rewards, logs, versions) alongside rollouts, so future audits are not conditional.

## Appendix: where the evidence lives
| item | location |
|---|---|
| Trace parser | `recon_work/tools/trace_lib.py` |
| Per-run summaries and fact files | `recon_work/facts/<run>.summary.md`, `<run>.json` |
| Cross-run answer synthesis (traps T1-T29) | `recon_work/facts/SYNTH_answers.md` |
| Judge panel verdicts | workflow `wf_fccc799a-d66` journal (summarised in `RECONSTRUCTION.md` §4) |
| Replays of all 12 runs on the rebuilt task | `recon_work/replay/*.final.out.json` |
| Reconstructed task + notes | `latch-bio-harbor-task/binding-arm-matched-pair/`, `RECONSTRUCTION.md` |
| Adversarial verification of this report | workflows `wf_5d80f2df-7db` (per-run table, defects) and `wf_7fae6dbf-5d0` (§3-4). Their findings were applied: citations re-pointed to decision steps, a grid-artefact citation removed, counts corrected, scenarios and grader-layer items added |
