"""Explicit cheap V3 benchmark, not GMMNLSE and not a trained surrogate.
Python 3.11+, standard library only; no subprocess/MATLAB or global RNG calls.
"""
from __future__ import annotations
from bisect import bisect_right
from pathlib import Path
import hashlib, json, math
from typing import Mapping, Any
FEATURES=('pump_power_W','filter_offset_nm','filter2_bw_nm','gain_length_m')
TARGETS=('compressed_energy_nJ','compressed_duration_fs','compressed_peak_power_MW')
ROOT=Path(__file__).resolve().parents[1]
def load_recipe(path: Path|None=None)->dict:
 return json.loads((path or ROOT/'configs/generator_recipe.json').read_text())
def canonical(obj: Any)->str:
 return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False)
def design_id(design: Mapping[str,float])->str:
 d={k:float(design[k]) for k in FEATURES}
 return 'd_'+hashlib.sha256(canonical(d).encode()).hexdigest()[:24]
def validate(design: Mapping[str,Any],c:dict)->dict[str,float]:
 if set(design)!=set(FEATURES): raise ValueError('Exactly four design fields required.')
 d={}
 for k in FEATURES:
  v=design[k]
  if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v): raise ValueError(k+' must be a finite real number.')
  lo,hi=c['domain'][k]
  if not lo<=v<=hi: raise ValueError(k+' outside V3 benchmark domain.')
  d[k]=float(v)
 t=d['gain_length_m']/c['gain_length_step_m']
 if abs(t-round(t))>1e-9: raise ValueError('Gain length must be on the 0.1m grid; no implicit rounding.')
 return d
def log_curve(x:float,xs:list[float],ys:list[float],h:float)->float:
 """Linear-in-log interpolation; bounded endpoint slope extension."""
 logs=[math.log(y) for y in ys]
 if x<xs[0]:
  slope=(logs[1]-logs[0])/(xs[1]-xs[0])
  return logs[0]+slope*h*math.tanh((x-xs[0])/h)
 if x>xs[-1]:
  slope=(logs[-1]-logs[-2])/(xs[-1]-xs[-2])
  return logs[-1]+slope*h*math.tanh((x-xs[-1])/h)
 i=min(max(0,bisect_right(xs,x)-1),len(xs)-2)
 f=(x-xs[i])/(xs[i+1]-xs[i])
 return logs[i]+f*(logs[i+1]-logs[i])
def evaluate(design:Mapping[str,Any],recipe:dict|None=None)->dict[str,float]:
 c=recipe or load_recipe(); d=validate(design,c); a=c['scale_anchor']; r=c['reference_design']; q=c['assumed_coefficients']
 le=lt=0.; low=[]; high=[]
 for k in FEATURES:
  cr=c['curves'][k]; x=d[k]
  le+=log_curve(x,cr['x'],cr['energy'],cr['extension_scale'])-log_curve(r[k],cr['x'],cr['energy'],cr['extension_scale'])
  lt+=log_curve(x,cr['x'],cr['duration'],cr['extension_scale'])-log_curve(r[k],cr['x'],cr['duration'],cr['extension_scale'])
  l,h=c['historical_core_domain'][k]; dl,dh=c['domain'][k]
  low.append(max(0.,l-x)/(l-dl)); high.append(max(0.,x-h)/(dh-h))
 u=[(d[k]-r[k])/s for k,s in zip(FEATURES,q['normalized_input_scales'])]
 pl=u[0]*u[3]; db=u[1]*u[2]; pd=u[0]*u[1]
 le+=q['energy_cross_PL']*pl+q['energy_cross_DB']*db+q['energy_cross_PD']*pd
 lt+=q['duration_cross_PL']*pl+q['duration_cross_DB']*db
 le-=sum(a*x*x+b*y*y for a,b,x,y in zip(q['energy_outside_lower'],q['energy_outside_upper'],low,high))
 lt+=sum(a*x*x+b*y*y for a,b,x,y in zip(q['duration_outside_lower'],q['duration_outside_upper'],low,high))
 energy=a['compressed_energy_nJ']*math.exp(le); duration=a['compressed_duration_fs']*math.exp(lt)
 k0=a['compressed_peak_power_MW']*a['compressed_duration_fs']/a['compressed_energy_nJ']
 shape=k0*math.exp(-q['shape_cross_PL_squared']*pl*pl-q['shape_cross_DB_squared']*db*db)
 peak=shape*energy/duration # nJ/fs has the numerical units MW
 out=dict(zip(TARGETS,[energy,duration,peak]))
 if not all(math.isfinite(v) and v>0 for v in out.values()): raise ArithmeticError('Nonfinite/nonpositive synthetic result.')
 return out

def evaluation(design:Mapping[str,Any],recipe:dict|None=None)->dict:
 c=recipe or load_recipe(); d=validate(design,c)
 return {'design_id':design_id(d),'design':d,'backend_id':c['benchmark_id'],'source_kind':c['source_kind'],'targets':evaluate(d,c),'job_status':'completed','physical_state':'undetermined','numerical_validation':'not_verified','eligible_for_benchmark_ml':True,'eligible_as_validated_training_truth':False,'waveforms':None,'waveforms_missing_reason':'Scalar analytic benchmark; no complex field computed.'}
