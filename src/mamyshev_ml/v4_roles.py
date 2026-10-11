"""Release DB access with explicit role/source guards and training-prefix queries."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'mamyshev_accuracy_v4'
FEATURES = ('pump_power_W', 'filter_offset_nm', 'filter2_bw_nm', 'gain_length_m')
TARGETS = ('compressed_energy_nJ', 'compressed_duration_fs', 'compressed_peak_power_MW')
SOURCE = 'repository_guided_synthetic'
BACKEND = 'mamyshev_repository_guided_synthetic_v3'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_frozen(model, selection):
    model, selection = Path(model).resolve(), Path(selection).resolve()
    # Only locally created artifacts under this repository, never an untrusted pickle.
    trusted = ROOT / 'reports/local/accuracy_v4_001'
    if not model.is_relative_to(trusted) or not selection.is_relative_to(trusted):
        raise PermissionError('Only this batch\'s locally created model is trusted')
    value = json.loads(selection.read_text())
    if not value.get('frozen') or value.get('model_sha256') != sha(model):
        raise ValueError('Missing freeze or model hash mismatch')
    if value['accuracy_protocol_sha256'] != sha(PACKAGE / 'configs/accuracy_protocol.json'):
        raise ValueError('Protocol changed after selection')
    for name, digest in value['training_source_hashes'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Frozen learning source changed: ' + name)
    for name, digest in value['split_hashes'].items():
        if sha(PACKAGE / name) != digest:
            raise ValueError('Frozen split changed: ' + name)
    return value


class ReleaseData:
    """Models use development by default. Evaluation roles require verified freeze."""
    def __init__(self, *, evaluation=False, model=None, selection=None, log_path=None):
        self.evaluation = bool(evaluation)
        self.accesses = []
        self.log_path = Path(log_path) if log_path else None
        if evaluation:
            if model is None or selection is None:
                raise PermissionError('Evaluation labels require a frozen trusted model')
            verify_frozen(model, selection)
        self.path = PACKAGE / ('evaluation_only/evaluation.sqlite' if evaluation else 'data/development.sqlite')

    def read(self, role, *, source_kind, ids=None):
        allowed = {'calibration', 'test', 'challenge'} if self.evaluation else {'train', 'validation'}
        if role not in allowed or source_kind != SOURCE:
            raise PermissionError('Role/source not authorized for this loader')
        if role == 'train' and ids is None:
            raise PermissionError('Training labels require an explicit prefix ID list')
        if ids is not None and len(set(ids)) != len(ids):
            raise ValueError('Duplicate requested IDs')
        columns = ['d.design_id', 'd.role', 'd.region', *['d.' + k for k in FEATURES],
                   *['e.' + k for k in TARGETS], 'e.source_kind', 'e.backend_id']
        sql = ('SELECT ' + ','.join(columns) + ' FROM designs d JOIN evaluations e USING(design_id) '
               'WHERE d.role=? AND e.source_kind=? AND e.backend_id=?')
        with sqlite3.connect(f'file:{self.path}?mode=ro', uri=True) as db:
            db.row_factory = sqlite3.Row
            if ids is None:
                result = [dict(r) for r in db.execute(sql + ' ORDER BY d.order_in_role', (role, source_kind, BACKEND))]
            else:
                result = []
                for offset in range(0, len(ids), 400):
                    batch = ids[offset:offset + 400]
                    result.extend(dict(r) for r in db.execute(sql + ' AND d.design_id IN (' + ','.join('?' for _ in batch) + ')',
                                                              [role, source_kind, BACKEND, *batch]))
                lookup = {r['design_id']: r for r in result}
                if set(lookup) != set(ids):
                    raise ValueError('Requested training prefix contains missing/wrong-role IDs')
                result = [lookup[i] for i in ids]
        self.accesses.append({'role': role, 'source_kind': source_kind, 'database': str(self.path.relative_to(PACKAGE)),
                              'rows': len(result), 'design_ids': [r['design_id'] for r in result]})
        if self.log_path:
            with self.log_path.open('a') as stream:
                stream.write(json.dumps(self.accesses[-1]) + '\n')
        return result
