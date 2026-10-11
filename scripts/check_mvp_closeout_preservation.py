#!/usr/bin/env python3
"""Read-only closeout preservation audit; writes only new audit evidence."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/local/mvp_closeout_001'
ALLOW={'README.md','docs/SCOPE.md','docs/EXECUTION_STATUS.md'}
DOCS=['README.md','docs/SCOPE.md','docs/EXECUTION_STATUS.md','docs/USER_GUIDE_ZH.md',
      'docs/CLAIM_EVIDENCE.md','docs/ATTRIBUTION_REVIEW.md','docs/MVP_CLOSEOUT_REPORT.md']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    destination=OUT/'preservation_check.json'
    if destination.exists():raise FileExistsError(destination)
    start=json.loads((OUT/'start_snapshot.json').read_text())
    changed=[];missing=[]
    for name,digest in start['sha256'].items():
        path=ROOT/name
        if not path.is_file():missing.append(name)
        elif sha(path)!=digest:changed.append(name)
    current={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()
             and not p.is_relative_to(OUT) and not any(x in p.parts for x in ('.git','__pycache__','.pytest_cache'))}
    new=sorted(current-set(start['sha256']))
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    diff=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True)
    whitespace=[]
    for name in new:
        path=ROOT/name
        if path.suffix in ('.py','.md'):
            for i,line in enumerate(path.read_text().splitlines(),1):
                if line.rstrip()!=line:whitespace.append(f'{name}:{i}')
    broken=[]
    for name in DOCS:
        path=ROOT/name
        for link in re.findall(r'\]\(([^\n]+?)\)',path.read_text()):
            target=unquote(link.strip('<>').split('#')[0])
            if not target or '://' in target or target.startswith('mailto:'):continue
            resolved=(path.parent/target).resolve()
            if resolved!=destination and not resolved.exists():broken.append({'document':name,'target':target})
    evidence=json.loads((OUT/'evidence/evidence_summary.json').read_text())
    sources_ok=all(sha(ROOT/name)==v['sha256'] for name,v in evidence['source_files'].items())
    figures_ok=all(sha(ROOT/r['source'])==sha(ROOT/r['copy'])==r['sha256'] for r in evidence['figures'])
    from mamyshev_ml.closeout_inference import verify
    bundle=verify(OUT/'inference_bundle')
    build=json.loads((OUT/'bundle_build.json').read_text())
    archive_ok=sha(OUT/'inference_bundle.zip')==build['archive_sha256']
    protected=[name for name in start['sha256'] if name.startswith(('code/','src/','tests/','scripts/','configs/','mamyshev_accuracy_v4/'))]
    historical=[name for name in start['sha256'] if name.startswith('reports/local/')]
    ledgers=[name for name in historical if any(x in name.lower() for x in ('query','ledger','.sqlite'))]
    result={'old_files_checked':len(start['sha256']),'unchanged':len(start['sha256'])-len(changed)-len(missing),
        'changed':changed,'missing':missing,'allowed_document_changes':sorted(ALLOW),
        'unexpected_changes':sorted(set(changed)-ALLOW),'new_repository_files':new,
        'protected_source_config_files':len(protected),'protected_all_unchanged':not set(protected)&set(changed+missing),
        'historical_evidence_files':len(historical),'historical_all_unchanged':not set(historical)&set(changed+missing),
        'evaluation_query_ledger_files':ledgers,'evaluation_query_ledger_bytes_unchanged':not set(ledgers)&set(changed+missing),
        'no_new_historical_files':not any(n.startswith('reports/local/') for n in new),
        'branch':branch,'commit':commit,'branch_commit_unchanged':branch==start['branch'] and commit==start['commit'],
        'git_diff_check_exit_code':diff.returncode,'git_diff_check_output':diff.stdout+diff.stderr,
        'new_file_whitespace_errors':whitespace,'broken_local_document_links':broken,
        'saved_summary_source_hashes_valid':sources_ok,'four_figure_copies_byte_identical':figures_ok,
        'bundle_verification':bundle,'archive_hash_unchanged':archive_ok}
    result['passed']=not missing and not result['unexpected_changes'] and result['branch_commit_unchanged'] and not diff.returncode and not whitespace and not broken and sources_ok and figures_ok and archive_ok and result['no_new_historical_files']
    with destination.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    (OUT/'git_status_end.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True))
    print(json.dumps({k:v for k,v in result.items() if k not in ('evaluation_query_ledger_files','new_repository_files')},indent=2))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
