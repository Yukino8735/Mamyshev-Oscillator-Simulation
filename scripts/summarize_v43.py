#!/usr/bin/env python3
"""Describe saved candidate verification; no fitting, predictions or new queries."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'reports/local/application_v4_3_001'
read = lambda path: json.loads(path.read_text())
plan = read(OUT/'candidates/frozen_candidate_plan.json')
summary = read(OUT/'candidates/candidate_summary.json')
events = [json.loads(line) for line in (OUT/'candidates/events.jsonl').read_text().splitlines()]
folder = OUT/'analysis'; folder.mkdir(exist_ok=False)
rows=[]
fig, axes = plt.subplots(2,2,figsize=(11,7.5))
for axis,scenario in zip(axes.flat,plan['scenarios']):
    name=scenario['id']; target=scenario['objective']['target']
    maximize=scenario['objective']['direction']=='maximize'
    inc=plan['common_incumbents'][name]['value']
    for method,color in (('model','#2369a3'),('random','#bd7125')):
        selected=[e for e in events if e['scenario_id']==name and e['method']==method]
        current=inc; track=[np.nan if current is None else current]
        for event in selected:
            if event['actual_feasible']:
                value=event['targets'][target]
                if current is None or (value>current if maximize else value<current): current=value
            track.append(np.nan if current is None else current)
        axis.plot(range(len(track)),track,marker='o',label=method,color=color)
        comparison=next(c for c in summary['comparisons'] if c['scenario_id']==name and c['method']==method)
        rows.append({**comparison,
            'directed_candidate_tolerance_passes': {k:sum(e['prediction_errors'][k]['tolerance_pass'] for e in selected if e['prediction_errors'])
                for k in ('compressed_energy_nJ','compressed_duration_fs','compressed_peak_power_MW')},
            'interval_relations': [e.get('constraint_diagnostics') for e in selected],
            'interpretation':'Directed confirmed candidates, not a new random test or statistically replicated search'})
    if inc is not None: axis.axhline(inc,color='#777777',linestyle=':',linewidth=1,label='shared T2 incumbent')
    axis.set_title(name); axis.set_xlabel('New logical queries (shared 1024-design trained model)')
    axis.set_ylabel(('Peak [MW]' if maximize else 'Duration [fs]')+'; actually evaluated synthetic')
    axis.grid(alpha=.2);axis.legend(fontsize=8)
fig.suptitle('Frozen-model application: best evaluated on synthetic, including shared training incumbent',fontsize=11)
fig.text(.5,.01,'One seed, eight queries per method/scenario; no global optimum, physical validation or BO claim.',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.04,1,.96));fig.savefig(folder/'candidate_comparison.png',dpi=140);plt.close(fig)
with (folder/'comparison.json').open('x') as stream: stream.write(json.dumps(rows,indent=2)+'\n')
table=['| 场景 | 方法 | 逻辑查询 | 可行数 | 预测假可行 | 共享既有最好 | 本批新评价最好 | 含既有的最好 | 相对既有改善 |',
       '|---|---|---:|---:|---:|---:|---:|---:|---|']
fmt=lambda x: 'null' if x is None else f'{x:.9g}'
for r in rows:
    table.append(f"| {r['scenario_id']} | {r['method']} | {r['logical_queries']} | {r['actual_feasible']} | {r['false_feasible']} | "
        f"{fmt(r['common_incumbent']['value'])} | {fmt(r['best_newly_evaluated']['value'])} | "
        f"{fmt(r['best_evaluated_on_synthetic']['value'])} | {r['candidate_goal_improved']} |")
(folder/'comparison_table.md').write_text('\n'.join(table)+'\n')
print(json.dumps({'read_only_saved_evidence':True,'new_queries':0,'new_predictions':0,
    'comparisons':len(rows),'plot':str(folder/'candidate_comparison.png')},indent=2))
