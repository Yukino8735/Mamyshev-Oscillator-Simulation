#!/usr/bin/env python3
"""Curated aggregate evidence and existing figures, without any raw design table."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/local/demo_10k_release_001'
DEST=ROOT/'docs/assets/demo10k'

def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')

def main():
    DEST.mkdir(parents=True,exist_ok=False)
    old=read(ROOT/'reports/local/accuracy_v4_2_001/evaluation/final_metrics.json')
    new=read(OUT/'final_metrics.json') if (OUT/'final_metrics.json').exists() else None
    summary=read(OUT/'summary.json')
    artifact={'schema_version':'demo10k_public_aggregate_v1','source_kind':'repository_guided_synthetic',
        'historical_v42':{'model_id':'v42_T2_K64_A0001','n_train':1024,'test_n':2048,'metrics':old['metrics'],'intervals':old['intervals'],'group_intervals':old['group_intervals'],
           'original_metrics_sha256':sha(ROOT/'reports/local/accuracy_v4_2_001/evaluation/final_metrics.json')},
        'demo_10k':{'model_id':summary['model_id'],'n_train':summary['n_unique_fit'],'test_n':summary['role_label_counts']['final_test'],'model_sha256':summary['model_sha256'],
           'metrics':new['metrics'] if new else None,'groups':new['groups'] if new else None,'intervals':new['intervals'] if new else None,'group_intervals':new['group_intervals'] if new else None,
           'constraints':new['constraints'] if new else None,'accuracy_target_met':summary['accuracy_target_met'],
           'original_metrics_sha256':sha(OUT/'final_metrics.json') if new else None},
        'comparison_scope':'Different newly sampled final tests; not a common-holdout sample-size ablation',
        'real_solver_generalization':None,'real_simulation_savings':None,'missing_reason':'not_measured',
        'public_release_status':'blocked_pending_rights_and_user_approval','raw_rows_included':0}
    write(DEST/'aggregate_metrics.json',artifact)
    figures=[]
    for name in ('v42_accuracy.png','v42_representation.png','v43_prediction_heatmap.png','v43_candidate_confirmation.png'):
        source=ROOT/'reports/local/mvp_closeout_001/evidence/figures'/name
        dest=DEST/name
        with dest.open('xb') as f:f.write(source.read_bytes())
        figures.append({'filename':name,'source_kind':'saved_historical_synthetic_evidence','source_sha256':sha(source),'copy_sha256':sha(dest),'no_new_experiment':True,'attribution':'Project-generated figure; publication rights still under review'})
    write(DEST/'figure_provenance.json',{'figures':figures,'raw_training_or_test_data_included':False})
    lines=['| Version / saved experiment | Unique training designs | New test designs | Target | MAE | P95 absolute error | Within tolerance |', '|---|---:|---:|---|---:|---:|---:|']
    for key in ('historical_v42','demo_10k'):
        model=artifact[key]
        if model['metrics'] is None:continue
        for target,m in model['metrics']['targets'].items():
            lines.append(f"| {model['model_id']} | {model['n_train']} | {model['test_n']} | {target} | {m['mae']:.6g} {m['unit']} | {m['absolute_error_quantiles']['P95']:.6g} {m['unit']} | {m['passed']}/{m['n']} |")
    lines += ['', 'These are different fixed synthetic test sets. Meeting tolerances is not zero error, real-solver accuracy, or a controlled sample-size ablation. Both versions keep diagnostic intervals limited.']
    (DEST/'model_comparison.md').write_text('\n'.join(lines)+'\n')
    write(OUT/'public_evidence_build.json',{'outputs':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(DEST.iterdir())],
        'new_predictions':0,'new_labels':0,'test_rescored':False,'real_runs':0})
    print(json.dumps({'status':'saved_aggregates_exported','raw_rows':0,'figures':4}))

if __name__=='__main__':main()
