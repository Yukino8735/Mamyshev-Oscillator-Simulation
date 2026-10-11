"""Metrics and joint split-conformal intervals. No oracle, MATLAB or label lookup."""
from __future__ import annotations
import math
import numpy as np
TARGETS=('compressed_energy_nJ','compressed_duration_fs','compressed_peak_power_MW')

def arrays(y,p):
    y=np.asarray(y,float);p=np.asarray(p,float)
    if y.shape!=p.shape or y.ndim!=2 or y.shape[1]!=3 or len(y)==0:raise ValueError('Need matching, nonempty n-by-3 arrays.')
    if not (np.isfinite(y).all() and np.isfinite(p).all()):raise ValueError('Nonfinite values are not silently dropped.')
    return y,p

def wilson(k,n,z=1.959963984540054):
    if n<=0:return [None,None]
    phat=k/n;denom=1+z*z/n;c=(phat+z*z/(2*n))/denom;h=z/denom*math.sqrt(phat*(1-phat)/n+z*z/(4*n*n))
    return [max(0.,c-h),min(1.,c+h)]

def report(y,p,protocol):
    y,p=arrays(y,p);a=np.abs(p-y);tol=np.array([protocol['tolerances'][k]['absolute'] for k in TARGETS]);rel=np.array([protocol['tolerances'][k]['relative'] for k in TARGETS]);den=np.maximum(tol,rel*np.abs(y));r=a/den;passed=r<=1
    floor=np.array([protocol['relative_error_floor'][k] for k in TARGETS]);percent=a/np.maximum(np.abs(y),floor)
    out={'n':len(y),'targets':{},'joint_pass_rate':float(passed.all(axis=1).mean()),'joint_wilson95':wilson(int(passed.all(axis=1).sum()),len(y)),
         'mean_tolerance_normalized_rmse':float(np.sqrt(np.mean(r*r,axis=0)).mean())}
    for j,k in enumerate(TARGETS):
        ss=float(np.sum((y[:,j]-y[:,j].mean())**2));q=np.quantile(percent[:,j],[.5,.9,.95])
        out['targets'][k]={'mae':float(a[:,j].mean()),'rmse':float(np.sqrt(np.mean((p[:,j]-y[:,j])**2))),
          'r2':None if ss==0 else float(1-np.sum((p[:,j]-y[:,j])**2)/ss),
          'median_relative_error':float(q[0]),'P90_relative_error':float(q[1]),'P95_relative_error':float(q[2]),
          'max_absolute_error':float(a[:,j].max()),'relative_floor_used_count':int((np.abs(y[:,j])<floor[j]).sum()),
          'pass_rate':float(passed[:,j].mean()),'wilson95':wilson(int(passed[:,j].sum()),len(y)),
          'P95_tolerance_ratio':float(np.quantile(r[:,j],.95)),'median_tolerance_ratio':float(np.median(r[:,j]))}
    return out

def accuracy_gate(overall,groups,protocol):
    g=protocol['acceptance']
    return bool(all(v['pass_rate']>=g['each_target_pass_rate'] for v in overall['targets'].values())
        and overall['joint_pass_rate']>=g['joint_all3_pass_rate']
        and all(all(v['pass_rate']>=g['each_core_expanded_target_pass_rate'] for v in groups[s]['targets'].values()) for s in ('historical_core','expanded_proposal')))

def joint_log_calibration(y,p,alpha=.05):
    y,p=arrays(y,p)
    if np.any(y<=0) or np.any(p<=0):raise ValueError('Log calibration requires strictly positive truth and prediction.')
    if not 0<alpha<1:raise ValueError('alpha must lie in (0,1)')
    s=np.max(np.abs(np.log(y)-np.log(p)),axis=1);rank=math.ceil((len(s)+1)*(1-alpha))
    q=float(np.sort(s)[rank-1]) if rank<=len(s) else math.inf
    return {'n_calibration':len(s),'alpha':alpha,'rank':rank,'q_joint_log':q,'method':'joint_max_absolute_log_residual'}

def prediction_intervals(p,calibration):
    p=np.asarray(p,float)
    if p.ndim!=2 or p.shape[1]!=3 or not np.isfinite(p).all() or (p<=0).any():raise ValueError('Positive finite n-by-3 predictions required')
    q=calibration['q_joint_log'];return p*np.exp(-q),p*np.exp(q)

def interval_report(y,p,calibration):
    y,p=arrays(y,p);lo,hi=prediction_intervals(p,calibration);inside=(y>=lo)&(y<=hi);joint=inside.all(axis=1)
    return {'n':len(y),'per_target_coverage':inside.mean(axis=0).tolist(),'joint_coverage':float(joint.mean()),'joint_wilson95':wilson(int(joint.sum()),len(y)),
            'median_relative_interval_width':np.median((hi-lo)/p,axis=0).tolist(),
            'P95_relative_interval_width':np.quantile((hi-lo)/p,.95,axis=0).tolist(),
            'claim_scope':'Empirical coverage. Nominal guarantee needs exchangeable reference-distribution test points, not adversarial/optimized candidates.'}
