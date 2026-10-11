# Claims and evidence for the local ML MVP

## New bounded batch: actual 10k synthetic training and interactive delivery

See [DEMO_10K_RELEASE_REPORT.md](DEMO_10K_RELEASE_REPORT.md) and the data-free
[aggregate evidence](assets/demo10k/aggregate_metrics.json). `demo_10k_v1` fitted
10,000 unique repository-guided synthetic designs once (three target regressors,
329 features each), followed by its own dev1024/cal1024/test2048; total new labels
14,096. Fixed own-test tolerances passed at 2048/2048; MAE is 0.1191669481 nJ,
0.0233741876 fs and 0.0024745678 MW. This is not GMMNLSE accuracy or zero error.
Own q=0.0030957846673075884; joint coverage1942/2048, near_slice218/256, hence limited.

Old1024 and new10k metrics come from different tests, not a controlled sample-size
ablation. Historical V4.3 candidate improvements below still belong to V4.2.
No real-solver generalization/savings were measured. A 10,000-row pending MATLAB
plan and no-propagation short checks do not mean 10,000 GMMNLSE runs occurred.
All full datasets/plan/row metrics remain local; the UI imports only reviewed
inference assets and selected aggregate/history summaries. AppTest passed outside
the repository; browser visual inspection did not finish before the bounded server
closed. Public redistribution remains blocked pending file/data/license review.

The remaining sections describe the previous closeout and historical experiments.

This index separates three historical synthetic experiments from the retained
GMMNLSE backend. Closeout reads existing results; it does not create labels,
repeat test scoring, train, recalibrate, search or start MATLAB. The compact
[machine summary](../reports/local/mvp_closeout_001/evidence/evidence_summary.json)
contains source paths, SHA-256 identities and full numeric precision. Its
[README tables](../reports/local/mvp_closeout_001/evidence/readme_tables.md) are
generated from that serialized summary by
[export_mvp_evidence.py](../scripts/export_mvp_evidence.py), not maintained as
independent hand-entered metrics. Local evidence is ignored and is not an
automatically published dataset.

| Claim / status | Source and model / protocol | Sample and query scope | Original records and implementation | Limitation |
|---|---|---|---|---|
| V4.2 point predictions met the declared error tolerances on the saved test | `repository_guided_synthetic`; `T2_K64_A0001`; protocol `accuracy_v4_2_representation_001`; exact model SHA below | 1024 training designs; one new fixed-mixture 2048-design test; T1/T2 selection training union 1536, not 2048 independent labels | [final_metrics.json](../reports/local/accuracy_v4_2_001/evaluation/final_metrics.json), [protocol.json](../reports/local/accuracy_v4_2_001/protocol.json), [release selection](../reports/local/accuracy_v4_2_001/release/selection.json); [v42_experiment.py](../src/mamyshev_ml/v42_experiment.py) | MAE/P95 are nonzero. Passing tolerance is not “100% accurate,” whole-domain reliability, physical stability or GMMNLSE generalization. This test is not reopened during closeout. |
| V4.2 intervals remain `limited` | Same frozen model; original joint log-residual calibration, no recalibration | Historical joint coverage overall 1936/2048; near_slice 216/256; reference_core 467/512 | [calibration.json](../reports/local/accuracy_v4_2_001/evaluation/calibration.json), [final_metrics group_intervals](../reports/local/accuracy_v4_2_001/evaluation/final_metrics.json); [v43_adapter.py](../src/mamyshev_ml/v43_adapter.py) | Near-slice coverage is 84.375%; core is 91.2109375%. A diagnostic interval wholly on one side of a threshold is not a physical safety certificate. |
| Historical V4 cold-start GP/random experiments ran | Separate per-experiment GP; `v4_independent_search_v1`; original seeds 11/22/33 | Four scenarios × three paired seeds × two methods, each 64 logical evaluations including 16 initial queries; 1536 events, 1230 unique computations, 306 cache hits | [search_summary.json](../reports/local/accuracy_v4_001/search/search_summary.json), [frozen_search_protocol.json](../reports/local/accuracy_v4_001/search/frozen_search_protocol.json), [experiment_summaries.json](../reports/local/accuracy_v4_001/search/experiment_summaries.json); [v4_search.py](../src/mamyshev_ml/v4_search.py) | This is not a V4.2-model result. Three seeds and a finite evaluated pool do not establish universal superiority or a continuous optimum. No old trajectory is rerun. |
| V4.3 frozen-model candidates improved their common known synthetic incumbent in all four saved scenarios | Original V4.2 model, V4.3 candidate plan seed 43043 and recorded ranking rules | 1024-design T2 training prior; eight confirmations per method per scenario; 64 events / 63 unique designs / one cache hit | [frozen_candidate_plan.json](../reports/local/application_v4_3_001/candidates/frozen_candidate_plan.json), [candidate_results.csv](../reports/local/application_v4_3_001/candidates/candidate_results.csv), [candidate_summary.json](../reports/local/application_v4_3_001/candidates/candidate_summary.json); [v43_candidates.py](../src/mamyshev_ml/v43_candidates.py) | One seed; not a cold-start comparison or significance claim. Improvements divide by the shared T2 incumbent, not all historical results or the full pool optimum. S1–S3 maximize MW; S4 minimizes fs. Random retains its incumbent and did not get worse. |
| V4.3 prediction scans, database persistence and CSV/MAT export were exercised | Explicit frozen-model adapter, `surrogate_prediction`; `Prediction`, never `Evaluation` | Nine saved one-dimensional predictions and 81 saved heatmap predictions; zero labels for those scans | [demonstration/summary.json](../reports/local/application_v4_3_001/demonstration/summary.json), [curve exports](../reports/local/application_v4_3_001/demonstration/curve/export/), [heatmap exports](../reports/local/application_v4_3_001/demonstration/heatmap/export/); [v43_scan.py](../scripts/v43_scan.py), [v4_scan.py](../src/mamyshev_ml/v4_scan.py) | Predictions are synthetic-surrogate values without complex optical fields. Reading these records is replay, not a new live scan or real measurement. |
| MATLAB generation, four-dimensional single points, scan/resume/save/database/export routes are retained | Separate original/repaired GMMNLSE provenance, not the synthetic model | Existing component and historical single-run evidence only; new live full scan during closeout `not_run`; authorized attempts remain zero | [ACCURACY_FIRST_V4_REPORT.md](ACCURACY_FIRST_V4_REPORT.md), [PHASE2_CONFIG_AND_WAVEFORM_REPORT.md](PHASE2_CONFIG_AND_WAVEFORM_REPORT.md), [FROZEN_MODEL_APPLICATION_V4_3_REPORT.md](FROZEN_MODEL_APPLICATION_V4_3_REPORT.md); [pending requests](../reports/local/application_v4_3_001/candidates/requests/matlab_requests.json) | Functional availability does not validate the physical backend. H02, independent grid/window/step convergence and stability validation remain unresolved/deferred. Historical missing-final and timeout records are not repaired by closeout. |
| Real-solver generalization and real-simulation savings | `not_measured`, numeric values `null` in the compact summary | No matched validated real-solver training/test study or measured avoided simulations | The synthetic protocols above explicitly exclude this claim | Do not reuse old résumé examples (5000 GMMNLSE runs, R² .97, F1 .94, 70% savings) as measured project achievements. Synthetic 14.34 MW is an analytic-generator evaluation, not MATLAB or laboratory output. |

The exact frozen model SHA-256 is
`c236c2d2dd6cb5b59e32bd5ab4f8c3823f7fefc10d7571108a3d6339ee46b2e0`.
The V4.2 protocol SHA-256 is
`fb624723207ee5f864976e70d971c3400fc2309313bf0467623237a59644f1cb`.
The V4.3 candidate plan's internal hash is
`64932231e664c5a983130a72bce4a5bb5c64c11061c007192957c215e44a9daf`.
The summary separately records file-byte hashes; an internal plan hash and a
JSON file-byte hash are distinct identities. These hashes identify the local
trusted assets; they do not certify untrusted pickle files as safe.

## Label and cost accounting

Read `historical_cost_accounting` in the machine summary for exact source-ledger
wall times. These are historical external subprocess walls, not the user's
complete development time, per-label costs or GMMNLSE speedups. Rows overlap and
must not be added as if they were independent new datasets.

| Historical scope | Count and provenance |
|---|---|
| Early package pilot | Train 4096 / validation 1024 were already seen, recorded in [V4 selection](../reports/local/accuracy_v4_001/models/selection.json). |
| V4 local supervised development | 1349 unique train labels plus 1024 validation, eight fits; source is the same selection record. This partly reuses the pilot pool. |
| V4 one-time evaluation | Calibration 1024, test 1536, challenge 512; [evaluation summary](../reports/local/accuracy_v4_001/evaluation/summary.json). Challenge failures remain part of the evidence. |
| V4 cold-start searches | 1536 logical events / 1230 unique computations / 306 cached; separate search provenance, not extra V4.2 training. |
| V4.1 targeted development | New train 512 and dev 512, two fits; [summary](../reports/local/accuracy_v4_1_001/summary/summary.json). Previously used test/challenge remain historical diagnostics, not new labels. |
| V4.2 representation study | T1/T2 each 1024, union 1536; old reference validation 1024 plus special development 512; zero new train/dev, ten new fits and two reused candidates. New calibration 1024 and test 2048; [summary](../reports/local/accuracy_v4_2_001/summary.json). |
| V4.3 application | Fit/train/dev/calibration/test additions all zero; 64 candidate events / 63 new designs / one cache hit. The 1024-design training prior is inherited and cannot be omitted when describing search cost. |
| This closeout | New labels, fits, calibration, search, test scoring and MATLAB starts all zero. Limited prediction and artifact checks are reported separately in [MVP_CLOSEOUT_REPORT.md](MVP_CLOSEOUT_REPORT.md). |

## Existing figures

The exporter copies these four already-existing figures byte-for-byte; original
and destination hashes are in the machine summary. It does not redraw, smooth,
resample or alter results. They remain local review artifacts, not a publication.

| Figure | Original source | Interpretation |
|---|---|---|
| [Synthetic accuracy](../reports/local/mvp_closeout_001/evidence/figures/v42_accuracy.png) | [V4.2 saved test scatter](../reports/local/accuracy_v4_2_001/analysis/selected_test_scatter.png) | The saved fixed-mixture test, not a new evaluation. |
| [Representation comparison](../reports/local/mvp_closeout_001/evidence/figures/v42_representation.png) | [V4.2 saved comparison](../reports/local/accuracy_v4_2_001/analysis/energy_pass_comparison.png) | Development and training diagnostics; not independent test replications. |
| [Prediction heatmap](../reports/local/mvp_closeout_001/evidence/figures/v43_prediction_heatmap.png) | [V4.3 heatmap](../reports/local/application_v4_3_001/demonstration/heatmap/plots/compressed_peak_power_MW.png) | 81 surrogate predictions, no oracle labels or physical waveforms. |
| [Candidate confirmation](../reports/local/mvp_closeout_001/evidence/figures/v43_candidate_confirmation.png) | [V4.3 saved candidate comparison](../reports/local/application_v4_3_001/analysis/candidate_comparison.png) | Limited synthetic confirmation with shared incumbent and prior training. |

All physical-state assertions remain `undetermined`; numerical validation is
`not_verified`; eligibility as validated training truth is `false`. The local
MVP claim is a documented synthetic-benchmark prediction and application path
with a separately retained physics backend. Public release, real candidate
execution and subsequent research require separate authorization.
