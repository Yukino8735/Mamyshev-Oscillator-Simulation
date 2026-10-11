"""Calibrate and evaluate a previously frozen local model exactly once per output dir.
This script NEVER trains, chooses a model, changes thresholds or calls an oracle.
Only load a pickle/joblib model that you created and trust.
Usage: python reference/evaluate_frozen.py --model /trusted/model.joblib \
 --selection /path/selection.json --out /new/evaluation_dir --authorize-final-evaluation
selection.json must include model_sha256, accuracy_protocol_sha256, frozen=true.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
import joblib,numpy as np
from models_v4 import FEATURES,TARGETS
from metrics_v4 import report,joint_log_calibration,interval_report,accuracy_gate
ROOT=Path(__file__).resolve().parents[1]
def read(p):
    with p.open(newline='') as f:rows=list(csv.DictReader(f))
    x=np.array([[float(r[k]) for k in FEATURES] for r in rows]);y=np.array([[float(r[k]) for k in TARGETS] for r in rows])
    return rows,x,y

def run(model_path,selection_path,out,authorized):
    if not authorized:raise PermissionError('Final evaluation is explicit and follows a frozen selection.')
    selection=json.loads(selection_path.read_text());p=ROOT/'configs/accuracy_protocol.json'
    if not selection.get('frozen'):raise ValueError('Freeze selection before evaluating')
    if selection.get('model_sha256')!=hashlib.sha256(model_path.read_bytes()).hexdigest():raise ValueError('Model digest mismatch')
    if selection.get('accuracy_protocol_sha256')!=hashlib.sha256(p.read_bytes()).hexdigest():raise ValueError('Evaluation protocol mismatch')
    protocol=json.loads(p.read_text());out.mkdir(parents=True,exist_ok=False)
    (out/'selection_snapshot.json').write_text(json.dumps(selection,indent=2)+'\n')
    model=joblib.load(model_path) # Trusted local artifact only; never load user-untrusted pickle.
    rc,xc,yc=read(ROOT/'evaluation_only/calibration_1024.csv');pc=model.predict(xc);cal=joint_log_calibration(yc,pc,protocol['uncertainty']['alpha'])
    (out/'calibration.json').write_text(json.dumps(cal,indent=2,allow_nan=False)+'\n');result={}
    for name,filename in [('test','test_1536.csv'),('challenge','challenge_512.csv')]:
        rows,x,y=read(ROOT/'evaluation_only'/filename);pred=model.predict(x);rgn=np.array([r['region'] for r in rows]);overall=report(y,pred,protocol)
        groups={g:report(y[rgn==g],pred[rgn==g],protocol) for g in sorted(set(rgn))}
        item={'metrics':overall,'groups':groups,'intervals':interval_report(y,pred,cal),'claim':'synthetic benchmark only; no GMMNLSE accuracy claim'}
        if name=='test':item['accuracy_target_met']=accuracy_gate(overall,groups,protocol)
        from metrics_v4 import prediction_intervals
        low,high=prediction_intervals(pred,cal)
        # Fixed bin diagnostics; no tuning based on these post-freeze outputs.
        bins={};bounds=json.loads((ROOT/'configs/domain.json').read_text())['bounds']
        for j,k in enumerate(FEATURES):
            edges=np.linspace(*bounds[k],5)
            for z in range(4):
                mask=(x[:,j]>=edges[z])&((x[:,j]<=edges[z+1])if z==3 else(x[:,j]<edges[z+1]))
                bins[f'{k}_bin{z+1}']={'n':int(mask.sum()),'small_group':int(mask.sum())<protocol['small_group_minimum'],'metrics':report(y[mask],pred[mask],protocol)if mask.any() else None}
        item['input_bins']=bins
        masks={'duration_38_42':(y[:,1]>=38)&(y[:,1]<=42),'energy_95_105':(y[:,0]>=95)&(y[:,0]<=105)}
        item['threshold_bands']={k:{'n':int(v.sum()),'small_group':int(v.sum())<protocol['small_group_minimum'],'metrics':report(y[v],pred[v],protocol)if v.any()else None}for k,v in masks.items()}
        # Feasibility is a task constraint, NOT stability/physical classification.
        truth=y[:,1]<=40;point=pred[:,1]<=40;screen=high[:,1]<=40
        item['duration_constraint']={}
        for kind,m in [('point_estimate',point),('interval_screen',screen)]:
            proposed=int(m.sum());tp=int((m&truth).sum());positives=int(truth.sum())
            item['duration_constraint'][kind]={'proposed':proposed,'true_feasible':tp,'precision':tp/proposed if proposed else None,'recall':tp/positives if positives else None,'uncertain_count':int(((low[:,1]<=40)&(high[:,1]>40)).sum()),'note':'Interval screen is not a per-candidate guarantee under adaptive search.'}
        result[name]=item
        with (out/(name+'_predictions.csv')).open('x',newline='')as f:
            w=csv.writer(f);w.writerow(['design_id','region',*[k+'_truth' for k in TARGETS],*[k+'_prediction' for k in TARGETS],*[k+'_lower' for k in TARGETS],*[k+'_upper'for k in TARGETS]])
            for r,a,b,l,u in zip(rows,y,pred,low,high):w.writerow([r['design_id'],r['region'],*a,*b,*l,*u])
    (out/'final_metrics.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',type=Path,required=True);p.add_argument('--selection',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--authorize-final-evaluation',action='store_true');a=p.parse_args();run(a.model,a.selection,a.out,a.authorize_final_evaluation)
