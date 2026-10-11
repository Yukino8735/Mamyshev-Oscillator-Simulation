#!/usr/bin/env python3
"""Read saved V4.1 evidence and plot observed development rates; no inference."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from mamyshev_ml.v41_experiment import OUT, TARGETS, SPECIAL

out=OUT/'summary';out.mkdir(exist_ok=False)
selection=json.loads((OUT/'development/selection.json').read_text())
diagnosis=json.loads((OUT/'diagnostics/diagnostic_summary.json').read_text())
rows=[]
for record in selection['candidates']:
    groups={'reference_all':record['reference'],**record['reference_groups'],**record['new_dev_groups']}
    for group,values in groups.items():
        for target,item in values['targets'].items():
            rows.append({'candidate':record['name'],'n_train':record['n'],'group':group,'n':values['n'],
                         'target':target,'pass_rate':item['pass_rate'],'joint_pass_rate':values['joint_pass_rate'],
                         'MAE':item['mae'],'RMSE':item['rmse'],'R2':item['r2'],
                         'signed_mean':item['signed_mean'],'signed_relative_mean':item['signed_relative_mean'],
                         'P50_relative_abs':item['median_relative_error'],'P90_relative_abs':item['P90_relative_error'],
                         'P95_relative_abs':item['P95_relative_error'],'max_abs':item['max_absolute_error'],
                         'wilson95_lower':item['wilson95'][0],'wilson95_upper':item['wilson95'][1]})
with (out/'development_metrics.csv').open('x',newline='') as stream:
    w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
events=[json.loads(line) for line in (OUT/'oracle_queries.jsonl').read_text().splitlines()]
reserved={e['design_id'] for e in events if e['event']=='reserved'}
completed={e['design_id'] for e in events if e['event']=='completed'}
summary={'pipeline_completed':True,'development_accuracy_target_met':selection['development_accuracy_target_met'],
         'accuracy_target_met':False,'selected':selection['selected'],'best_diagnostic_candidate':selection['best_diagnostic_candidate'],
         'new_unique_oracle_designs_reserved':len(reserved),'new_unique_oracle_designs_completed':len(completed),
         'uncompleted_reservations':sorted(reserved-completed),
         'new_oracle_by_role':{r:sum(e['event']=='completed' and e['role']==r for e in events) for r in ('train','dev','calibration','test')},
         'old_training_labels_used':selection['old_unique_train_labels_used'],'old_validation_labels_used':selection['old_validation_labels_used'],
         'old_test_challenge_diagnostic_labels':2048,'new_candidate_fits':selection['fit_count'],
         'calibration_status':'not_run','test_status':'not_run','missing_reason':selection['stop_reason'],
         'unused_new_oracle_allowance':4096-len(reserved),'MATLAB_starts':0,'GMMNLSE_attempts':0,
         'physical_state':'undetermined','numerical_validation':'not_verified','eligible_as_validated_training_truth':False}
if selection['selected'] is not None:raise RuntimeError('This failure-summary route is not for a passed development candidate')
for name in ('evaluation','samples/calibration','samples/test','final_evaluation.lock'):
    if (OUT/name).exists():raise RuntimeError('Failed development must not consume holdout')
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
groups=['reference_all','historical_core','expanded_proposal',*SPECIAL]
fig,axes=plt.subplots(1,3,figsize=(15,6),constrained_layout=True)
for j,target in enumerate(TARGETS):
    values=np.array([[next(r['pass_rate'] for r in rows if r['candidate']==b and r['group']==g and r['target']==target)
                      for b in ('B0','B1','B2')] for g in groups])
    im=axes[j].imshow(values,vmin=0,vmax=1,cmap='viridis',aspect='auto')
    axes[j].set(xticks=range(3),xticklabels=['B0 (512)','B1 (1024)','B2 (1024)'],yticks=range(7),yticklabels=groups,title=target)
    for y in range(7):
        for x in range(3):axes[j].text(x,y,f'{100*values[y,x]:.1f}%',ha='center',va='center',color='white' if values[y,x]<.5 else 'black')
fig.colorbar(im,ax=axes,label='Empirical tolerance pass fraction')
fig.suptitle('Frozen V4.1 development comparison; no candidate passed all gates; not physical validation')
fig.savefig(out/'development_pass_rates.png',dpi=140);plt.close(fig)
print(json.dumps(summary,indent=2))
for candidate in selection['candidates']:
    print(candidate['name'], 'score',candidate['equal_group_normalized_rmse'])
    for g in groups:
        r=[row for row in rows if row['candidate']==candidate['name'] and row['group']==g]
        print(g, 'E/tau/peak',*[round(100*x['pass_rate'],6) for x in r], 'joint',round(100*r[0]['joint_pass_rate'],6))
