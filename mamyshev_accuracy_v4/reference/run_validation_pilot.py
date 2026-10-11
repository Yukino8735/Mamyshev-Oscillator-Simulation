"""One fixed-configuration learning curve on DEVELOPMENT data only.
Does not open evaluation_only, oracle or generator_recipe.
No scientific final-test result or optimality claim is produced.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,platform,time,warnings
from pathlib import Path
import numpy as np,sklearn
from threadpoolctl import threadpool_limits
from models_v4 import FEATURES,TARGETS,LogSurrogate
from metrics_v4 import report,accuracy_gate
ROOT=Path(__file__).resolve().parents[1]
def rows(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))
def run(out,families,sizes,seed):
    out.mkdir(parents=True,exist_ok=False);t0=time.monotonic();protocol=json.loads((ROOT/'configs/accuracy_protocol.json').read_text());domain=json.loads((ROOT/'configs/domain.json').read_text())
    # Domain JSON is only metadata; it has no labels/curve coefficients.
    if 'bounds' in domain:domain=domain['bounds']
    elif 'domain' in domain:domain=domain['domain']
    train=rows(ROOT/'data/train_pool_4096.csv');val=rows(ROOT/'data/validation_1024.csv');lookup={r['design_id']:r for r in train}
    seq=json.loads((ROOT/'data/training_orders.json').read_text())['orders'][str(seed)];train=[lookup[i] for i in seq]
    x=np.array([[float(r[k]) for k in FEATURES] for r in train]);y=np.array([[float(r[k]) for k in TARGETS] for r in train]);xv=np.array([[float(r[k]) for k in FEATURES] for r in val]);yv=np.array([[float(r[k]) for k in TARGETS] for r in val]);regions=np.array([r['region'] for r in val])
    # Freeze files/parameters before any fit; only the requested prefix is used.
    freeze={'families':families,'sizes':sizes,'seed':seed,'protocol_sha256':hashlib.sha256((ROOT/'configs/accuracy_protocol.json').read_bytes()).hexdigest(),'train_sha256':hashlib.sha256((ROOT/'data/train_pool_4096.csv').read_bytes()).hexdigest(),'validation_sha256':hashlib.sha256((ROOT/'data/validation_1024.csv').read_bytes()).hexdigest(),'python':platform.python_version(),'sklearn':sklearn.__version__,'numpy':np.__version__,'scope':'development only; no calibration/test/challenge model scoring'}
    (out/'freeze.json').write_text(json.dumps(freeze,indent=2)+'\n');results=[]
    with threadpool_limits(limits=2):
        for n in sizes:
            for family in families:
                started=time.monotonic()
                with warnings.catch_warnings(record=True) as ws:
                    warnings.simplefilter('always');m=LogSurrogate(family,domain,protocol['models'].get(family,protocol.get('exploratory_models',{}).get(family)),seed).fit(x[:n],y[:n]);fit=time.monotonic()-started;p=m.predict(xv)
                overall=report(yv,p,protocol);groups={g:report(yv[regions==g],p[regions==g],protocol) for g in sorted(set(regions))};rec={'model':family,'n_train':n,'training_order_seed':seed,'fit_s':fit,'elapsed_s':time.monotonic()-started,'warnings':[str(w.message) for w in ws],'metrics':overall,'groups':groups,'accuracy_gate_passed':accuracy_gate(overall,groups,protocol)}
                results.append(rec);(out/'results.json').write_text(json.dumps({'freeze':freeze,'results':results,'elapsed_s':time.monotonic()-t0},indent=2)+'\n')
                print(family,n,'p95rel',np.round([v['P95_relative_error'] for v in overall['targets'].values()],4),'joint',round(overall['joint_pass_rate'],3),'gate',rec['accuracy_gate_passed'],'s',round(rec['elapsed_s'],3),flush=True)
                if n==4096 or n==512:
                    with (out/f'validation_predictions_{family}_{n}.csv').open('w',newline='') as f:
                        w=csv.writer(f);w.writerow(['design_id','region',*[k+'_true' for k in TARGETS],*[k+'_pred' for k in TARGETS]])
                        for r,a,b in zip(val,yv,p):w.writerow([r['design_id'],r['region'],*a,*b])
    return results
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--families',nargs='+',default=['ridge2','spline_interactions','hist_gb']);p.add_argument('--sizes',type=int,nargs='+',default=[256,512,1024,2048,4096]);p.add_argument('--seed',type=int,default=11);a=p.parse_args();run(a.out,a.families,a.sizes,a.seed)
