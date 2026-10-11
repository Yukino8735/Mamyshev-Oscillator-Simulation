# Execution status

## Current: bounded full-pipeline check passed; authorized code release

2026-10-11. The current publishing instruction and the owner's explicit
follow-up authorize publication of project-owned pipeline code with public
MATLAB live execution marked **blocked**. Four Cornell engine modifications
are excluded; prior remote history is retained. Exact publication receipts and
remote results are recorded in
[FULL_PIPELINE_GITHUB_RELEASE_REPORT.md](FULL_PIPELINE_GITHUB_RELEASE_REPORT.md).

The task-qualified training bridge and parameterized CLI now accept exact-source
DB/lossless CSV and design-group splits. Ten bridge tests, seven exporter tests
and fifteen related backend tests passed. One genuine saved parent final was
rechecked and exported through the same qualification boundary. A clean copy
completed one temporary release-smoke fit using 128 saved training and 16 saved
development designs: 329 features, scaler128, zero reload prediction difference.
No old held-out scoring or new labels. The exported single-10k Demo retains all
runtime/model bytes, with a one-point regression difference of zero.

Local full MATLAB/scan/resume/store/export functionality remains intact; its
public live route requires private exact initialization references and excluded
engine changes. The strict gate is preserved. New MATLAB/propagation/oracle,
10k retraining, calibration, BO and Cloud deployment are zero. Browser review
remains pending. Phase 2 stays in_progress; physical_state=undetermined,
numerical_validation=not_verified, eligible_as_validated_training_truth=false.
Earlier records below retain their original authorization and historical claims.

## Current: main-project Demo/export synchronization delivered; awaiting review

2026-10-11. `CODEX_PROJECT_DEMO_SYNC_PROMPT.md` authorizes the directly related
main-project UI/adapter/export/tests/docs work. The common single-10k runtime
already matched the reviewed deployment snapshot and was retained. The complete
main project is now the sole maintenance source, with `scripts/export_demo.py`
and public profile/templates in `demo/deploy/`. The old snapshot stays read-only.
The new independent `Mamyshev_Demo_Deploy_synced_001` contains 29 files / 677721
bytes; its manifest SHA-256 is
`519bf7b14f22f0e6e00efda775c47c9c8cca24663ac54d778ec9d36d2b5c6547`.

Seven export component methods passed. Three-way default/9-point/81-point
inference, q, interval and numeric export comparisons have maximum difference
0 at fixed atol=rtol=1e-10. Main and exported Demo checks each preserve six
actual chart spec/Arrow cases, current UI behavior and isolated session caches.
The two failed test-launch commands are retained, not counted as passed tests.
Historical/backend checks, actual total cost and preservation evidence are in
[PROJECT_DEMO_SYNC_REPORT.md](PROJECT_DEMO_SYNC_REPORT.md). AppTest is component
evidence; browser visual acceptance and publication remain pending.

Historical models, original q, complete MATLAB/scan/store/resume/export routes
and prior dirty work remain protected. The real-source `training_records`
eligibility gap described below remains open. No scientific validation status
is promoted: physical Phase 2 stays `in_progress/deferred`, with
undetermined/not_verified/false validated training-truth eligibility. This task
does not authorize training, labels, oracle, calibration, MATLAB, propagation,
browser/server startup, Git writes or deployment. This batch stops for review.
Earlier status entries below remain historical records.

## Current: real-simulation readiness reviewed; public Demo entry prepared

2026-10-11. User requested a gap review and a README showcase entry; user
confirmed that no public Demo URL exists. The README now links to
[DEMO_SHOWCASE.md](DEMO_SHOWCASE.md), explicitly marked deployment pending.
[REAL_SIMULATION_VALIDATION_PLAN.md](REAL_SIMULATION_VALIDATION_PLAN.md)
records current evidence, missing scientific gates and the next execution order.
38 existing authorization/cleanup/observation/waveform component methods passed.
Read-only audit of four historical real-run records and 15 evaluation SQLite
stores found zero eligible repaired-backend training rows in the inspected stores.
A tagged isolated fixture reproduced training_records accepting completed but
unvalidated real-source records; this gap is documented, not silently repaired.
Current ML roles remain synthetic-only. The old cleanup fix is present and
component-tested, but has no new real-run acceptance. H02, numerical convergence,
physical-state labels, real data splits and real model generalization remain open.
No MATLAB, real propagation, oracle, training, recalibration, server start,
Git publication or deployment performed. Historical data/model/code retained.
Evidence and backups: `reports/local/real_simulation_readiness_001/`.

## Current: main-repository Demo synchronized to single_10k_001

2026-10-11. The user's local synchronization request updates the Demo to the
completed deployment snapshot, with demo_10k_v1 as its only active model.
31 unit methods and actual inference/chart/UI/session component checks passed;
deployment-vs-main maximum numerical difference is 0. Complete research
evaluators/scans/DB/export, historical V4.2 assets and prior work are retained.
See [DEMO_MAIN_SYNC_REPORT.md](DEMO_MAIN_SYNC_REPORT.md) and
`demo/source_version.json`. Exact replaced files are backed up under ignored
`reports/local/demo_main_sync_001/`. Existing feature branch, HEAD and index
remain unchanged; no GitHub publication or cloud deployment performed.
Browser visual acceptance remains pending. No training, recalibration, oracle,
MATLAB or full propagation in this synchronization. Phase2 scientific status
remains deferred/in_progress, undetermined/not_verified/false truth eligibility.
Earlier records below describe their original batches and are preserved.

## Current: Demo chart padding fixed; actual browser review pending

2026-10-10. See [DEMO_CHART_RENDER_FIX_REPORT.md](DEMO_CHART_RENDER_FIX_REPORT.md).
Confirmed numeric top-level padding in actual serialized Streamlit specs;
normalized the same margins to an object and separated current table/export
from chart construction. Both models × 1D/2D × three targets preserve exact
predictions, CSV/JSON, Arrow data and summaries across the change. Five new
component methods and three directly affected old regressions passed; one
initial discovery-path failure is retained. Charged runtime 47.224673 s / 180 s.
No fitting, calibration, oracle, Evaluation, MATLAB, model/data/environment
changes or Git publication. Protected assets/source/history hashes unchanged.
Browser visual/console check and Node mechanism execution are not_run; no
browser or server was started. Code/components complete, waiting for the user's
existing browser refresh. Old physical Phase2 remains in_progress/deferred,
with undetermined/not_verified/false truth eligibility. Stop for review.

## Current: task-oriented Demo UX delivered; visual review pending

2026-09-28 UTC. See [DEMO_UX_REVIEW_REPORT.md](DEMO_UX_REVIEW_REPORT.md).
The explicit UX prompt authorized only frozen predictions and interface changes.

- Four task views now support explicit 10k example selection, same-model baseline
  comparison, per-condition diagnostics, finite X-only candidate ranking and up
  to three zero-allowance pending requests. Old catalog default remains V4.2.
- Parameter response uses true rect cells, numeric axis spacing, exact baseline
  and objective-best markers. Full-precision values drive rankings and exports;
  technical JSON is folded away from the main task.
- Five new fixture methods plus eight directly affected regressions passed once.
  First AppTest passed ten cases; static review then prompted three small fixes.
  Final outside-repository AppTest passed twelve distinct cases (ten repeats,
  two added), including 512-candidate and 441-cell actual prediction checks.
  UI/direct/CLI maximum difference is zero at fixed atol=rtol=1e-10.
- Runtime fit/oracle/Evaluation/MATLAB counters are all zero. No environment,
  scientific model, propagation or authorization code changed. Existing q,
  weights, model manifests and old evidence are retained.
- browser_visual_check=not_run. No browser-control calls or test servers started;
  no user service or unknown port was stopped. Desktop visual review is pending.
- Evidence and monitored budget: `reports/local/demo_ux_001/`. No Git staging,
  commit, push or publication. Stop for review; old physical Phase2 remains
  in_progress/deferred with undetermined/not_verified/false truth eligibility.

## Current: Demo and one 10k synthetic fit delivered; publication review pending

2026-09-28 UTC. See [DEMO_10K_RELEASE_REPORT.md](DEMO_10K_RELEASE_REPORT.md).
Earlier entries below retain their original batch identities.

- `demo_10k_v1` actually fitted 10,000 unique synthetic designs once; fresh
  train/dev/cal/test labels total 14,096. Fixed development and own final-test
  point gates passed. Own q and limited intervals are retained; old V4.2 weights,
  q, experiment records and default model remain unchanged.
- Data-independent Demo assets and four views passed outside-repository AppTest
  in the existing environment with no PYTHONPATH. The first chart-element assertion
  failure is preserved; corrected checker passed. No runtime fit/oracle/Evaluation/
  MATLAB calls. Browser visual check is not_run: the browser-control tool blocked
  for 2717.7581 s while the 120 s bounded localhost service closed automatically.
  This tool wait exceeds the 600 s engineering wall budget under a conservative
  inclusive interpretation; no further preview or component tests were started.
- Full pending MATLAB plan: 10,000 unique rows, null real targets, zero allowance.
  Recorded interrupt/resume/export and five existing authorization tests passed.
  One 40.075218 s MATLAB process checked four original-grid initializations plus
  32 already-generated formula labels. New real propagation/full scans: zero.
- Public-review aggregates/figures and exact-file Git checklist prepared. Tracked
  historical data and mixed license/private-path issues block publication.
  No git add/commit/push/untrack/history rewrite or remote check was performed.
- Old physical Phase2 remains in_progress/deferred; physical_state=undetermined,
  numerical_validation=not_verified, eligible_as_validated_training_truth=false.
  Stop for review; no further fitting, search, live scan or next phase authorized.

Evidence: `reports/local/demo_10k_release_001/`; only aggregate/curated assets in
`demo/assets/` and `docs/assets/demo10k/` are proposed for later rights review.

## Current: local MVP closeout delivered; awaiting review

2026-09-28 UTC. See [MVP_CLOSEOUT_REPORT.md](MVP_CLOSEOUT_REPORT.md).
All earlier status entries and failed/timeout evidence remain historical records.

- Frozen V4.2 model/custom class/domain/q copied without alteration into a small
  independently manifested local inference bundle; original strict release intact.
  Outside-repository extraction with the existing environment and no repo
  `PYTHONPATH` passed verify and limited prediction/readback checks. Three distinct
  old inputs, nine repeated prediction rows; maximum discrepancy from saved
  predictions `4.440892098500626e-16`, fixed atol/rtol `1e-10`.
- Seven new schema/integrity test methods and one reused zero-live authorization
  regression passed. Four CLI failure cases rejected before model/custom-class
  loading; there is no oracle/MATLAB fallback. This is component/delivery evidence,
  not a new physical or independent numerical validation.
- English README, Chinese guide, claim/evidence and attribution documents now
  distinguish V4.2 supervised results, historical cold-start V4 search and V4.3
  frozen application. Machine summary and four copied figures consume saved
  evidence only. Intervals remain `limited`; real-solver error/savings unmeasured.
- New labels, fits, recalibration, test rescoring, search, MATLAB and GMMNLSE starts
  are all zero in this batch. Existing MATLAB generation/scan/save/resume/database/
  export/recorded/live features are retained; new full live scans `not_run`.
- Revised synthetic ML MVP and local application delivery are complete at the
  stated scope. Entire old Phase2 remains `in_progress`, deep physical study
  `deferred`; physical state `undetermined`, numerical validation `not_verified`,
  eligible validated training truth `false`. GitHub/publication `not_authorized`.

Evidence: `reports/local/mvp_closeout_001/{bundle_build.json,inference_bundle.zip,
demo/result.json,evidence/evidence_summary.json,budget_ledger.json,preservation_check.json}`.
Stop and await review; no subsequent experiment or phase starts automatically.

## Current: V4.3 frozen-model application completed; awaiting review

2026-09-28 UTC. See [FROZEN_MODEL_APPLICATION_V4_3_REPORT.md](FROZEN_MODEL_APPLICATION_V4_3_REPORT.md).
Earlier current-status headings below are preserved historical entries.

- V4.2 point prediction retains its passed, fixed synthetic evaluation; weights,
  original selection, q, training IDs and default deployment are unchanged.
  Intervals remain `limited` (near_slice joint coverage216/256), not a95% safety guarantee.
- Explicit V4.2 adapter/CLI completed actual9-point and81-point prediction scans,
  Prediction-only database writes, all-target CSV/MAT readback and saved-prediction
  wiring checks at fixed atol/rtol1e-10. Evaluation count from these scans remains0.
- One seed43043 frozen candidate application completed:64 logical confirmations,
  63 new synthetic designs,1 same-source cache hit,0 failures. Model selection
  improved each scenario's shared T2 training incumbent; this small descriptive
  comparison is not cold-start BO, statistical superiority or physical validation.
- Twelve per-scenario requests (11 unique designs) were exported, all
  `pending_manual_approval`, `max_new_real_attempts=0`, `real_targets=null`.
- Twenty-three new component methods and18 affected existing regressions passed.
  Training/dev/calibration/test labels0, fits0, recalibration0, BO0, MATLAB0,
  GMMNLSE0 in this batch. Existing MATLAB generation/scan/save/database/export
  and recorded/live routes remain intact; no current full propagation was run.
- Old24 cold-start optimization experiments remain historical independent evidence.
  Phase2 deep physical validation is still `deferred/in_progress`;
  `physical_state=undetermined`, `numerical_validation=not_verified`,
  `eligible_as_validated_training_truth=false`. No next-phase work or Git publication.

Evidence: `reports/local/application_v4_3_001/summary.json`,
`demonstration/summary.json`, `candidates/frozen_candidate_plan.json`,
`candidates/candidate_summary.json`, `candidates/requests/`,
`budget_ledger.json`, `preservation_check.json`. Stop for review.

## Current: V4.1 targeted comparison finished; development target not met; awaiting review

2026-09-28 UTC. The user's final attached V4.1 instruction was executed as a
bounded incremental batch. See [ACCURACY_V4_1_TARGETED_REPORT.md](ACCURACY_V4_1_TARGETED_REPORT.md).
The earlier V4 delivery and failures below remain historical evidence.

- Old test/challenge diagnostics: no wiring inconsistency found in checked
  ID/X/Y, fitted transforms, inverse-log and batch/single/CLI adapter paths.
  Fixed P4/L4 energy has a systematic positive residual, not a 91% numerical error.
- Protocol frozen before new labels/fits. B0 original512 retained; B1 old1024;
  B2 old512 plus targeted512. New development512 independently sampled.
- All three fail at least one predeclared development gate. B2 fixes the exact
  slice development group but fails near-slice and original reference overall
  energy (94.824%). `selected=null`, `accuracy_target_met=false`; B2 is retained
  only as best diagnostic candidate, not promoted or certified.
- New synthetic oracle labels1024 (512 train +512 dev); calibration/test0,
  no final evaluation or new interval calibration. No automatic expansion.
- 31 new component methods and10 directly affected existing Python regression
  methods pass. One earlier discovery-path failure (0 tests) remains charged.
  Source/hash retention and git diff checks are recorded in the new evidence.
- MATLAB0, GMMNLSE0, BO0. Production physics, old scans/database/export and
  source-separated real routing remain intact; no environment or Git publication.
- Phase2 remains `in_progress`; deep physical validation / following phases are
  not completed. `physical_state=undetermined`, `numerical_validation=not_verified`,
  `eligible_as_validated_training_truth=false`. Stop for review.

Evidence: `reports/local/accuracy_v4_1_001/summary/summary.json`,
`development/selection.json`, `diagnostics/diagnostic_summary.json`,
`protocol.json`, `budget_ledger.json`, `preservation_check.json`.

## Current: accuracy-first V4 revision delivered; awaiting review

2026-09-28 UTC. The formal V4 prompt supersedes V1/V2/V3 and scan supplements.
See [ACCURACY_FIRST_V4_REPORT.md](ACCURACY_FIRST_V4_REPORT.md).

| V4 workstream | Actual status |
|---|---|
| Data integrity and MATLAB synthetic parity | completed; 8192 labels checked, 24 parity rows; original two strict floating/CSV byte tests still reported failed, unchanged toleranced checks pass |
| Model/size selection and reload | completed; fixed spline, n=512, all orders11/22/33 pass; order11 weights frozen and reload identical |
| Independent calibration and one final evaluation | completed; main test accuracy_target_met=true, joint pass94.08%; challenge joint65.04%, fixed-hardware energy8.59%, limitations retained |
| Independent four-scenario GP/random search | completed;24 sequences/1536 logical events/1230 unique computations;12 synthetic-evaluated candidates pending_manual_approval, real allowance0 |
| Generation/scan/save/database functionality | implemented and current synthetic/component acceptance completed; historical successful final/MAT imported read-only; new full real scans not_run |
| Current MATLAB execution | exactly2 short processes,16.682391459s;5 real initializations,0 propagation,0 full GMMNLSE |
| Physical/deep numerical validation | deferred; old Phase2 remains in_progress, not completed |
| Next phase / publication | not_started; stop for review |

`physical_state=undetermined`, `numerical_validation=not_verified`,
`eligible_as_validated_training_truth=false`. Real-solver prediction error and
wall-clock savings remain null/not_measured. The fixed synthetic labels are not
a reduced backend masquerading as original GMMNLSE truth.

New cleanup/parent-final protection is implemented and tested with owned short
Python/shell children and controlled errors. This does not determine the old OS
EPERM root cause: historical `observation_001` retains its failed runner and
missing final. All prior timeouts, reports, source identities and MATs remain.
Production physical/numerical updates were not changed in V4. No real scan,
candidate validation, retraining after holdout, next phase or Git publication
was performed. The branch and existing uncommitted work are preserved.

Final V4 evidence: 43 new component methods and 40 directly affected existing
Python regression methods passed (repeated runs not counted as independent).
The package's original 15 tests retain 2 exact-floating/CSV-byte failures, with
the unchanged declared numerical parity tolerance separately verified. Measured
totals including failed checks: engineering Python39.765384377s/300,
ML/prediction/search22.009272834s/900, MATLAB16.682391459s/180. Delivery audit
checked2281 original files: no unexpected changes/deletions; frozen model and
learning/search sources unchanged; git diff --check passed.

The chronological phase records below are preserved history. Their earlier
authorization statements describe those batches; the V4 instruction authorized
only the completed synthetic/component revision above.

## Historical status after waveform stationarity batch

Updated: 2026-09-27 local / 2026-09-28 UTC. Phase 2 waveform stationarity batch
finished: old six-round analysis, bounded observation controls, one real cold
start through round 20, and saved-MAT diagnostics. MATLAB returned normally, but
the monitor failed during process-group cleanup; runner is failed and the parent
final is missing. This failure is retained. Awaiting review; the sole observation
attempt is consumed. Earlier config_waveform_001, validation_002, validation_001
and all historical authorization/evidence records remain unchanged.

| Phase | Status |
|---|---|
| 0 — local environment and repository | completed |
| 1 — audit | completed — findings and bounded baseline recorded |
| 2 — backend | in_progress — 20-round waveform diagnosis finished; monitor cleanup/finalization failed; awaiting review, no further run authorized |
| 2B — optional reduced model | not_started; requires separate approval |
| 3 — dataset | not_started |
| 4 — ML | not_started |
| 5 — optimization | not_started |
| 6 — portfolio | not_started |
| 7 — publication | not_started; requires separate approval |

## Phase 2 waveform stationarity diagnosis and fixed 20-round observation

See [PHASE2_STATIONARITY_REPORT.md](PHASE2_STATIONARITY_REPORT.md).

- Analyzed the existing six-round pre/post-tracker complex MATs first. Integer
  periodic whole-window alignment uses the original 1.52587890625 fs spacing,
  with no amplitude normalization, smoothing, local warp or solver feedback.
  Round6 versus5 retains 2.28386% aligned intensity L2 and 2.66038% spectral L2.
  The original 4.54467% unaligned error and applied +6.103516 fs shift remain visible.
- Added separate fixed_roundtrips/20 observation options; design_config still
  has exactly four physical inputs. The same production initialization and loop
  retain the original energy criterion/H04 and legacy flags, bypass only
  convergence early exits in this mode, and preserve numerical/death/no-progress/
  STOP/timeout protection. Default legacy behavior and original max_rt50 remain.
  No propagation, material, filter, grid, tolerance, RNG or compressor changes.
- Nine artificial analysis groups and eight control groups passed, including one
  production initialization with no propagation. Existing convergence20,
  contract20 and wrapper11 groups passed. Python: 55 different methods passed
  (18 new,37 reused); development repeats do not count as independent tests.
- Exactly one observation_validation_001 / observation_001 cold start used
  default 4D inputs, seed0/twister, original Nt32768/50ps/max_rt50 and a 3600 s
  supervisor cap including30 s reserve. B passed256 actual configuration leaves;
  A/B/C observation options agree. Completed20 rounds,80 cavity segments,40 filter
  calls, then pigtail and the same original compressor analysis once at the endpoint.
  No pigtail/compressor was run at round6 before continuing.
- The old criterion first became true at6 and stayed true through20; both force
  flags remained false. The actual loop stop is observation_budget_reached,
  not stability convergence. Original converged=true and ML_state=1 remain
  descriptive legacy flags, never stable_single.
- MATLAB exited0 and wrote a completed candidate, but existing stop_owned raised
  PermissionError on SIGKILL during cleanup. Original runner is failed,
  cleanup_verified=false, CLI exit1, supervisor_error.json present, final_result.json
  absent. The parent never reached its candidate gate/merge/final commit. A later
  read-only ps found owned group23043 absent; this does not repair the original
  cleanup status. No retry, signal to unrelated sessions, gate bypass, source fix
  or candidate-to-final copy was performed. This run's final-chain integration
  acceptance is not_passed due to monitor cleanup/finalization failure.
- Full recorded counters are available as diagnostics: gain90146/48/90098,
  passive44867/40/44827, pigtail684/2/682 trials/rejections/advanced steps. All81
  segments balance and no active segment remains. Independent post-hoc pure gates,
  waveform hashes and seven candidate-only scalar checks pass; these do not mean
  the failed parent ran its gate or restore a successful final.
- Saved20 round MATs and one endpoint MAT. Offline analysis preserves
  missing_final/diagnostic_only:146 recomputation checks pass;7 comparisons to
  parent-final metrics remain not_verified. First6 pre/post complex fields and
  raw energies match config_waveform_001 exactly (all max errors0; grids exact)
  under the frozen tolerances, without alignment or old post-compressor RNG comparison.
- Fixed last-five window16–20 retains0.80352–2.84030% aligned adjacent intensity
  differences and0.50535–4.39690% spectral differences. Round20 versus fixed6
  retains2.37241% aligned intensity and3.37163% spectral difference. Energy-only
  stopping at6 is insufficient to establish waveform stationarity in this record;
  changes persist, but no stability/breathing/multipulse truth label is assigned.
  Per-round energies, peaks, shifts, raw/aligned/spectral differences, edge fractions,
  main-half-maximum regions and real-data figures are retained locally.
- Three serial MATLAB short/initialization/offline processes consumed
  57.70359037397429/300 s, each<180 s, all completed. Real monitor wall was
  2115.063928082993 s including failed cleanup; backend elapsed2104.935732 s.
  Parent-to-final time is null because no final was committed; separate cleanup
  duration and peakRSS remain unmeasured. Raw33 files total26175918 bytes.
- Frozen255-file identity c5f9d4bd61fa26a25d0b6f3bab4dc211252f2afcb51206b3693155f8fefe3505
  stayed unchanged during and after the attempt. Reports/local holds the new
  evidence, not public data. Final diff/old-file/raw-evidence preservation checks
  are recorded in stationarity_001/delivery_review.json. No environment change,
  branch switch, commit, push, further observation or next-phase work occurred.

Run packaging, the earlier six-round normal-return chain and the 4D entry remain
historical achievements; this batch adds waveform observations with an explicit
operational failure, not a validated training design. Next priority is to inspect
the existing cleanup EPERM/finalization interruption before any separately
authorized run, and separately plan numerical/random diagnostics of the residual
waveform changes. Neither was performed here. Phase2 stays **in_progress**;
physical_state=undetermined, numerical_validation=not_verified,
eligible_as_validated_training_truth=false. H02 remains unresolved. Phase2B/3
and later phases remain not_started. This batch is stopped awaiting review.

## Phase 2 four-dimensional configuration and waveform evidence (historical)

See [PHASE2_CONFIG_AND_WAVEFORM_REPORT.md](PHASE2_CONFIG_AND_WAVEFORM_REPORT.md).

- New run_mamyshev_config shares the original initialization and loop. Four
  explicit inputs reach actual gain/filter/fiber calls: pump_power_W=4,
  filter_offset_nm=10 (1040 minus SF2 center), filter2_bw_nm=3, gain_length_m=4.
  Legacy PumpPower/cw2 converts into this same parser. Unknown, conflicting,
  nonfinite and unsupported save-grid inputs fail; lengths are not rounded.
- Fixed passive 0.4/1.5/3.2 m and pigtail 0.2 m remain. Gain length changes
  actual total length/save allocation/initial t_rep; dynamic t_rep remains
  original. H02 still unresolved: declared passive MFD10.5 retains SR from5.95.
  No propagation algorithm, physical assumptions, resolution or stopping changes.
- Six no-propagation production initializations passed: legacy/default exact,
  then one input varied at a time. Eight configuration groups, five artificial
  waveform IO groups and ten artificial analysis groups passed. A first short
  process failed in the new analyzer's struct-array allocation after earlier
  checks had passed; its original failure was retained and locally corrected.
  Only affected analysis and wrapper components followed; six initializations
  were not repeated. Relevant existing capture/contract/wrapper regressions
  passed; H01/full third-party suites were not repeated.
- Python: 48 different methods passed (14 new, 34 existing); repeats do not
  increase independent counts. Old strict baseline gate remains; config requests
  verify actual A/B/C and inherited rules. Waveform paths/hashes/units/identity
  join the existing parent gate. STOP, one reservation and failure priority remain.
- Exactly one new cold start through config entry, seed0/twister, 32768 samples,
  50 ps and max_rt50; 1800 s supervisor budget including30 s reserve. Completed
  six rounds, pigtail and the original single compressor analysis. MATLAB exit0,
  candidate/runner/parent final completed; legacy_energy_convergence, not max_rt.
  256 actual configuration comparisons passed; all25 segments and12 filter calls
  complete. Gain 27374/18/27356, passive cavity13312/12/13300, pigtail719/2/717
  trials/rejections/advanced steps, exactly matching validation_002.
- Six round MATs preserve SF1 rejected pre/post-tracker complex fields and raw
  energy; final MAT holds returned output/pigtail and the actual same-call
  compressor field. Its energy is measured from that field, not upstream energy.
  Seven waveform MATs plus manifest are present; old missing fields remain missing.
- One offline MATLAB read produced 55 passing recomputation checks and three
  real-data figures; all15 frozen scalar/stop regressions against validation_002
  passed with exact common values. Actual before/after RNG states also match.
  Pre/post trapz energies are distinguished. Last-round intensity L2 change is
  about4.54%, despite the old small energy fluctuation; this is not stable_single.
- MATLAB short tests/initializations/offline analysis total49.38697491696803 s
  of300, across3 serial processes (one failed), each under180 s. Real external
  wall586.4352557079983 s, parent precommit586.5082124159671 s. RSS, separate
  cleanup time and exact final commit duration remain unmeasured/null. Raw19
  files total9,986,403 bytes. No claim of speedup from a single timing comparison.
- Source identity explicitly changed to244 files, digest
  54c9be5a5084b0f83735ad60f5c99233934b1d780e745ce0b5745f0b3b9d05bd;
  remained frozen during the real run. Historical evidence and original dirty
  worktree retained; no environment changes, scan, training, optimization or Git
  publication. Final git diff --check and hash-preservation review recorded locally.

Run packaging and the old single-point normal-return chain are completed; this
batch adds tested configuration routing and actual saved-waveform evidence.
The entire Phase 2 remains **in_progress**, awaiting review. No four-dimensional
physical domain, independent grid/window/step convergence or physical label is
validated: physical_state=undetermined, numerical_validation=not_verified,
eligible_as_validated_training_truth=false. This repeat is not an independent
design/training sample. Phase 2B/3 and later phases remain not_started. Stopped.

## Phase 2 explicitly authorized extended single attempt (historical)

See [PHASE2_EXTENDED_SINGLE_RUN_REPORT.md](PHASE2_EXTENDED_SINGLE_RUN_REPORT.md).

- New authorization allowed one validation_002 in single_validation_002, total
  supervisor cap 1800 s including the existing 30 s cleanup/finalization reserve.
  Added only restricted launcher batch/budget wiring plus its Python tests.
  Default old900 behavior, one reservation per batch, STOP and final rules remain.
- New launcher tests: 8 passed; reused Python supervisor regression: 17 passed.
  No MATLAB fixture/preflight was run. One dry-run verified new directory/budget;
  exactly one real cold start followed, with no retry or later computation.
- Source identity changed explicitly for scripts/run_mamyshev_once.py and new
  tests/test_once_launcher.py. Production MATLAB, physics configs, supervisor and
  process monitor are unchanged; old manifests/evidence were not rewritten.
- Actual B passed all 256 exact comparisons to the direct Phase 1 baseline.
  B, initial-field/grid summaries and full RNG state match validation_001 except
  run/time/source metadata. Original physics, resolution, tolerances and noise
  remain; dynamic t_rep and adaptive steps were not fixed.
- Completed 6 rounds (24 cavity segments), the 0.2 m pigtail and original
  compressor analysis; normal backend return observed. MATLAB exit0, runner
  completed/process_exit, candidate and parent final completed with
  legacy_energy_convergence; no STOP/deadline events. Cleanup verified.
- Gain counts 27374 trials / 18 rejects / 27356 advances; passive cavity totals
  13312 / 12 / 13300; pigtail 719 / 2 / 717. All 25 segments complete and balanced,
  no active segment; actual configuration/runtime/integrity gate passed.
- MATLAB external wall 1040.4727931660018 s; parent precommit 1040.5507749579847 s.
  Exact final commit duration, separate cleanup time and peak RSS were not measured.
  Raw artifacts: 11 files, 1443726 bytes; candidate/runner/final all present.
- This frozen single-point normal production return and final-record chain passed.
  Physical state remains undetermined, numerical validation not_verified, and
  eligible_as_validated_training_truth=false. Legacy ML_state=1 is not stable_single.
  H02 remains unresolved; one same-design repeat is not a new training design.

Phase 2 remains in_progress awaiting review. The additional attempt is consumed;
no third repaired attempt, scan, training, optimization, convergence experiment,
Phase 2B/3, environment change, commit or remote publication was performed.

## Phase 2 batch 4 single real attempt (historical)

See [PHASE2_SINGLE_RUN_REPORT.md](PHASE2_SINGLE_RUN_REPORT.md).

- The user's new batch-4 instruction authorized exactly one real attempt with
  the existing 900 s supervisor, including 30 s cleanup/finalization reserve.
  Launchprep final source identity matched across 230 files; branch/commit and
  original uncommitted work were retained. No source/configuration change or
  additional MATLAB preflight/fixture/test occurred.
- `validation_001` was reserved and MATLAB entered the repaired original backend.
  Actual B initialization passed 256 exact leaf comparisons to direct baseline_001.
  Original physics, grid, tolerances, noise and seed were preserved; t_rep evolved.
- Twenty cavity segments (five full round trips) returned normally. Round 6 gain
  was entered, then interrupted at the external budget boundary. Pigtail and
  compressor were not called. The final record's returned round count remains null;
  five completed rounds are separately supported by diagnostics/stdout.
- Completed gain subset: 23310 trials / 15 rejections / 23295 advances.
  Completed passive subset: 10977 / 10 / 10967. All 20 complete segments balance;
  active round-6 counts remain null/incomplete, so whole-run totals are unknown.
  Real gain rejections demonstrate this run traversed the H01 retry/rollback path,
  not the old baseline's rejection count or error and not independent validation.
- MATLAB exit -15; runner failed/timeout, cleanup_verified=true; top-level CLI exit1.
  Candidate absent. Parent final exists with timeout, all scientific values null,
  physical_state=undetermined, numerical_validation=not_verified, training=false.
  Complete-candidate gate was not evaluated; required_records_error=null is not pass.
- Measured MATLAB external wall 870.185940 s; supervisor precommit wall 870.331246 s.
  Exact through-commit wall, separate cleanup time and peak RSS were not measured.
  Original run artifacts: 10 files / 1331265 bytes. No additional measurement run.
- Normal full-cavity completion integration was not achieved (budget stop).
  Real entry/partial production observations and safe timeout-to-parent-final path
  were observed. No new numerical-error/config-gate/cleanup failure was established.
  No changes were made to gates or original runner/final records.

The sole attempt is consumed; no retry, budget extension or second run was made.
Phase 2 stays in_progress, awaiting review. H02 remains unresolved and physical
truth unvalidated. Phase 2B/3 and subsequent phases remain not_started. No scan,
convergence study, training, optimization, environment changes or Git publication.

## Phase 2 batch 3 evidence and gate (historical)

See [PHASE2_LAUNCHER_REPORT.md](PHASE2_LAUNCHER_REPORT.md).

- Implemented actual A/B/C snapshots and independent read-only scalar trial,
  rejection and advanced-step counters in the co-pump gain and passive paths.
  Default observer absence preserves the existing path. Real mode rejects
  injected component backends and all active test_hook fields, including []/false.
- Exactly one full legacy initialization returned before any propagation.
  Nt=32768, 50 ps and max_rt=50 preserved; 256 leaf comparisons against direct
  baseline_001 configuration passed. RNG unchanged. No cavity candidate written.
  Full legacy runtime C observations remain deferred_to_authorized_run.
- Implemented single-attempt supervisor, owned process-group cleanup, STOP,
  monotonic 900 s real-mode budget and parent-only safe_result_v1 finalization.
  Real completion requires valid identity plus actual complete configuration,
  runtime records/counters and file integrity. Timeout/cancel cannot be erased
  by success candidates or zero exit. --dry-run was executed; --execute-real was not.
- Component evidence: observer 5 groups, capture 14 groups, repeated H01/H04/
  wrapper/result-contract 62 groups; Python 30 methods (11 old + 19 new) passed.
  Actual MATLAB synthetic candidate-to-parent-final case passed, then repeated
  after final missing-field contract strengthening. These are not cavity runs.
- Seven serial MATLAB processes: measured finalized time 85.766570 s, plus
  conservative 180 s charge for one unfinalized cleanup-permission failure:
  total budget debit 265.766570/600 s, per-process cap 180 s. Its 12 assertions
  passed, but its process outcome remains failed/unfinalized, not success.
  Original runner evidence retained; external group-absence reconciliation is
  separate. Cleanup now accepts EPERM only after confirming the owned group
  is absent; otherwise propagates failure. Another Python fixture path error
  was corrected and its original failure log retained.
- Prior Phase 1/repair/readiness evidence preserved (384 files, same hashes).
  Existing worktree changes retained. No environment installs or global changes,
  full cavity, scan, training, optimization, commit, push, PR or merge.

`runtime_observability_ready=true`, `supervisor_finalization_ready=true`,
`ready_to_request_single_run=true` indicate component readiness to request
separate authorization. They are not a physics validation or permission to run.
H02 legacy conventions remain frozen/unvalidated; physical_state=undetermined,
numerical_validation=not_verified, training eligibility=false. Full-cavity
integration and random-rejection protocol remain unverified. Phase 2 remains
in_progress, waiting for review; Phase 2B/3 and later phases have not started.

## Phase 2 batch 2 evidence and gate (historical)

See [PHASE2_INTEGRATION_READINESS.md](PHASE2_INTEGRATION_READINESS.md).

- Actual production co-pump loop reached z=0.001 m with nonempty 32-element
  a5. Two controlled rejected trials changed the pump; retry-start leakage
  was zero. Final small-step field/a5/pumps/N2 matched the original kernel
  started from that captured state exactly. This is a component comparison.
- Three 0.004 m synthetic gain segments returned normally, including saved
  initial/final outputs; no-hook and pure-observer outputs matched exactly.
  The numerical engine and original fixture were not changed in this batch.
- Fixed swallowed wrapper exceptions: write the failed candidate, then
  rethrow; write failures propagate. Eleven explicit synthetic wrapper cases
  passed, and a separate uncaught fixture error caused MATLAB exit 1 with
  failed candidate and parent process record. Default cavity path was not run.
- Repeated H01/H04/result-contract checks passed. Historical Phase 1 numerical
  identity remains legacy_pre_repair_phase1 after JSON round-trip.
- Two serial MATLAB short-test processes used 23.465726 s of a fresh 600 s
  budget (each below 180 s), including the expected exit-1 process. Final
  Python suite: 11 passed (9 existing + 2 new). Full-cavity runs: **0**.
- The 1-attempt / 900 s proposal is for review only. Runtime-resolved parameter
  snapshots/read-only step counters and supervisor final-result merging still
  require wiring and component tests before execution. The short-test CLI is
  not the proposed full-cavity launcher.

Batch 2 is complete, waiting for review. Phase 2 remains in_progress. H02
physical conventions, independent numerical convergence, random-rejection
semantics and physical-state labels remain unverified; training eligibility
remains false. No Phase 2B/3, full cavity, scan, training, optimization, commit,
push, PR or merge. Do not automatically start the proposed validation run.

## Phase 2 batch 1 evidence and gate (historical)

See [PHASE2_REPAIR_REPORT.md](PHASE2_REPAIR_REPORT.md) for the Chinese repair
report, source lines, before/after evidence, exact test boundaries and remaining work.

- H01 original defect reproduced through real production gain trial logic:
  rejected-trial pump leakage was -0.000915418915651 W. Minimal pump rollback
  reduced retry-start leakage to zero; deterministic full-state small-step and
  no-rejection controls matched exactly. A narrow non-progress retry guard is
  tested; random rejection semantics and broader retry protection remain open.
- H04 original safety expectations failed for NaN/Inf energy and nonfinite
  field. The repaired production helper passed 20 cases, uses explicit completed
  history, and reports structured numerical errors without physical labels.
- Safe result/JSON contract passed 20 cases; physical_state remains undetermined,
  independent numerical validation remains not_verified, and compressed energy
  and field remain null with reasons. The full-cavity wrapper was not invoked.
- H02 legacy identity is frozen separately from numerical and result-protocol
  versions. Passive declared MFD=10.5 um still has SR derived from 5.95 um.
  No physics parameter, filter rule, noise default, grid or tolerance was changed.
- Three serial MATLAB short-test processes used 30.349815 s total of 600 s,
  each below 180 s. Full-cavity runs: **0**. Final Python tests: 9 passed.
- Original-defect expected failures and repaired passes are recorded separately
  in ignored reports/local/phase2/repair_001/. Phase 1 artifacts and unrelated
  existing user files were preserved; only the explicit repair allowlist changed.

Batch 1 is complete; the user subsequently authorized only batch 2 above. The backend is still not validated training
truth. Phase 2 is not complete; no further cavity run, Phase 2B, Phase 3, scan,
training, optimization, commit or push was performed. Further computation needs
the user's separate next-batch confirmation.

## Phase 1 evidence and gate (historical)

Phase 1 completed on 2026-09-27. See [AUDIT.md](AUDIT.md) and
[BASELINE_REPORT.md](BASELINE_REPORT.md) for Chinese findings, source lines,
measured outputs, costs, and limitations.

- Two physical attempts, 714.324 s and 800.070 s, total 1514.394 s (25 min 14 s).
  Both returned at 6 round trips under the original energy convergence rule,
  with exit code 0. No physical timeout, scan, training or optimization.
- The first used a logged copy preserving the original numerical/physical
  statements; the second directly called original `run_mamyshev(4,1030,false)`.
  Same RNG seed; output/pigtail complex fields and compared metrics matched
  exactly. This is repeatability, not independent numerical validation.
- Legacy returned values: rejected-port 128.722091 nJ and 6.405640 ps;
  after pigtail + compressor analysis, 29.868593 fs and 2.778735 MW.
  These remain unvalidated numerical outputs, not performance claims.
  Both run records retain `physical_state=undetermined` despite legacy ML_state=1.
- Independent, non-propagating fixtures confirmed energy/FFT normalization and
  implemented filter behavior, and reproduced NaN acceptance / inability to
  distinguish equal-energy single/double fields in the convergence function.
- The memory probe silently parsed the `1` in `zsh:1: command not found: free`
  into a 0.5-byte memory limit. Current adaptive runs do not use this field.
- Confirmed source concerns: passive MFD/SR mismatch (3.11419 ratio), missing
  pump rollback after rejected gain steps, energy-only labels, mixed output
  planes and warning suppression. No physical-source fixes were made.
- Historical arrays, trend-guided data, failed/processed records and existing
  reproduction outputs were separated from these two new physical attempts.
- Local commands, configs, representative fields, logs and machine records are
  in ignored `reports/local/phase1/`. All 192 snapshotted code/support files
  retained identical hashes. Existing user work and branch were preserved.

The audit and bounded-run phase is complete. Stable-single classification,
time/grid/step convergence, independent pump-update verification and different
seed robustness remain unverified. These block use as trustworthy training
labels, not completion of this audit. The user subsequently authorized only
Phase 2 batch 1; its evidence and current gate are recorded above.

## Phase 0 evidence

- Local macOS 26.6.2, Darwin 25.6.0, arm64, model Mac15,12, 16 GiB RAM.
- Verified repository: `Yukino8735/Mamyshev-Oscillator-Simulation`.
  Started at `main` / `489bf42`; now on local `feature/mamyshev-ml-mvp`.
- Read all Markdown planning files and the environment bootstrap template.
  No existing repository/ancestor AGENTS.md was found. Execution status, scope,
  root environment.yml and pyproject.toml were also absent before this phase.
- Used the existing Miniforge, Conda 26.3.2. Created `mamyshev-ml` with only
  Python 3.11 and pip requested, plus their resolver-selected dependencies.
  The shared [environment specification](../environment.yml) has no prefix.
- Actual Python: 3.11.16, arm64; pip 26.2.1 resolves inside the same environment.
  Full installed Conda builds are in
  [the osx-arm64 package manifest](environment.osx-arm64.explicit.txt).
  No pip packages were separately installed; the project was tested from source.
- MATLAB R2025a Update 1 (`25.1.0.2973910`), `maca64`: batch startup exited 0,
  and `license('test','MATLAB')` returned 1. MATLAB is installed despite being
  absent from PATH. Project toolboxes and the GMMNLSE backend remain untested.
- Two standard-library unittest checks passed: runtime configuration agrees
  with the actual environment; incompatible environment/version is rejected.
- `git diff --check` passed. Original untracked files (including planning and
  reproduction scripts) passed SHA-256 comparison. Existing environment
  transaction histories and shell/Conda configuration hashes are unchanged.
- Initial sandbox-only RAM reads and `conda run` failed permission checks.
  Specific escalated operations succeeded without sudo or permission changes.
  The failed sandbox `conda run` attempts never started Python or the tests.
- Private paths, exact diagnostic commands and observed output are stored in
  ignored `reports/local/phase0-commands.md` and `phase0-python.json`.

## Phase 0 checks (historical record)

Run from the repository root on this machine:

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python -m unittest discover -s tests -v
```

At the end of Phase 0, no physics simulations, convergence checks, MATLAB project integration tests,
ML training, packaging installation test, Git commit or push were performed.
MATLAB startup is not evidence that the physics backend is validated.
No Phase 0 blocker remained. The user subsequently authorized Phase 1; its
results and the subsequently authorized Phase 2 batch 1 are recorded above.
Await review before any further Phase 2 work.

## Latest appended result: V4.2 representation comparison finished; awaiting review

2026-09-28 UTC. This entry records the subsequently authorized V4.2 batch;
all earlier entries, including their former current-status headings, are retained
as history. See [ACCURACY_V4_2_REPRESENTATION_REPORT.md](ACCURACY_V4_2_REPRESENTATION_REPORT.md).

- Fixed T1/T2 each contain 1024 training designs, with a unique union of1536.
  Existing reference validation1024 and special development512 were reused.
  New training/development labels0. Twelve representation/alpha slots completed:
  two reused old weights and ten fitted new candidates; eight passed every
  development gate. The unique selection is `T2_K64_A0001`.
- After selection, one new independent calibration1024 and test2048 were
  evaluated, totaling3072 unique synthetic labels. All2048 test points pass
  each target's fixed tolerance and the joint tolerance; `accuracy_target_met=true`.
  This concerns repository-guided synthetic labels, not real-solver accuracy.
- Interval joint empirical coverage is94.53125% overall and84.375% in near_slice.
  Point-accuracy success therefore does not establish95% coverage in every group
  or guaranteed feasibility. No post-test retraining, recalibration or expansion.
- A separately loadable, identity-checked candidate is retained in
  `reports/local/accuracy_v4_2_001/release/`; `deployment_replaced=false`.
  Old defaults and V4/V4.1 evidence remain preserved.
- Thirty new component methods and ten directly related existing Python
  regression methods pass. MATLAB0, GMMNLSE0, BO0; production physics and
  MATLAB generation/scan/save/database/export routes are unchanged.
- Phase2 remains `in_progress`; physical/deep numerical validation remains
  deferred. `physical_state=undetermined`, `numerical_validation=not_verified`,
  `eligible_as_validated_training_truth=false`. No next phase or Git publication.

Evidence: `reports/local/accuracy_v4_2_001/protocol.json`, `selection.json`,
`summary.json`, `evaluation/final_metrics.json`, `budget_ledger.json`,
and `preservation_check.json`. This batch ends here, awaiting review.
