#!/usr/bin/env python3
"""Summarize saved twelve-slot and conditional evaluation records; no inference."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from mamyshev_ml.v42_experiment import ROOT,OUT,TARGETS

directory=OUT/'analysis';directory.mkdir(exist_ok=False)
records=json.loads((OUT/'development/comparison.json').read_text())
selection=json.loads((OUT/'selection.json').read_text());summary=json.loads((OUT/'summary.json').read_text())
rows=[]
for record in records:
    if record['status']!='completed':continue
    sets={'training':record['training'],'reference':record['reference'],**record['reference_groups'],**record['new_dev_groups']}
    for name,value in sets.items():
        for target,item in value['targets'].items():
            rows.append({'slot_id':record['slot_id'],'training_set':record['training_set'],'n_knots':record['n_knots'],
                'alpha':record['alpha'],'set':name,'n':value['n'],'target':target,'passed':item['passed'],
                'pass_rate':item['pass_rate'],'joint_passed':value['joint_passed'],'joint_pass_rate':value['joint_pass_rate'],
                'MAE':item['mae'],'RMSE':item['rmse'],'R2':item['r2'],'bias':item['signed_mean'],
                'relative_P50':item['median_relative_error'],'relative_P90':item['P90_relative_error'],
                'relative_P95':item['P95_relative_error'],'max_abs_error':item['max_absolute_error'],
                'P95_r':item['P95_tolerance_ratio'],'wilson_lower':item['wilson95'][0],'wilson_upper':item['wilson95'][1]})
with (directory/'all_metrics.csv').open('x',newline='') as stream:
    w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
valid={r['slot_id']:r for r in records if r['status']=='completed'}
effects=[]
for training in ('T1','T2'):
    for variable in ('knots','alpha'):
        pairs=[]
        if variable=='knots':
            for tag in ('A01','A0001'):
                pairs.extend((f'{training}_K{a}_{tag}',f'{training}_K{b}_{tag}') for a,b in ((16,32),(32,64)))
        else:pairs=[(f'{training}_K{k}_A01',f'{training}_K{k}_A0001') for k in (16,32,64)]
        for first,second in pairs:
            if first not in valid or second not in valid:continue
            a,b=valid[first],valid[second]
            effect={'training_set':training,'variable':variable,'from':first,'to':second,
                'delta_equal_group_score':b['equal_group_normalized_rmse']-a['equal_group_normalized_rmse'],'groups':{}}
            for group in ('training','reference','slice','near_slice','outer_faces','corners'):
                x=a[group] if group in a else a['new_dev_groups'][group]
                y=b[group] if group in b else b['new_dev_groups'][group]
                energy=TARGETS[0]
                effect['groups'][group]={'energy_RMSE_before':x['targets'][energy]['rmse'],
                    'energy_RMSE_after':y['targets'][energy]['rmse'],
                    'energy_pass_before':x['targets'][energy]['passed'],'energy_pass_after':y['targets'][energy]['passed'],
                    'n':x['n'],'joint_before':x['joint_passed'],'joint_after':y['joint_passed']}
            effects.append(effect)
(directory/'controlled_effects.json').write_text(json.dumps(effects,indent=2)+'\n')
groups=['training','reference','slice','near_slice','outer_faces','corners']
fig,axes=plt.subplots(2,3,figsize=(15,8),constrained_layout=True)
for ax,group in zip(axes.flat,groups):
    for training in ('T1','T2'):
        for alpha,tag,style in ((.1,'A01','-'),(.001,'A0001','--')):
            points=[]
            for k in (16,32,64):
                r=valid.get(f'{training}_K{k}_{tag}')
                if r is None:continue
                value=r[group] if group in r else r['new_dev_groups'][group]
                points.append((k,100*value['targets'][TARGETS[0]]['pass_rate']))
            if points:ax.plot(*zip(*points),style,marker='o',label=f'{training}, alpha={alpha}')
    ax.axhline(95,color='gray',ls=':',label='95% gate (not training)' if group=='training' else None)
    ax.set(title=group,xlabel='Uniform knots',ylabel='Energy tolerance pass (%)',xticks=[16,32,64],ylim=(-2,102))
    ax.grid(alpha=.25)
axes.flat[0].legend(fontsize=8)
fig.suptitle('Fixed-data representation comparison; training is fit diagnostics, development is reused')
fig.savefig(directory/'energy_pass_comparison.png',dpi=140);plt.close(fig)
print('selected',selection.get('selected'),'passing',selection.get('passing_slots'))
for r in records:
    if r['status']!='completed':print(r['slot_id'],r['status']);continue
    energy=TARGETS[0]
    print(r['slot_id'],'score',r['equal_group_normalized_rmse'],'pass',r['gate']['passed'],
          'trainRMSE',r['training']['targets'][energy]['rmse'],'trainE',r['training']['targets'][energy]['passed'],
          'refE',r['reference']['targets'][energy]['passed'],
          'sliceE',r['new_dev_groups']['slice']['targets'][energy]['passed'],
          'nearE',r['new_dev_groups']['near_slice']['targets'][energy]['passed'],'warnings',r['warnings'])
if (OUT/'evaluation/final_metrics.json').exists():
    final=json.loads((OUT/'evaluation/final_metrics.json').read_text())
    print('FINAL',json.dumps({'gate':final['gate'],'overall':final['metrics'],'reference':final['reference'],
        'intervals':final['intervals'],'constraints':final['constraints']},indent=2))
    for g,m in final['groups'].items():print('TESTGROUP',g,json.dumps(m))
    with (directory/'test_groups.csv').open('x',newline='') as stream:
        fields=['group','n','target','passed','pass_rate','joint_passed','joint_pass_rate','mae','rmse','r2','bias','P95_relative','P95_r','coverage','width_median','width_P95']
        w=csv.DictWriter(stream,fieldnames=fields);w.writeheader()
        for g,m in final['groups'].items():
            intervals=final['group_intervals'][g]
            for j,target in enumerate(TARGETS):
                t=m['targets'][target];width=intervals['width_original_units'][target]
                w.writerow(dict(group=g,n=m['n'],target=target,passed=t['passed'],pass_rate=t['pass_rate'],
                    joint_passed=m['joint_passed'],joint_pass_rate=m['joint_pass_rate'],mae=t['mae'],rmse=t['rmse'],r2=t['r2'],
                    bias=t['signed_mean'],P95_relative=t['P95_relative_error'],P95_r=t['P95_tolerance_ratio'],
                    coverage=intervals['per_target_coverage'][j],width_median=width['median'],width_P95=width['P95']))
    with (OUT/'evaluation/test_predictions.csv').open() as stream:saved=list(csv.DictReader(stream))
    fig,axes=plt.subplots(1,3,figsize=(13,4),constrained_layout=True)
    for ax,target in zip(axes,TARGETS):
        truth=np.array([float(r[target+'_truth']) for r in saved]);pred=np.array([float(r[target+'_prediction']) for r in saved])
        ax.scatter(truth,pred,s=5,alpha=.35);low=min(truth.min(),pred.min());high=max(truth.max(),pred.max())
        ax.plot([low,high],[low,high],'--',color='gray');ax.set(title=target,xlabel='Synthetic truth',ylabel='Frozen prediction');ax.grid(alpha=.2)
    fig.suptitle('One frozen selected-model test; fixed strata; no MATLAB/physical accuracy claim')
    fig.savefig(directory/'selected_test_scatter.png',dpi=140);plt.close(fig)
print('SUMMARY',json.dumps(summary,indent=2))
lines=['# Saved V4.2 numerical tables','',
       '| Slot | Features | Train E / tau / peak / joint (n=1024) | Reference E / tau / peak / joint (n=1024) | Six-group score | All development gates |',
       '|---|---:|---|---|---:|---|']
def counts(value):return '/'.join(str(value['targets'][t]['passed']) for t in TARGETS)+'/'+str(value['joint_passed'])
for r in records:
    if r['status']!='completed':lines.append(f"|{r['slot_id']}|null|{r['status']}|null|null|false|");continue
    lines.append(f"|{r['slot_id']}|{r['expected_features']}|{counts(r['training'])}|{counts(r['reference'])}|{r['equal_group_normalized_rmse']:.9f}|{r['gate']['passed']}|")
lines+=['','| Slot | Slice E/128 | Near E/128 | Faces E/128 | Corners E/128 | Train E bias / RMSE nJ | Reference E bias / RMSE nJ | Slice E bias / P95 abs-relative | Near E bias / P95 abs-relative |',
        '|---|---:|---:|---:|---:|---|---|---|---|']
energy=TARGETS[0]
for r in records:
    if r['status']!='completed':continue
    special=r['new_dev_groups'];train=r['training']['targets'][energy];ref=r['reference']['targets'][energy]
    sl,near=special['slice']['targets'][energy],special['near_slice']['targets'][energy]
    lines.append(f"|{r['slot_id']}|"+'|'.join(str(special[g]['targets'][energy]['passed']) for g in ('slice','near_slice','outer_faces','corners'))+
        f"|{train['signed_mean']:.6f} / {train['rmse']:.6f}|{ref['signed_mean']:.6f} / {ref['rmse']:.6f}|{sl['signed_mean']:.6f} / {100*sl['P95_relative_error']:.6f}%|{near['signed_mean']:.6f} / {100*near['P95_relative_error']:.6f}%|")
for training in ('T1','T2'):
    ins=json.loads((OUT/'development'/f'{training}_K16_A01'/'inspection.json').read_text())
    lines+=['',training+' X ranges: '+json.dumps(ins['train_X_ranges']),training+' solver: '+str(ins['targets'][energy]['ridge_fitted_solver'])]
if (OUT/'evaluation/final_metrics.json').exists():
    lines+=['','| Test group | n | E/tau/peak/joint passing counts | Joint interval coverage | E/tau/peak RMSE |',
            '|---|---:|---|---:|---|']
    for g,m in {'overall':final['metrics'],'reference':final['reference'],**final['groups']}.items():
        ci=final['intervals'] if g=='overall' else final['group_intervals'].get(g)
        coverage=f"{100*ci['joint_coverage']:.6f}%" if ci else 'see core/expanded'
        lines.append(f"|{g}|{m['n']}|{counts(m)}|{coverage}|"+'/'.join(f"{m['targets'][t]['rmse']:.8f}" for t in TARGETS)+'|')
    lines+=['','Calibration: '+(OUT/'evaluation/calibration.json').read_text(),'','Overall constraints: '+json.dumps(final['constraints'],indent=2),
            '','Group constraints: '+json.dumps(final['group_constraints'],indent=2),
            '','Overall intervals: '+json.dumps(final['intervals'],indent=2),'','Group intervals: '+json.dumps(final['group_intervals'],indent=2)]
(directory/'report_tables.md').write_text('\n'.join(lines)+'\n')
