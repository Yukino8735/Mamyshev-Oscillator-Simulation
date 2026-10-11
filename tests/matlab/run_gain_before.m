% Original rollback defect with observation-only hook; deterministic fixture.
root = getenv('PHASE2_ROOT');
output_dir = getenv('PHASE2_OUTPUT_DIR');
addpath(fullfile(root,'tests','matlab'));
test_gain_rollback('reproduce',output_dir);
