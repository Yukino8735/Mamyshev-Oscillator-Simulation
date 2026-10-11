"""Rebuild V4 tables from immutable V3 formula and supplied legacy inputs.
No MATLAB/solver invocation. Refuses to overwrite existing generated files.
Usage: python reference/build_release.py --out /new/output/directory
"""
from __future__ import annotations
import argparse,csv,hashlib,itertools,json,math,random,sqlite3,time
from collections import Counter
from pathlib import Path
from oracle import ROOT,FEATURES,TARGETS,load_recipe,evaluate,validate,design_id

def read_csv(p):
    with Path(p).open(newline='') as f:return list(csv.DictReader(f))
def write_csv(p,rows,columns):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)
def in_core(d,c):return all(a<=d[k]<=b for k,(a,b) in c['historical_core_domain'].items())
def lhs(n,b,rng):
    axes=[]
    for k in FEATURES[:3]:
        a,z=b[k];v=[a+(z-a)*(i+rng.random())/n for i in range(n)];rng.shuffle(v);axes.append(v)
    a,z=b['gain_length_m']; ticks=list(range(round(a*10),round(z*10)+1));rng.shuffle(ticks)
    lengths=[ticks[i%len(ticks)]/10 for i in range(n)];rng.shuffle(lengths)
    return [dict(zip(FEATURES,[round(axes[j][i],6) for j in range(3)]+[lengths[i]])) for i in range(n)]
def build(out:Path):
    t=time.monotonic();c=load_recipe();out.mkdir(parents=True,exist_ok=True)
    legacy=json.loads((ROOT/'provenance/v3_design_ids.json').read_text())
    used=set(itertools.chain.from_iterable(legacy.values()));used.add(design_id(c['reference_design']))
    for r in read_csv(ROOT/'provenance/oracle_parity_cases_24.csv'):
        used.add(design_id({k:float(r[k]) for k in FEATURES}))
    rows=[];order=Counter();old_heldout=set(legacy['test_256.csv']+legacy['boundary_test_128.csv'])
    for role,filename in [('train','train_pool_512.csv'),('validation','validation_128.csv')]:
        for r in read_csv(ROOT/'provenance'/filename):
            for k in FEATURES+TARGETS:r[k]=float(r[k])
            r['order_in_role']=int(r['order_in_role']);r['release_id']='mamyshev_accuracy_v4';r['origin']='v3_preserved'
            rows.append(r);order[role]+=1
    def append(d,role,region=None):
        order[role]+=1
        r={'design_id':design_id(d),'role':role,'order_in_role':order[role],
           'region':region or ('historical_core' if in_core(d,c) else 'expanded_proposal'),
           **d,**evaluate(d,c),'source_kind':c['source_kind'],'backend_id':c['benchmark_id'],
           'release_id':'mamyshev_accuracy_v4','origin':'v4_new'}
        rows.append(r)
    def take_lhs(n,core,rng):
        result=[];b=c['historical_core_domain'] if core else c['domain']
        while len(result)<n:
            for d in lhs(max(32,n-len(result)),b,rng):
                if not core and in_core(d,c):continue
                did=design_id(d)
                if did in used:continue
                used.add(did);result.append(d)
                if len(result)==n:break
        return result
    rng=random.Random(20261001)
    for role,total in [('train',4096),('validation',1024)]:
        while order[role]<total:
            batch=take_lhs(32,True,rng)+take_lhs(32,False,rng);rng.shuffle(batch)
            for d in batch:append(d,role)
    # Independent common reference mixture for calibration and main test.
    # Exclusion is fixed by prior rows/legacy candidates; no within-pool redraw.
    prior_used=set(used);pair=[];rng_iid=random.Random(20261002)
    def draw_iid():
        core=rng_iid.random()<0.5;b=c['historical_core_domain'] if core else c['domain']
        while True:
            d={k:round(rng_iid.uniform(*b[k]),6) for k in FEATURES[:3]}
            a,z=b['gain_length_m'];d['gain_length_m']=rng_iid.randint(round(a*10),round(z*10))/10
            if core or not in_core(d,c):break
        return d
    while len(pair)<2560:
        d=draw_iid()
        if design_id(d) in prior_used:continue
        pair.append(d)
    if len({design_id(d) for d in pair})!=len(pair):raise RuntimeError('IID calibration/test collision: new release seed needed, do not silently deduplicate.')
    for i,d in enumerate(pair):
        used.add(design_id(d));append(d,'calibration' if i<1024 else 'test')
    # Stress is design-only selection; it is NOT drawn from reference mixture.
    # 256 outer-boundary points, 128 exact hardware slice, 128 corner neighborhoods.
    boundary=[]
    # Original V3 corners already excluded. The new face sample avoids old held-outs.
    rng_s=random.Random(20261003)
    while len(boundary)<256:
        d=lhs(1,c['domain'],rng_s)[0];j=len(boundary)%4;side=(len(boundary)//4)%2
        d[FEATURES[j]]=float(c['domain'][FEATURES[j]][side]);did=design_id(d)
        if did in used:continue
        used.add(did);boundary.append(d)
    for d in boundary:append(d,'challenge','outer_boundary')
    count=0
    while count<128:
        d=lhs(1,c['domain'],rng_s)[0];d.update(pump_power_W=4.0,gain_length_m=4.0);did=design_id(d)
        if did in used:continue
        used.add(did);append(d,'challenge','fixed_P4_L4');count+=1
    count=0
    while count<128:
        d={}
        for j,k in enumerate(FEATURES):
            lo,hi=c['domain'][k];side=(count//(2**j))%2
            if j<3:
                u=rng_s.random()*0.05;d[k]=round(lo+(hi-lo)*(u if side==0 else 1-u),6)
            else:
                ticks=list(range(round(lo*10),round(hi*10)+1));span=max(1,math.ceil(.05*len(ticks)))
                choices=ticks[:span] if side==0 else ticks[-span:];d[k]=rng_s.choice(choices)/10
        did=design_id(d)
        if did in used:continue
        used.add(did);append(d,'challenge','corner_neighborhood');count+=1
    columns=list(rows[0]);by_role={role:[r for r in rows if r['role']==role] for role in order}
    paths={'train':'data/train_pool_4096.csv','validation':'data/validation_1024.csv',
           'calibration':'evaluation_only/calibration_1024.csv','test':'evaluation_only/test_1536.csv',
           'challenge':'evaluation_only/challenge_512.csv'}
    for role,p in paths.items():write_csv(out/p,by_role[role],columns)
    pcols=['design_id','role','order_in_role','region',*FEATURES,*TARGETS,'solver_status']
    plan=[{**{k:r[k] for k in pcols if k in r and k not in TARGETS},**dict.fromkeys(TARGETS,''),'solver_status':'not_run'} for r in rows]
    write_csv(out/'plans/solver_designs_8192.csv',plan,pcols)
    for dbname,roles in [('data/development.sqlite',['train','validation']),('evaluation_only/evaluation.sqlite',['calibration','test','challenge'])]:
        dbp=out/dbname
        if dbp.exists():raise FileExistsError(dbp)
        db=sqlite3.connect(dbp);db.executescript('''
        PRAGMA foreign_keys=ON;
        CREATE TABLE designs(design_id TEXT PRIMARY KEY,role TEXT,order_in_role INTEGER,region TEXT,pump_power_W REAL,filter_offset_nm REAL,filter2_bw_nm REAL,gain_length_m REAL,release_id TEXT,origin TEXT);
        CREATE TABLE evaluations(design_id TEXT PRIMARY KEY REFERENCES designs(design_id),backend_id TEXT,source_kind TEXT,compressed_energy_nJ REAL,compressed_duration_fs REAL,compressed_peak_power_MW REAL);
        CREATE TABLE metadata(key TEXT PRIMARY KEY,value_json TEXT);
        ''')
        selected=[r for r in rows if r['role'] in roles]
        db.executemany('INSERT INTO designs VALUES(?,?,?,?,?,?,?,?,?,?)',[(r['design_id'],r['role'],r['order_in_role'],r['region'],*(r[k] for k in FEATURES),r['release_id'],r['origin']) for r in selected])
        db.executemany('INSERT INTO evaluations VALUES(?,?,?,?,?,?)',[(r['design_id'],r['backend_id'],r['source_kind'],*(r[k] for k in TARGETS)) for r in selected])
        db.execute('INSERT INTO metadata VALUES(?,?)',('label_function',json.dumps({'backend_id':c['benchmark_id'],'scope':'constructed scalar benchmark, not GMMNLSE'})))
        db.commit();assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';db.close()
    # Fixed nested orders: seed11 uses provided balanced order; others balanced blocks.
    train=by_role['train'];orders={'11':[r['design_id'] for r in train]}
    for seed in [22,33]:
        rr=random.Random(seed);core=[r['design_id'] for r in train if r['region']=='historical_core'];expanded=[r['design_id'] for r in train if r['region']=='expanded_proposal'];rr.shuffle(core);rr.shuffle(expanded)
        seq=[]
        for i in range(0,2048,32):
            block=core[i:i+32]+expanded[i:i+32];rr.shuffle(block);seq+=block
        orders[str(seed)]=seq
    (out/'data/training_orders.json').write_text(json.dumps({'sizes':[256,512,1024,2048,4096],'orders':orders},indent=2)+'\n')
    summary={'release_id':'mamyshev_accuracy_v4','label_function':c['benchmark_id'],'formula_changed_from_v3':False,'active_labeled_designs':len(rows),'roles':dict(order),
             'preserved_v3_rows':640,'new_labeled_designs':len(rows)-640,'archived_v3_holdout_ids_excluded':len(old_heldout),
             'candidate_designs':20000,'candidate_labels_generated':0,'calibration_and_test_distribution':'independent common 0.5 core + 0.5 expanded-uniform reference mixture; fresh IDs, not LHS',
             'region_counts':{k:dict(Counter(r['region'] for r in v)) for k,v in by_role.items()},
             'all_values_finite_positive':True,'solver_calls':0,'matlab_processes':0,'generation_elapsed_s':time.monotonic()-t,
             'formula_file_sha256':hashlib.sha256((ROOT/'configs/generator_recipe.json').read_bytes()).hexdigest()}
    (out/'DATA_BUILD_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');return summary
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.out),indent=2))
