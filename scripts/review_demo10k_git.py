#!/usr/bin/env python3
"""Read-only worktree/index/local-history inventory. Never stages or untracks."""
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/local/demo_10k_release_001'
DATA_EXT={'.csv','.tsv','.jsonl','.sqlite','.db','.parquet','.mat','.npy','.npz','.h5','.hdf5',
          '.zip','.tar','.tgz','.gz','.7z','.xlsx','.xls','.fig','.feather','.arrow','.joblib','.pkl','.pickle','.log'}
FEATURES={'pump_power_W','filter_offset_nm','filter2_bw_nm','gain_length_m'}
HISTORICAL_SUMMARY='demo/assets/historical_candidates.json'


def json_content_findings(name,raw):
    """Conservative structure checks, not a general secret/data detector.

    Aggregated metrics and recipe knot tables remain distinct from per-design
    X/Y or canonical-ID lists. Only the named historical summary may retain at
    most twelve actual four-input/target rows; hand-written tiny inputs are not
    evidence tables. Full arrays do not become publishable by changing suffix.
    """
    if Path(name).suffix.lower()!='.json':return []
    if len(raw)>2_000_000:return [{'kind':'large_json_not_content_reviewed','location':'$'}]
    try:value=json.loads(raw)
    except (ValueError,UnicodeDecodeError):return [{'kind':'invalid_json_needs_review','location':'$'}]
    findings=[]
    if name==HISTORICAL_SUMMARY:
        rows=value.get('rows') if isinstance(value,dict) else None
        if (not isinstance(rows,list) or len(rows)>12 or not isinstance(value.get('model_id'),str)
            or value.get('n_train')!=1024 or value.get('source')!='repository_guided_synthetic'):
            findings.append({'kind':'historical_summary_exceeds_or_lacks_reviewed_scope','location':'$.rows'})

    def visit(node,location='$',field=''):
        if isinstance(node,dict):
            for key,item in node.items():visit(item,location+'.'+key,key)
        elif isinstance(node,list):
            canonical_ids=bool(node) and all(isinstance(item,str) and re.fullmatch(r'd_[0-9a-f]{24}',item) for item in node)
            design_rows=any(isinstance(item,dict) and (FEATURES<=set(item) or
                isinstance(item.get('design_config'),dict) and FEATURES<=set(item['design_config'])) for item in node)
            matrix_name=field.lower() in {'x','y','x_train','y_train','x_test','y_test','y_true','y_pred',
                'inputs','targets','predictions','residuals','scores','samples','labels'}
            # Hash strings/counts in provenance are not raw ID or sample arrays.
            if len(node)>12 and (canonical_ids or design_rows or matrix_name):
                findings.append({'kind':'full_id_or_per_design_json_array','location':location,'rows':len(node)})
            if design_rows and len(node)<=12 and name!=HISTORICAL_SUMMARY:
                # Small arbitrary recorded tables still need review. The single
                # hand-written input format is one dict, not an evidence table.
                findings.append({'kind':'small_design_table_needs_review','location':location,'rows':len(node)})
            for index,item in enumerate(node):visit(item,f'{location}[{index}]',field)
    visit(value)
    return findings

def git(*args,input=None):
    p=subprocess.run(['git',*args],cwd=ROOT,input=input,capture_output=True)
    if p.returncode not in (0,1):raise RuntimeError(p.stderr.decode())
    return p.stdout

def classify(name,tracked):
    p=Path(name);ext=p.suffix.lower()
    if (name.startswith('demo/outputs/') or p.name=='secrets.toml' or p.name=='.env'
        or p.name.startswith('.env.') or ext in {'.key','.pem'}):
        return ('D' if tracked else 'B'),('needs_untrack_approval' if tracked else 'keep_local'),'Private runtime output or secret/config material','local_only','Keep local; inspect secret scope separately; no deletion or index changes performed.'
    if name.startswith(('code/simulation_engine/','third_party/')):
        required='MATLAB_engine_bundle; individual_file_necessity_not_verified' if name.startswith('code/simulation_engine/') else 'reference_only'
        return 'D','blocked_license','Third-party/custom engine or reference package; includes material inputs and historical examples, not all files are current run dependencies',required,'Retain attribution and actual material inputs; distinguish example outputs during file-level redistribution review; do not blanket-remove MAT/CSV.'
    if name.startswith(('docs/thesis/','docs/references/')) or ext=='.pdf':
        return 'D','blocked_license','Thesis/literature or historical document','no','Confirm author/institution redistribution rights before publication.'
    raw=(name.startswith(('reports/local/','mamyshev_accuracy_v4/data/','mamyshev_accuracy_v4/evaluation_only/','mamyshev_accuracy_v4/evidence/','mamyshev_accuracy_v4/plans/','data/','results/','archive/original_experiment_folder/'))
         and p.name!='README.md')
    raw=raw or (name.startswith('mamyshev_accuracy_v4/provenance/') and (ext=='.csv' or 'design_ids' in name))
    raw=raw or name=='configs/accuracy_v4_2_protocol.json'
    minimal_weight=name.startswith('demo/assets/models/') and p.name=='model.joblib'
    if raw or ext in DATA_EXT and not minimal_weight:
        decision='needs_untrack_approval' if tracked else 'keep_local'
        return ('D' if tracked else 'B'),decision,'Private dataset, complete plan, raw/derived evidence or historical output','local_reproduction_only','Keep local; separate approval needed to untrack and to address any historical blobs.' if tracked else 'Keep in ignored output/data path; do not encode/compress/LFS the data for publication.'
    if name.startswith('demo/assets/models/'):
        return 'C','blocked_license','Minimal inference weight/class/config/q/aggregate model card','Demo','Review model, recipe and source attribution; only audited minimal artifacts, never old bundle ZIP.'
    if name.startswith(('docs/assets/','demo/assets/')):
        return 'A','include','Curated aggregate summary or attributed visualization; no full dataset','Demo','Review generated provenance and image attribution; permission to publish still separate.'
    if name.startswith(('_codex_plan/','.codex/','.agents/')) or p.name.startswith('CODEX_') or 'UPLOAD_REVIEW' in p.name or p.name=='DOCUMENT_REVIEW.json':
        return 'B','review_sensitive','Local execution instructions/review workflow','no','Keep local or prepare a separate redacted copy; do not rewrite old identities.'
    if '__pycache__' in name or ext in {'.pyc','.asv'} or p.name=='.DS_Store':
        return 'B','keep_local','Cache/editor backup','no','Do not submit caches; no deletion performed in this batch.'
    return 'A','include','Source, test, configuration, schema or documentation','Demo/MATLAB/reproduction depending on path','Review file-level notices and remove private-path dependence from public quick entry; no automatic git add.'

def main():
    dest=OUT/'git_release_manifest.json'
    if dest.exists():raise FileExistsError(dest)
    tracked=set(git('ls-files','-z').decode().split('\0'))-{''}
    staged=set(git('diff','--cached','--name-only','-z').decode().split('\0'))-{''}
    names=sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts and p!=dest)
    ignore_raw=git('check-ignore','--no-index','-v','-z','--stdin',input=('\0'.join(names)+'\0').encode()).decode().split('\0')
    ignore={}
    for i in range(0,len(ignore_raw)-3,4):
        source,line,pattern,name=ignore_raw[i:i+4]
        ignore[name]={'source':source,'line':int(line),'pattern':pattern,'effective_for_untracked':name not in tracked and not pattern.startswith('!')}
    records=[]
    for name in names:
        path=ROOT/name;raw=path.read_bytes()
        cat,decision,purpose,required,action=classify(name,name in tracked)
        content_findings=[]
        if decision in {'include','blocked_license'} and not name.startswith(('code/simulation_engine/','third_party/')):
            content_findings=json_content_findings(name,raw)
            if any(item['kind']=='full_id_or_per_design_json_array' for item in content_findings):
                cat,decision=('D','needs_untrack_approval') if name in tracked else ('B','keep_local')
                purpose='JSON contains full ID/per-design arrays; encoding does not change the data publication restriction'
                required='local_reproduction_only';action='Keep this data local; publish only separately reviewed aggregate provenance, not encoded rows.'
            elif content_findings:
                decision='review_sensitive';action='Resolve JSON content/scope findings before including this file; no automatic approval.'
        sensitive=[]
        if path.suffix.lower() in {'.py','.m','.md','.json','.toml','.yml','.yaml','.txt'} and len(raw)<2_000_000 and not name.startswith('reports/local/'):
            text=raw.decode(errors='replace')
            for line,value in enumerate(text.splitlines(),1):
                if re.search(r'/Users/[^/\s]+|/opt/homebrew/|/private/var/',value):sensitive.append({'line':line,'kind':'machine_path'})
                if re.search(r'(?:gh[pousr]_[A-Za-z0-9]{25,}|sk-[A-Za-z0-9]{32,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)',value):sensitive.append({'line':line,'kind':'potential_secret'})
        if sensitive and decision=='include':decision='review_sensitive'
        state='tracked' if name in tracked else ('ignored' if ignore.get(name,{}).get('effective_for_untracked') else 'untracked')
        records.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'state':state,'staged':name in staged,
                        'ignore_rule':ignore.get(name),'category':cat,'recommendation':decision,'purpose':purpose,'required_for':required,
                        'attribution_basis':'docs/ATTRIBUTION_REVIEW.md; per-file notices and this batch asset provenance; root license not finalized',
                        'sensitive_locations':sensitive,'json_content_findings':content_findings,'next_action':action})
    history=[]
    for line in git('rev-list','--objects','--all').decode().splitlines():
        parts=line.split(' ',1)
        if len(parts)!=2:continue
        oid,name=parts
        if (Path(name).suffix.lower() in DATA_EXT or name=='configs/accuracy_v4_2_protocol.json'
            or name.startswith(('data/','archive/original_experiment_folder/','docs/references/','docs/thesis/',
                'mamyshev_accuracy_v4/data/','mamyshev_accuracy_v4/evaluation_only/','mamyshev_accuracy_v4/evidence/',
                'mamyshev_accuracy_v4/plans/','mamyshev_accuracy_v4/provenance/'))):
            cat,decision,purpose,required,action=classify(name,True)
            history.append({'path':name,'git_object':oid,'category':cat,'recommendation':decision,'required_for':required,'next_action':action})
    summary={'file_count':len(records),'by_recommendation':dict(collections.Counter(r['recommendation'] for r in records)),
             'tracked_files':len(tracked),'staged_files':len(staged),'tracked_data_needing_approval':[r['path'] for r in records if r['recommendation']=='needs_untrack_approval'],
             'local_history_relevant_objects':len(history),'public_readiness':'public_release_blocked',
             'blocking_reasons':['Tracked historical data require separate untrack/history decision; none performed','Mixed source/model/recipe/figure redistribution rights pending','Machine-specific documents/source require separate sharing review'],
             'remote_network_checked':False,'remote_has_never_contained_data':'not_verified','git_writes_performed':False,
             'hash_scope':'Current worktree bytes. Tracked/staged path states are inspected; distinct staged blob contents are not separately audited.',
             'content_check_scope':'Path/extension classification plus bounded JSON structure and text-pattern checks; not proof against every possible encoded dataset or secret.',
             'no_data_via_LFS_or_reencoding':True}
    manifest={'schema_version':'demo10k_git_review_v1','summary':summary,'files':records,'available_local_history':history}
    with dest.open('x') as stream:json.dump(manifest,stream,indent=2);stream.write('\n')
    lines=['# Git 发布预审清单（未执行 Git 写操作）','',
        '完整逐文件相对路径、大小、SHA-256、tracked/staged/ignored 状态、ignore 规则、用途和建议见本地 `reports/local/demo_10k_release_001/git_release_manifest.json`。',
        '这里只记录当前工作树、索引与可用本地历史；没有联网核对远程，不能声称远程从未含数据。公开状态 `public_release_blocked`。','',
        '逐文件SHA256对应当前工作树字节；索引检查记录tracked/staged状态，未另审查不同的staged blob内容。JSON结构检查只针对可识别的逐点/ID数组，不是所有编码数据或秘密的完备探测。','',
        '| 分类 | 当前文件数 | 后续动作 |','|---|---:|---|']
    for decision,count in summary['by_recommendation'].items():lines.append(f'| {decision} | {count} | 详见逐文件清单；均未自动 stage/commit/push |')
    lines += ['',f"索引当前跟踪 {len(tracked)} 个路径，staged {len(staged)} 个路径；可用本地历史中发现 {len(history)} 个相关数据/文档对象。",'',
        '## A. 拟提交工程文件','',
        '`demo/app.py`、`demo/ui_logic.py`、`src/mamyshev_ml/demo_inference.py`、`src/mamyshev_ml/demo10k_experiment.py`、本批计划/训练/检查 scripts 与 tests、`configs/` 小型协议、README/指南、聚合 metrics 和 docs/assets 图。每个实际文件的摘要与敏感路径命中在机器清单；include 是建议，不是发布授权。','',
        '## B. 仅本地','',
        '`reports/local/`、完整 train/dev/cal/test/候选池、全部 10k plan、逐点评分/预测、SQLite/JSONL/CSV、原复场 MAT 和私人日志全部 keep_local。数据换成 JSON、ZIP 或 Git LFS 仍然是数据发布，不接受该绕行。','',
        '## C. 轻量推理工件','',
        '`demo/assets/models/` 下明确受信的权重、原类、域/schema、必要 q、聚合 model card 与独立 manifest；不得夹带训练 X/Y、ID 排除表或旧整个 ZIP。功能副本含许可待审工件，不等同获准公开版本。需先确认模型/配方/源码归属。','',
        '## D. 已跟踪数据、历史和第三方','',
        '`.gitignore` 只影响未跟踪项，不能清除现有索引或历史。以下实际已跟踪数据需要单独审批；本批未删除、未 git rm --cached、未取消 stage 或改写历史。','',
        '| 已跟踪数据路径 | 大小（字节） | SHA-256 |','|---|---:|---|']
    for r in records:
        if r['recommendation']=='needs_untrack_approval':lines.append(f"| `{r['path']}` | {r['bytes']} | `{r['sha256']}` |")
    lines += ['', '实际 GMMNLSE 与 third_party 中的 MAT/CSV/截面材料输入单列为引擎依赖，保留文件和逐文件声明，不用全局 *.mat/*.csv 忽略/删除破坏后端。MMTools GPLv3 不自动覆盖实际定制引擎。论文/毕业论文/第三方示例输出的许可逐项待审。','',
        '下一步需用户批准：拟公开模型/配方/自有图及源码许可范围；哪些已跟踪数据取消跟踪（如需）；历史是否需要另行处理及影响；精确提交allowlist。当前不执行这些操作。']
    (ROOT/'docs/GIT_RELEASE_PLAN.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
