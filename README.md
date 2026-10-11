# Mamyshev optical simulation and Scientific ML

This project contains optical-simulation interfaces, data generation,
training/evaluation, conditional design search and provenance-aware database
storage. The full local project retains the MATLAB/GMMNLSE production, scan,
save, resume and export routes. **Mamyshev Design Explorer** is its frozen-model
prediction interface. Public live-solver execution has external-resource
blockers described below; a clone is not an unconditionally runnable MATLAB setup.

The main project is the sole maintenance source: edit and test here, then export
a small deployment snapshot for the reviewed publication scope. The
current Demo uses only `demo_10k_v1`; historical 1024-design models and evidence
remain available for research reproduction outside the current Demo.
The 10k model was trained on **10,000 unique repository-guided synthetic designs**,
not 10,000 GMMNLSE runs. Its full-solver validation remains pending.

## Demo showcase

Published code: [complete project](https://github.com/Yukino8735/Mamyshev-Oscillator-Simulation) · [lightweight single-10k Demo](https://github.com/Yukino8735/mamyshev-design-explorer). Both default branches were remotely verified after publication. The public MATLAB live route remains blocked as described below; GitHub code publication is separate from website deployment.

**[Interactive demo & website status](docs/DEMO_SHOWCASE.md)** ·
[Run locally](#run-the-local-interactive-demo) ·
[Real-simulation validation roadmap](docs/REAL_SIMULATION_VALIDATION_PLAN.md)

**Website: deployment pending.** The local single-model Demo is available;
there is no public URL yet. The showcase page describes the prepared Streamlit
deployment and acceptance steps. Once an actual public URL is verified, this
entry will link directly to **Open live demo**.

## Run the local interactive demo

From this directory, use your existing `mamyshev-ml` environment:

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python -m streamlit run demo/app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

Open `http://127.0.0.1:8501`; stop with **Ctrl-C**. This command needs the reviewed
assets under `demo/assets/` and the dependencies in [demo/requirements.txt](demo/requirements.txt),
not training data or `reports/local`. It never trains or starts MATLAB.
The Demo uses only `demo_10k_v1`, retaining the reviewed single-model behavior.
There is no model selector. Historical V4.2 research assets and explicit research
CLI routes remain available outside this Demo. The frozen model and manifest
are checked before loading; stale or foreign result identities are rejected.

Start with **Load fixed-hardware example**: fix pump power at 4 W and gain
length at 4 m, require predicted duration ≤40 fs, and compare filter designs by
predicted peak power. Submit a bounded candidate set, compare the chosen design
with the baseline, then export up to three requests for later evaluation.
The highest prediction is the best in that submitted set, not a physical optimum.

The earlier [synchronization report](docs/DEMO_MAIN_SYNC_REPORT.md) and
[version receipt](demo/source_version.json) record the initial UI migration.
Current maintenance and export instructions are in
[Demo development](docs/DEMO_DEVELOPMENT.md); this batch's evidence is in
[the project/export synchronization report](docs/PROJECT_DEMO_SYNC_REPORT.md).
Browser visual acceptance and cloud deployment remain pending.

| Entry | What it does |
|---|---|
| **Design workbench** | Baseline/current comparison, explicit constraints, ≤4096 X-only candidates, selected zero-allowance requests |
| **Parameter response** | ≤21-point curves or ≤441 actual rect heatmap cells, exact baseline and feasible-best markers |
| **Method & data** | Synthetic training source, saved model structure, aggregate metrics and diagnostic intervals |
| **MATLAB pipeline** | Inspect the 10,000-design pending plan summary; no live execution button |

See the [Chinese guide](docs/USER_GUIDE_ZH.md), [UX review](docs/DEMO_UX_REVIEW_REPORT.md),
[10k model report](docs/DEMO_10K_RELEASE_REPORT.md),
[machine-generated model comparison](docs/assets/demo10k/model_comparison.md),
and [aggregate metrics](docs/assets/demo10k/aggregate_metrics.json).
Both models passed their own fixed synthetic point-tolerance tests. Their test
sets differ; this is not a common-test sample-size ablation. Diagnostic intervals
remain **limited**, including lower near-slice coverage. Real-solver error and
real-simulation savings are **not_measured**.

The current task authorizes bounded code publication after the applicable checks.
This does not authorize a cloud App or new data uploads. The repository already
contains tracked historical data; this release does not delete or republish it
as new data. See the historical [Git release plan](docs/GIT_RELEASE_PLAN.md) and
the current [release report](docs/FULL_PIPELINE_GITHUB_RELEASE_REPORT.md) for actual
remote status, release contents and remaining blockers.

## Reusable data → features → training workflow

The normal training entrypoint is `scripts/train_surrogate.py`, using explicit
V4Store SQLite or its lossless training CSV and an exact source identity. It does
not need a private V4 experiment manifest or fixed historical run directory.
The following is a small **future-use example**, not a claim that this release
generated labels or retrained the 10k model. Use a new output directory; never
clear an existing run to repeat it.

```sh
mkdir -p reports/local
mkdir reports/local/user_pipeline_001
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/v4_scan.py plan \
  --spec examples/plan_small.json --out reports/local/user_pipeline_001/plan.json
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/v4_scan.py run \
  --plan reports/local/user_pipeline_001/plan.json --db reports/local/user_pipeline_001/evaluations.sqlite \
  --scan-id small_synthetic --evaluator synthetic --execute --max-new-attempts 16 --total-wall-s 60 \
  --stop reports/local/user_pipeline_001/STOP
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/train_surrogate.py identities \
  --db reports/local/user_pipeline_001/evaluations.sqlite --out reports/local/user_pipeline_001/identities.json
```

`plan_small.json` is a 16-design LHS input plan. The explicit `run` command above
would query the repository-guided **synthetic** generator, not MATLAB. Omitting
`--execute` leaves it plan-only. Select exactly one object from the `identities`
array and save that object as `reports/local/user_pipeline_001/identity.json`;
retain all six source/backend/version/seed/observation/metric fields, not the
inventory wrapper. There is no implicit source mixing or fallback.

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/train_surrogate.py export \
  --db reports/local/user_pipeline_001/evaluations.sqlite --identity reports/local/user_pipeline_001/identity.json \
  --out reports/local/user_pipeline_001/training.csv
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/train_surrogate.py split \
  --csv reports/local/user_pipeline_001/training.csv --identity reports/local/user_pipeline_001/identity.json \
  --seed 11 --out reports/local/user_pipeline_001/split.json
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/train_surrogate.py fit \
  --csv reports/local/user_pipeline_001/training.csv --identity reports/local/user_pipeline_001/identity.json \
  --split reports/local/user_pipeline_001/split.json --model-id user-source-emulation-001 \
  --out reports/local/user_pipeline_001/model
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/train_surrogate.py predict \
  --model-dir reports/local/user_pipeline_001/model --trusted-local --design examples/design_default.json \
  --out reports/local/user_pipeline_001/prediction.json
```

The saved original `LogSurrogate` applies domain scaling, spline/interaction
features, a training-only StandardScaler, log-target Ridge fitting and exp output
restoration. Only the four design inputs are features. The fixed K64 representation
has 329 features; this entrypoint performs one three-target fit without search or
calibration. Same-design repeats cannot cross split groups. At least eight distinct
training designs and two development designs are required to exercise the API;
these minimum counts do not establish predictive accuracy. An explicit test group
can be supplied in the split; it is never borrowed from a frozen release.

The training CSV preserves original `record_json`, units and evidence references;
it is **not** the flattened `v4_scan.py export` results CSV. Failed/missing/null
records are excluded with reasons, predictions never become labels, and a single
real design is insufficient for fitting. Model metadata records this dataset's
source, protocol, counts, split and fitted transforms, without borrowing the old
10k model's q or scores. `--trusted-local` applies only to weights you trust;
joblib is executable serialization.

For a genuine completed solver result, import its original parent final into a
new database, then use the same identity selection, export and training commands:

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/v4_scan.py import-final \
  --db reports/local/user_pipeline_001/solver.sqlite --final /path/to/original/run/final_result.json
```

`v4_training.training_records/read_records` rechecks the actual final, request,
runner and referenced waveform integrity. All three targets come from the same
compressed-analysis plane. Its **solver-emulation** qualification does not change
`physical_state=undetermined`, numerical validation or validated-truth eligibility.
The frozen low-level `V4Store.training_records` remains an identity selector, not
this qualification boundary. Keep real and synthetic identities separate and keep
the original evidence available; missing finals cannot be reconstructed from CSV.

The bounded release check passed using 128 saved training records and 16 saved
development records, with 144 distinct designs and no old held-out access. One
temporary `release-smoke` fit ran from a clean source copy: 329 features, scaler
fitted on exactly 128 rows, and zero save/load prediction difference. One genuine
saved final also passed DB → qualified training CSV → X/y export with its original
physical-validation flags unchanged. These are interface checks, not new model
accuracy evidence. No new labels, 10k fit or MATLAB launch occurred; costs and
component-test results are in the release report.

## MATLAB route and public execution prerequisites

The `plan` subcommand and `examples/plan_small.json` shown above use the same
plan format for future real execution and start no MATLAB. Real
execution remains the existing `GMMNLSEEvaluator → supervisor →
run_mamyshev_recorded → run_mamyshev_config` chain, with separate explicit
authorization for the plan hash, designs, seed, attempt and wall-clock budgets.
Its CLI adds `--evaluator gmmnlse --authorization AUTHORIZATION.json --batch-dir
NEW_BATCH --execute --execute-real`; these flags do not grant authorization by
themselves. STOP, per-attempt finalization and cumulative resume limits remain.

**Public live-solver path: blocked.** The unchanged strict initialization gate
requires `reports/local/phase1/baseline_001/configuration.mat` and
`configuration.json`. These private historical resources are not public inputs,
and there is no published substitute or configurable preparation route that
removes that requirement. Locally modified Cornell propagation code is also
excluded from this publication pending its separate distribution scope. The full
local code is preserved; gates are not disabled, references are not fabricated,
and an upstream download alone is not claimed to reproduce the customized engine.
MATLAB/toolboxes, material inputs and these exact resources must be resolved before
claiming a new public checkout can run this path. See the release report for the
precise excluded paths and historical evidence; synthetic data/ML and pure Demo
inference have separate runnable scopes.

## Export the deployment snapshot from the main project

After the affected component checks, export to a new, nonexistent directory:

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python -B scripts/export_demo.py --output "$(cd .. && pwd)/Mamyshev_Demo_Deploy_synced_001"
```

This resolves the batch's destination to an absolute path before export;
literal `..` path components are rejected. Once that output exists, preserve it;
the exporter refuses to overwrite it. Future exports need an explicitly chosen
new destination. The public profile and templates live in `demo/deploy/`, with
an exact file allowlist and frozen model checks. Exporting does not fit, query
labels or start MATLAB, and does not need training CSVs, historical databases,
private reports or the previous deployment copy.

The generated directory is an ordinary-file delivery snapshot, not another
development project. Its small `src/` is generated from selected pure functions
in this repository; it must never replace the full research `src/`. Keep the
older `Mamyshev_Demo_Deploy` snapshot for comparison. Develop only here, then
**test → export → approve the exact new manifest → publish separately**.
No repository or live Demo URL is created by export.

## Optical project background

The optical project originated as `Maymashev 1`. Ring and linear cavity programs,
the customized propagation engine, historical data/figures, thesis and references
remain available. The ring model references Haig et al.'s all-fiber Mamyshev
oscillator; its historical baseline uses a 4 m gain fiber and SF2 at 1030 nm
(10 nm below SF1), rather than the reference's 1036 nm. The Boulanger-inspired
linear FBG model includes a 0.2 m output pigtail, not the full external GMN
amplifier. See [parameter mapping](docs/PARAMETER_MAPPING.md) and
[literature notes](docs/LITERATURE_NOTES.md).

## Historical local-only CLI and closeout bundle

Use the **existing** `mamyshev-ml` environment. Replace the Conda path below with
your actual installation; no environment creation or installation is implied.
All repository commands are run from the repository root. Model artifacts and
historical results are local ignored files, not downloads included in Git.

```sh
CONDA_EXE=/path/to/existing/conda
mkdir reports/local/user_demo_001
"$CONDA_EXE" run -n mamyshev-ml --no-capture-output python scripts/v43_scan.py predict \
  --input reports/local/application_v4_3_001/demonstration/single_input.json \
  --model reports/local/accuracy_v4_2_001/release/model.joblib \
  --selection reports/local/accuracy_v4_2_001/release/selection.json \
  --out reports/local/user_demo_001/prediction.json
```

Stop if the output directory already exists and inspect it; do not clear old
evidence. This example explicitly chooses V4.2; the old default model is unchanged.
JSON accepts one four-field object or a list. Normal prediction never trains,
requests a synthetic label, starts MATLAB or falls back to another backend.
The complete original release is needed for repository loading.

For a small standalone local copy, extract
`reports/local/mvp_closeout_001/inference_bundle.zip` into a new directory. It
contains the original model/custom class, configuration, q, provenance, manifest
and exact dependency versions, without the propagation engine or full archive.
From that directory:

```sh
env -u PYTHONPATH "$CONDA_EXE" run -n mamyshev-ml --no-capture-output python infer.py verify
env -u PYTHONPATH "$CONDA_EXE" run -n mamyshev-ml --no-capture-output python infer.py predict \
  --input inputs.json --output predictions.json
env -u PYTHONPATH "$CONDA_EXE" run -n mamyshev-ml --no-capture-output python infer.py predict \
  --input inputs.csv --output predictions.csv
```

An existing default input is
`{"pump_power_W":4,"filter_offset_nm":10,"filter2_bw_nm":3,"gain_length_m":4}`.
CSV uses those four headers in any order. Exact assets are checked before loading
the model. Hashes establish identity/integrity, not the safety of unknown pickle
or source code. The independent inference manifest does not replace or weaken
the original experiment release. Actual verification scope and commands are in
[the closeout report](docs/MVP_CLOSEOUT_REPORT.md); same-environment testing outside
the repository is not a new clean-environment or cross-platform certification.

Read existing local-only `reports/local/application_v4_3_001/candidates/`
without requesting new evaluations. Public-review summaries are in
[demo/assets/historical_candidates.json](demo/assets/historical_candidates.json).
The [Chinese guide](docs/USER_GUIDE_ZH.md)
provides exact CSV `plan → run → export` commands, 1D/2D prediction specs,
plot/export of copies of saved databases, and historical MAT waveform reading.
Replay consumes saved results; it is not a new live run. The 81-point heatmap is
historical, not regenerated by this closeout.

## Interface and interpretation

| Input, in model order | Unit | Declared input domain |
|---|---|---|
| `pump_power_W` | W | 2–10 |
| `filter_offset_nm` | nm | 2–16 |
| `filter2_bw_nm` | nm | 0.5–8 |
| `gain_length_m` | m | 1–8, exactly on a 0.1 m grid |

`filter_offset_nm = SF1 - SF2`, with SF1 fixed at 1040 nm. A separate conflicting
`cw2` field is rejected. Nonfinite, unknown, missing, out-of-domain or off-grid
inputs fail explicitly; they are not clipped or rounded. This is an exploratory
synthetic domain, not a validated laser operating envelope.

Outputs are `compressed_energy_nJ`, `compressed_duration_fs`, and
`compressed_peak_power_MW`, in that order. Predictions have no propagated complex
field. Legacy passive lengths (0.4/1.5/3.2 m), 0.2 m pigtail and unresolved H02
MFD/SR convention remain separate from surrogate accuracy claims.

| Record/source | Meaning |
|---|---|
| Synthetic `Evaluation` | A labeled result from the identified analytic synthetic generator |
| Recorded `Evaluation` | Replay with matching source, numerical version, seed, observation and metric identity |
| Surrogate `Prediction` | Output of explicit frozen weights, stored separately from Evaluation |
| GMMNLSE `Evaluation` | A separately authorized real production run through the existing supervisor |

## Saved evidence, three different experiments

The tables below are generated from the machine-readable
[public aggregate summary](docs/assets/demo10k/aggregate_metrics.json) and the local-only
`reports/local/mvp_closeout_001/evidence/evidence_summary.json`,
not from new scoring. Each claim's sources, protocol, cost and limits are in
[CLAIM_EVIDENCE.md](docs/CLAIM_EVIDENCE.md).

<!-- MVP_RESULTS_START -->

<!-- Generated from evidence_summary.json by scripts/export_mvp_evidence.py. -->
### A. Frozen V4.2 supervised accuracy (saved synthetic evaluation)

1024 training designs; 2048 new test designs in the fixed stratified mixture. All saved test points met the stated tolerances; this is not zero error or real-solver accuracy.

| Target | MAE | P95 absolute error | P95 relative error | Tolerance |
|---|---:|---:|---:|---|
| compressed_energy_nJ | 0.159472395 nJ | 0.534898777 nJ | 0.282357% | max(2 nJ, 3% of truth) |
| compressed_duration_fs | 0.0335371312 fs | 0.0967493076 fs | 0.227693% | max(1 fs, 3% of truth) |
| compressed_peak_power_MW | 0.00325829759 MW | 0.0116808147 MW | 0.265623% | max(0.05 MW, 5% of truth) |

Intervals remain **limited**: saved empirical joint coverage is overall 1936/2048 (94.5312%); near_slice 216/256 (84.375%); core 467/512 (91.2109%). They are not physical safety guarantees.

### B. Historical V4 cold-start GP/random comparison

A separate experiment: 4 scenarios × 3 paired seeds × 2 strategies × 64 logical evaluations. The first 16 evaluations were initial exploration. This did not use the V4.2 trained model.

| Scenario / objective | GP final best, seeds 11 / 22 / 33 | Random final best, seeds 11 / 22 / 33 |
|---|---|---|
| S1_peak_under_40fs (MW, maximize) | 14.3462622 / 14.9229959 / 14.4954327 | 10.5958788 / 10.8273935 / 10.9856636 |
| S2_low_pump (MW, maximize) | 9.84388539 / 9.41562613 / 9.84388539 | 6.68269651 / 7.45938545 / 8.67179634 |
| S3_fixed_hardware (MW, maximize) | 3.99613928 / 3.99613928 / 3.99613928 | 3.71107937 / 3.67768765 / 3.84952964 |
| S4_short_pulse (fs, minimize) | 20.013675 / 20.0924734 / 20.0614535 | 21.1880201 / 22.9480935 / 22.0779072 |

Saved accounting: 1536 logical events, 1230 unique computations, 306 cache hits. Three seeds support a finite descriptive comparison, not general superiority.

### C. V4.3 frozen-model application with a 1024-design training prior

Each method received 8 confirmations per scenario, with the same known T2 incumbent. 64 events / 63 new designs / 1 cache hit; one seed, no significance claim. Values below are analytic synthetic evaluations, not MATLAB or experimental measurements.

| Scenario | Method | Unit | Shared T2 incumbent | Best new confirmed point | Final best including incumbent | Improvement |
|---|---|---|---:|---:|---:|---:|
| S1_peak_under_40fs | model | MW | 13.5206379 | 14.3437531 | 14.3437531 | 6.087842% |
| S1_peak_under_40fs | random | MW | 13.5206379 | 9.16375592 | 13.5206379 | 0.000000% |
| S2_low_pump | model | MW | 7.88229025 | 9.02347852 | 9.02347852 | 14.477877% |
| S2_low_pump | random | MW | 7.88229025 | 2.31116812 | 7.88229025 | 0.000000% |
| S3_fixed_hardware | model | MW | 3.92527199 | 3.95402408 | 3.95402408 | 0.732486% |
| S3_fixed_hardware | random | MW | 3.92527199 | 2.72010745 | 3.92527199 | 0.000000% |
| S4_short_pulse | model | fs | 20.3033326 | 20.1818449 | 20.1818449 | 0.598363% |
| S4_short_pulse | random | fs | 20.3033326 | 23.2847113 | 20.3033326 | -0.000000% |

Improvement uses only the shared known T2 incumbent as denominator, with the objective's direction. The random method retains its incumbent; weaker new samples did not make its final best worse. S1–S3 maximize peak power; S4 minimizes duration. Neither the full candidate pool nor the continuous domain was exhaustively evaluated.

**Real-solver generalization error and real-simulation savings: not measured (`null`).** The current model does not emulate a validated full GMMNLSE response.

<!-- MVP_RESULTS_END -->

The V4.2 point tolerances apply to a fixed synthetic test mixture, not “100%
accuracy.” Diagnostic intervals remain **limited**: overall empirical joint
coverage 1936/2048, near-slice 216/256 (84.375%), core 467/512; there is no
per-group, per-point or physical safety guarantee. Synthetic values such as
14.34 MW are generator evaluations, not MATLAB or laboratory measurements.
Real-solver generalization and real-simulation savings remain `not_measured`.

Aggregate results are available in [aggregate_metrics.json](docs/assets/demo10k/aggregate_metrics.json)
and [model_comparison.md](docs/assets/demo10k/model_comparison.md). Historical
pointwise scatter, response-grid and candidate figures remain local; they are not
new publication assets for this release.

## MATLAB and research reproduction: separate authorization required

Four-input production generation, 1D/2D/4D plans, random/LHS plans, per-point
persistence, STOP/cancel/resume, database and CSV/MAT export, recorded results and
real MAT reading are preserved. `run_mamyshev_config` uses the original production
loop. New live scans default to **zero** allowed attempts; a plan is not an
authorization. Live execution requires a separately approved plan identity,
design IDs, total/per-run budgets and attempt count. The parent supervisor owns
the final record and cleans only its own process group. Failed history stays
failed; deleting locks or changing IDs is not resume.

The former closeout checked help/configuration paths. The historical 10k batch also
validated a full 10,000-row pending plan, three-point recorded cancel/resume and
one MATLAB short process: four original-grid initializations and 32-point formula
parity, **zero propagation calls**. See the [capability matrix](docs/DEMO_10K_MATLAB_MATRIX.md).
Strict future live parameter checks still require the original local reference
MAT; the data-free Demo copy cannot by itself perform a live run. No gate is disabled.

Historical CLI help:

```sh
"$CONDA_EXE" run -n mamyshev-ml --no-capture-output python scripts/v4_scan.py run --help
"$CONDA_EXE" run -n mamyshev-ml --no-capture-output python scripts/v4_scan.py waveform --help
"$CONDA_EXE" run -n mamyshev-ml --no-capture-output python scripts/run_v4_ml.py select --help
"$CONDA_EXE" run -n mamyshev-ml --no-capture-output python scripts/run_v4_search.py --help
```

`v4_scan.py` routes synthetic or GMMNLSE data generation; `run_v4_ml.py select`
fits models and `evaluate` requires `--authorize-final-evaluation`;
`run_v4_search.py` reproduces the historical cold-start experiment. These need
new explicit computation budgets and are not normal demo commands. Configurations
are in `mamyshev_accuracy_v4/configs/{domain,accuracy_protocol,scenarios}.json`.
Do not rerun completed experiments into their existing directories.

Historical MATLAB entry points remain available below for provenance and future
approved use; they were **not executed in this closeout**. Existing local history
uses MATLAB R2025a. The earlier project-organization report's lack of MATLAB was
a historical environment limitation, not the current machine's state.

```matlab
cd('/path/to/Mamyshev_Oscillator_Project/code')
[project_root, engine_root] = setup_mamyshev_project();
% Historical ring / linear single points:
run(fullfile(project_root,'code','ring_cavity','main','Mamyshev_ring_cavity.m'));
run(fullfile(project_root,'code','linear_cavity','main','Mamyshev_linear_cavity.m'));
% Historical scan entries (require separate run budgets):
run(fullfile(project_root,'code','ring_cavity','scans','scan_mamyshev.m'));
run(fullfile(project_root,'code','linear_cavity','scans','scan_linear_FBG_mamyshev.m'));
```

| Capability/evidence | Actual scope |
|---|---|
| Local frozen bundle and ≤9 saved-input smoke test | Current closeout; exact outcomes in the report |
| Single/batch predictions, 9/81-point scans, database and CSV/MAT | Executed in V4.3; not repeated as new experiments |
| MATLAB production initialization, single-return and waveform history | Historical/component evidence only; see phase reports |
| New complete GMMNLSE scan | `not_run`; implementation retained |
| Deep Phase 2 physical validation | `deferred/in_progress` |
| Public/GitHub release | `not_authorized` |

`physical_state=undetermined`, `numerical_validation=not_verified`, and
`eligible_as_validated_training_truth=false` remain in force. No old résumé
example metrics are acceptance criteria or new achievements.

## Repository and attribution

| Path | Contents |
|---|---|
| `src/mamyshev_ml/`, `scripts/`, `tests/` | Provenance, inference, scan/store/export, authorized execution and tests |
| `code/ring_cavity/`, `code/linear_cavity/` | Optical single-point, scan and plotting programs |
| `code/simulation_engine/GMMNLSE/` | Customized GMMNLSE actually used by the optical project |
| `data/`, `results/`, `archive/` | Original historical data, figures and script versions |
| `docs/thesis/`, `docs/references/` | Thesis and source literature |
| `third_party/MMTools/` | Separate reference package, not the actual engine on the project path |
| `reports/local/` | Ignored local evidence and inference package; not publicly uploaded |

See [data provenance](data/README.md), [engine provenance](code/simulation_engine/README.md),
[third-party notes](third_party/README.md), and [attribution review](docs/ATTRIBUTION_REVIEW.md).
MMTools retains its GPLv3 license and embedded notices. The customized engine and
repository-wide distribution rights require review; no blanket MIT license or
ownership claim is added. Local delivery is not public redistribution permission.

中文：先用[本地使用指南](docs/USER_GUIDE_ZH.md)进行纯预测或读取已有结果；
输入必须是四字段，长度严格为 0.1 m 格点。合成预测、历史回放和真实传播分开记录。
新批已完成一次 10k 合成训练与有界组件检查；没有真实整腔传播、搜索或发布。
结果见[本批报告](docs/DEMO_10K_RELEASE_REPORT.md)，旧[收尾报告](docs/MVP_CLOSEOUT_REPORT.md)保持历史身份。
