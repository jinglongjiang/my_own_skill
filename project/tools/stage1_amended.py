#!/usr/bin/env python3
"""Additive Amendment-1 runner. Frozen original source and evidence stay unchanged."""
import os
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '2'
import argparse
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import time
import sys
import numpy as np
import joblib
from threadpoolctl import threadpool_limits
import stage1_offline as original

ROOT = original.ROOT
OLD = original.OUT
OUT = OLD / 'amendment1'
FROZEN = original.FROZEN
AMENDMENT_COMMIT = '0d470b6ac9e8acca259ed806078689068bedade7'
AMENDMENT_SHA = '670e6819a00df64d95bf60fd4c42faacca38550329711dc0cbd71ba55b0d62d1'
NOTE_SHA = '87653d1a8b50454c37733430c9a4ca2a5ee6d85a7d5e974c629a4fd12c7b96c3'
ORIGINAL_SOURCE_SHA = '734e63b5917f6f5003936c99503d7410ca49140001eae1f941998c455c783920'
WHOLE_TASK_DEADLINE = datetime(2026, 10, 14, 2, 38, tzinfo=timezone.utc)
RESUMED_ACTIVE_DEADLINE = datetime(2026, 10, 14, 7, 51, 5, tzinfo=timezone.utc)
DEADLINE = min(WHOLE_TASK_DEADLINE, RESUMED_ACTIVE_DEADLINE)
original.OUT = OUT
original.STAGE1_DEADLINE = DEADLINE
save = original.save_json
sha = original.sha


def ensure_budget():
    assert datetime.now(timezone.utc) < DEADLINE, 'STOP: original whole-task deadline reached; unfinished result INCONCLUSIVE'


def exclusive_marker(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def verify_history():
    assert sha(FROZEN / 'AMENDMENT-1.md') == AMENDMENT_SHA
    assert sha(FROZEN / 'AMENDMENT-1-IMPLEMENTATION.md') == NOTE_SHA
    assert sha(ROOT / 'project/tools/stage1_offline.py') == ORIGINAL_SOURCE_SHA
    checked = []
    for name in ('PUBLICATION_MANIFEST.json', 'LOCAL_ARTIFACTS.json'):
        for item in json.loads((OLD / name).read_text())['files']:
            # SUMMARY is owned by the coordinator; all scientific artifacts remain immutable.
            if item['path'] == 'project/reports/SUMMARY.md':
                continue
            path = ROOT / item['path']
            assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], 'Historical artifact changed: ' + item['path']
            checked.append(item['path'])
    save(OUT / 'historical_integrity.json', {'status': '已验证通过', 'checked_files': checked,
         'amendment_remote_commit': AMENDMENT_COMMIT, 'amendment_sha256': AMENDMENT_SHA,
         'implementation_note_sha256': NOTE_SHA, 'original_source_sha256': ORIGINAL_SOURCE_SHA,
         'seen_before_amendment': ['C01 true OOF', 'C01 shuffled OOF', 'C02 shuffled OOF'],
         'locked_labels_decoded': False})
    original.verify_inputs()


def read_rows(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


def paired_contrast(true_rows, shuffle_rows, partition_code):
    true_by_key = {r['key']: r for r in true_rows}
    shuffle_by_key = {r['key']: r for r in shuffle_rows}
    assert len(true_by_key) == len(true_rows) == len(shuffle_rows) == len(shuffle_by_key)
    assert set(true_by_key) == set(shuffle_by_key)
    ordered = sorted(true_by_key)
    tr = [true_by_key[k] for k in ordered]
    sr = [shuffle_by_key[k] for k in ordered]
    invariant = ('episode', 'case', 'cell', 'eligible_count', 'baseline_choice', 'regret_base',
                 'regret_random', 'regret_random_top5', 'regret_oracle_top5', 'failure_base',
                 'failure_random', 'failure_random_top5', 'failure_oracle_top5')
    for t, s in zip(tr, sr):
        assert all(t[k] == s[k] for k in invariant), 'Mismatched paired root/control'
    report = {}
    for gi, cells in enumerate(original.GROUPS):
        ii = [i for i, row in enumerate(tr) if row['cell'] in cells]
        t = [tr[i] for i in ii]; s = [sr[i] for i in ii]
        if not t:
            continue
        eligible = np.array([r['eligible_count'] >= 2 for r in t])
        delta = np.array([a['regret_candidate'] - b['regret_candidate'] for a, b in zip(t, s)])
        fdelta = np.array([a['failure_candidate'] - b['failure_candidate'] for a, b in zip(t, s)])
        report[original.GROUP_NAMES[gi]] = {}
        for cluster, key in [('episode', 'episode_primary'), ('case', 'case_sensitivity')]:
            w, seed = original.bootstrap_weights(t, cluster, gi, partition_code)
            wr = w * eligible
            sampled = original.ratio(wr @ delta, wr.sum(axis=1))
            ci = original.percentile(sampled)
            report[original.GROUP_NAMES[gi]][key] = {
                'delta_true_minus_shuffle': float(delta[eligible].mean()),
                'delta_true_minus_shuffle_ci95': ci,
                'gain_shuffle_minus_true': float(-delta[eligible].mean()),
                'gain_shuffle_minus_true_ci95': [-ci[1], -ci[0]],
                'delta_ci98_3333_cv_bonferroni': original.percentile(sampled, 1 - 0.05 / 3) if partition_code == 0 else None,
                'failure_change_true_minus_shuffle': float(fdelta.mean()),
                'failure_change_true_minus_shuffle_ci95': original.percentile(original.ratio(w @ fdelta, w.sum(axis=1))),
                'n_states_regret': int(eligible.sum()), 'n_states_failure': len(t),
                'n_episodes': len({r['episode'] for r in t}), 'n_cases': len({r['case'] for r in t}),
                'bootstrap': {'cluster': cluster, 'replicates': original.N_BOOT, 'seed_sequence': seed},
                'interpretation': 'Negative Delta favors true labels; positive gain favors true labels.'}
    return report


def gate(summary):
    checks = []
    for group in original.GROUP_NAMES:
        item = summary[group]['episode_primary']
        ci = item['paired_regret_gain_ci95']
        assert ci is not None and len(ci) == 2 and np.isfinite(ci).all(), 'STOP: undefined shuffled gate interval'
        checks.append({'group': group, 'gain_base_minus_shuffle': item['paired_regret_gain'],
                       'ci95': ci, 'triggers_stop': ci[0] > 0.0})
    return {'status': '已确认失败' if any(x['triggers_stop'] for x in checks) else '已验证通过',
            'definition': 'STOP iff any group episode-primary paired absolute regret gain lower 95% CI > 0',
            'checks': checks, 'locked_labels_decoded': False}


def adjudicate(primary, contrast):
    reduction = primary['regret_reduction']
    ci = primary['regret_reduction_ci95']
    gain_ci = contrast['gain_shuffle_minus_true_ci95']
    if reduction is None or ci is None or gain_ci is None:
        return 'INCONCLUSIVE'
    if reduction < 0.05:
        return 'NOT SUPPORTED'
    if (reduction >= 0.20 and ci[0] > 0.0
            and primary['candidate']['failure_rate'] <= primary['base']['failure_rate']
            and gain_ci[0] > 0.0):
        return 'SUPPORTED'
    return 'INCONCLUSIVE'


def amended_tests():
    original.synthetic_tests()
    count = 0
    def check(value):
        nonlocal count
        assert value, 'Amended synthetic check %d' % (count + 1)
        count += 1
    fixture = {g: {'episode_primary': {'paired_regret_gain': 0.1, 'paired_regret_gain_ci95': [-0.2, 0.3]}} for g in original.GROUP_NAMES}
    check(gate(fixture)['status'] == '已验证通过')
    fixture['5人']['episode_primary']['paired_regret_gain_ci95'] = [0.0, 0.3]
    check(gate(fixture)['status'] == '已验证通过')
    fixture['10人']['episode_primary']['paired_regret_gain_ci95'] = [1e-15, 0.3]
    check(gate(fixture)['status'] == '已确认失败')
    row = {'key': 'c4-k93000-s1', 'episode': 'c4-k93000', 'case': 93000, 'cell': 4, 'eligible_count': 2,
           'baseline_choice': 0, 'regret_base': 0.4, 'regret_random': 0.3, 'regret_random_top5': 0.3,
           'regret_oracle_top5': 0.0, 'failure_base': 1.0, 'failure_random': 0.5,
           'failure_random_top5': 0.5, 'failure_oracle_top5': 0.0, 'regret_candidate': 0.1, 'failure_candidate': 0.0}
    other = dict(row, regret_candidate=0.3, failure_candidate=1.0)
    result = paired_contrast([row], [other], 0)['20人']['episode_primary']
    check(np.allclose(result['delta_true_minus_shuffle_ci95'], [-0.2, -0.2]))
    check(np.allclose(result['gain_shuffle_minus_true_ci95'], [0.2, 0.2]))
    check(result['failure_change_true_minus_shuffle_ci95'] == [-1.0, -1.0])
    bad = dict(other, key='c4-k93000-s2')
    try:
        paired_contrast([row], [bad], 0)
    except AssertionError:
        check(True)
    else:
        check(False)
    primary = {'regret_reduction': 0.3, 'regret_reduction_ci95': [0.1, 0.5],
               'candidate': {'failure_rate': 0.1}, 'base': {'failure_rate': 0.2}}
    check(adjudicate(primary, {'gain_shuffle_minus_true_ci95': [0.01, 0.2]}) == 'SUPPORTED')
    check(adjudicate(primary, {'gain_shuffle_minus_true_ci95': [0.0, 0.2]}) == 'INCONCLUSIVE')
    check(adjudicate(dict(primary, regret_reduction=0.04), {'gain_shuffle_minus_true_ci95': [-0.1, 0.2]}) == 'NOT SUPPORTED')
    marker = OUT / 'synthetic_read_once_claim.json'
    exclusive_marker(marker, {'synthetic_only': True})
    try:
        exclusive_marker(marker, {'synthetic_only': True})
    except FileExistsError:
        check(True)
    else:
        check(False)
    p = {'c4-k93000': {'partition': 'locked'}, 'c4-k93001': {'partition': 'development'}}
    got = original.filtered_records([json.dumps(row), '{"episode":"c4-k93001","G_A":THIS_MUST_NOT_PARSE}'], p, 'locked')
    check(len(got) == 1 and got[0]['key'] == row['key'])
    check(DEADLINE == WHOLE_TASK_DEADLINE)
    save(OUT / 'amended_synthetic_tests.json', {'status': '已验证通过', 'checks_passed': count,
         'original_checks_passed': 26, 'source_sha256': sha(__file__), 'real_data_loaded': False, 'time': original.utcnow()})
    print('Amended synthetic checks passed:', count, flush=True)


def old_arm(records, dataset, config, shuffled):
    suffix = 'shuffle' if shuffled else 'true'
    name = config['id'] + '_' + suffix
    rows = read_rows(OLD / (name + '_oof_rows.jsonl'))
    pred = np.load(OLD / (name + '_oof_predictions.npy'), allow_pickle=False)
    choices = original.choices_from_prediction(records, dataset, pred, config)
    expected = [original.reference_metrics(row, choice) for row, choice in zip(records, choices)]
    assert rows == expected, 'STOP: saved arm rows do not match archived predictions/current frozen data'
    return rows


def save_arm_summary(candidate, arm, rows):
    summary = original.summarize(rows)
    save(OUT / (candidate + '_' + arm + '_summary.json'), summary)
    return summary


def publish_manifest(name, extra=()):
    paths = [ROOT / 'project/tools/stage1_amended.py', *extra]
    for p in sorted(OUT.rglob('*')):
        if not p.is_file() or p.name.endswith('_PUBLICATION_MANIFEST.json'):
            continue
        rel = p.relative_to(OUT)
        if 'runtime' in rel.parts or 'models' in rel.parts or p.suffix == '.npy' or p.name.endswith('_oof_rows.jsonl'):
            continue
        paths.append(p)
    unique = sorted(set(paths))
    files = []
    for p in unique:
        files.append({'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': sha(p),
                      'encoding': 'base64' if p.suffix in ('.joblib', '.gz') else 'utf-8'})
    save(OUT / (name + '_PUBLICATION_MANIFEST.json'), {'status': 'ready for parent publication', 'files': files})


def compress_rows():
    for p in OUT.glob('*_oof_rows.jsonl'):
        q = Path(str(p) + '.gz')
        if not q.exists():
            with q.open('xb') as stream:
                stream.write(gzip.compress(p.read_bytes(), mtime=0))


def run_cv(note_commit):
    ensure_budget()
    assert len(note_commit) == 40, 'Implementation note remote commit confirmation required'
    assert not (OUT / 'CV_STARTED.json').exists(), 'Refuse to rerun amended CV'
    tests = json.loads((OUT / 'amended_synthetic_tests.json').read_text())
    assert tests['status'] == '已验证通过' and tests['source_sha256'] == sha(__file__)
    verify_history()
    exclusive_marker(OUT / 'CV_STARTED.json', {'time': original.utcnow(), 'note_remote_commit': note_commit,
                     'amendment_remote_commit': AMENDMENT_COMMIT, 'whole_task_deadline': DEADLINE.isoformat(),
                     'resumed_active_deadline': RESUMED_ACTIVE_DEADLINE.isoformat(), 'locked_labels_decoded': False})
    split = original.assignments()
    assert all(93000 <= int(r['case']) <= 93174 for r in split.values())
    records = original.load_development(split)
    original.verify_development_controls(records)
    dataset = original.make_dataset(records, split)
    configs = json.loads((FROZEN / 'candidates.json').read_text())['candidates']
    completed = []; skipped = []; all_summaries = {}
    for config in configs:
        ensure_budget()
        cid = config['id']
        shuffled = old_arm(records, dataset, config, True) if cid in ('C01', 'C02') else original.oof_fit(records, split, dataset, config, True)
        if shuffled is None:
            skipped.append({'candidate': cid, 'reason': 'shuffle fit failed'}); continue
        shuffle_summary = save_arm_summary(cid, 'shuffle', shuffled)
        gating = gate(shuffle_summary); gating['candidate'] = cid
        save(OUT / (cid + '_shuffle_gate.json'), gating)
        original.note('Amended any-group shuffle gate: ' + cid + ' ' + gating['status'])
        if gating['status'] != '已验证通过':
            save(OUT / 'CV_TERMINAL.json', {'status': '已确认失败', 'reason': 'amended shuffle hard gate',
                 'candidate': cid, 'gate': gating, 'locked_labels_decoded': False, 'time': original.utcnow()})
            compress_rows(); publish_manifest('STOPPED'); return 2
        true = old_arm(records, dataset, config, False) if cid == 'C01' else original.oof_fit(records, split, dataset, config, False)
        if true is None:
            skipped.append({'candidate': cid, 'reason': 'true fit failed'}); continue
        true_summary = save_arm_summary(cid, 'true', true)
        contrast = paired_contrast(true, shuffled, 0)
        save(OUT / (cid + '_paired_true_minus_shuffle.json'), contrast)
        all_summaries[cid] = {'true': true_summary, 'shuffle': shuffle_summary, 'paired': contrast}
        primary = true_summary['20人']['episode_primary']
        completed.append({'candidate': cid, 'regret': primary['candidate']['regret_mean'],
                          'failure': primary['candidate']['failure_rate'], 'reduction': primary['regret_reduction']})
        original.note('True and shuffle OOF complete: ' + cid + ' ' + json.dumps(completed[-1]))
        print('PAIRED_20 ' + cid + ' ' + json.dumps(contrast['20人']['episode_primary']), flush=True)
    assert completed, 'STOP: no candidate completed'
    winner = sorted(completed, key=lambda x: (x['regret'], x['failure'], x['candidate']))[0]
    config = next(c for c in configs if c['id'] == winner['candidate'])
    whole = np.ones(len(dataset['X']), dtype=bool)
    models = {}
    target = 'failure' if config['id'] == 'C03' else 'return'
    for arm in ('true', 'shuffle'):
        ensure_budget()
        got = original.one_fit(dataset, config, whole, whole, target if arm == 'true' else 'shuffle_' + target,
                               config['id'] + '_' + arm + '_final_development')
        assert got is not None, 'STOP: selected full-development fit failed; locked evaluation forbidden'
        models[arm] = {'path': str(got[1].relative_to(ROOT)), 'sha256': sha(got[1]), 'bytes': got[1].stat().st_size,
                       'target': target if arm == 'true' else 'shuffle_' + target}
    selection = {'status': '已验证通过', 'next_step': 'await verified publication of both actual models and selection before locked read',
         'selected_candidate': config, 'selection_rule': 'minimum true-label 20-person OOF regret, then failure, then candidate ID',
         'winner': winner, 'all_completed_candidates': completed, 'skipped_candidates': skipped, 'models': models,
         'protocol_remote_commit': original.PROTOCOL_COMMIT, 'amendment_remote_commit': AMENDMENT_COMMIT,
         'implementation_note_remote_commit': note_commit, 'protocol_sha256': sha(FROZEN / 'PROTOCOL.md'),
         'episodes_csv_sha256': sha(FROZEN / 'episodes.csv'), 'candidate_list_sha256': sha(FROZEN / 'candidates.json'),
         'amendment_sha256': AMENDMENT_SHA, 'implementation_note_sha256': NOTE_SHA,
         'original_source_sha256': ORIGINAL_SOURCE_SHA, 'amended_source_sha256': sha(__file__),
         'training_roots': len(records), 'training_candidates': len(dataset['X']),
         'locked_labels_decoded': False, 'time': original.utcnow(), 'whole_task_deadline': DEADLINE.isoformat(),
         'history': 'C01 true/shuffle and C02 shuffle CV seen before amendment; historical stopped outputs preserved'}
    save(OUT / 'SELECTED_CANDIDATE.json', selection)
    save(OUT / 'CV_COMPARISON.json', all_summaries)
    save(OUT / 'CV_TERMINAL.json', {'status': '已验证通过', 'winner': winner, 'locked_labels_decoded': False,
          'reason': 'CV and dual final fits complete; wait for remote publication', 'time': original.utcnow()})
    compress_rows()
    publish_manifest('PRELOCKED', [ROOT / x['path'] for x in models.values()])
    original.note('Both final models and selection ready for remote publication; locked labels remain sealed')
    return 0


def inference_dataset(records):
    X = []; pools = []; offsets = [0]
    for row in records:
        features, pool = original.feature_rows({k: row[k] for k in original.ALLOWLIST})
        X.append(features); pools.append(pool); offsets.append(offsets[-1] + len(pool))
    return {'X': np.concatenate(X), 'pools': pools, 'offsets': offsets}


def predict_model(model, X):
    if 'constant_failure_probability' in model:
        return np.full(len(X), model['constant_failure_probability'])
    if model['mean'] is not None:
        X = (X - model['mean']) / model['scale']
    estimator = model['estimator']
    if model['config']['id'] == 'C03':
        return estimator.predict_proba(X)[:, list(estimator.classes_).index(1)]
    return estimator.predict(X)


def verify_locked_controls(records):
    ruler = original.import_repo_module('skills/prescreen/scripts/regret_ruler.py', 'locked_ruler')
    rescue = original.import_repo_module('project/tools/rescue_stats.py', 'locked_rescue')
    args = argparse.Namespace(group_map='0,1=5人;2,3=10人;4,5=20人', key='key', score='final_scores', ret='G_A', group='cell', cluster='episode', mode='target', chosen='chosen', mask_below=-1e8)
    states, groups, skipped = ruler.build(records, args)
    by_key = {s.rec['key']: s for s in states}; max_error = 0.0
    for row in records:
        m = original.reference_metrics(row, row['chosen'])
        if m['eligible_count'] >= 2:
            s = by_key[row['key']]
            error = max(abs(m['regret_base'] - (s.best - s.ret[s.base])), abs(m['regret_random'] - (s.best - s.ret[s.feas].mean())))
            assert error <= 1e-9; max_error = max(error, max_error)
        else:
            assert row['key'] not in by_key
        r = rescue.per_row(row)
        assert m['failure_base'] == r[0] and abs(m['failure_random'] - r[3]) <= 1e-9
    save(OUT / 'locked_controls.json', {'status': '已验证通过', 'roots': len(records), 'regret_roots': len(states),
         'single_eligible_skipped': skipped, 'maximum_absolute_difference': max_error, 'source_label_passes': 1})


def run_locked(receipt_path):
    ensure_budget()
    assert not (OUT / 'LOCKED_READ_STARTED.json').exists(), 'STOP: locked read already claimed; reread forbidden'
    verify_history()
    selection_path = OUT / 'SELECTED_CANDIDATE.json'
    selection = json.loads(selection_path.read_text())
    receipt = json.loads(Path(receipt_path).read_text())
    assert receipt['confirmed_by_parent'] is True and len(receipt['remote_commit']) == 40
    published = {i['path']: i['sha256'] for i in receipt['files']}
    required = [selection_path, Path(__file__), *[ROOT / x['path'] for x in selection['models'].values()]]
    for p in required:
        assert published[str(p.relative_to(ROOT))] == sha(p), 'STOP: artifact not confirmed at publication commit'
    assert selection['amended_source_sha256'] == sha(__file__)
    assert selection['episodes_csv_sha256'] == sha(FROZEN / 'episodes.csv')
    assert selection['candidate_list_sha256'] == sha(FROZEN / 'candidates.json')
    config = selection['selected_candidate']
    assert config in json.loads((FROZEN / 'candidates.json').read_text())['candidates']
    models = {}
    for arm, item in selection['models'].items():
        assert sha(ROOT / item['path']) == item['sha256']
        models[arm] = joblib.load(ROOT / item['path'])
        assert models[arm]['config'] == config
    assert set(models) == {'true', 'shuffle'}
    split = original.assignments()
    claim = {'time': original.utcnow(), 'publication_remote_commit': receipt['remote_commit'],
             'selection_sha256': sha(selection_path), 'models': selection['models'],
             'source_label_read_passes_permitted': 1, 'retry_after_claim_forbidden': True}
    exclusive_marker(OUT / 'LOCKED_READ_STARTED.json', claim)
    # The only outcome-decoding locked-table entry point. No other path loads this partition.
    with gzip.open(original.TABLE, 'rt', encoding='utf-8') as stream:
        records = original.filtered_records(stream, split, 'locked')
    assert len(records) == 420 and len({r['key'] for r in records}) == 420
    expected = {r[k] for r in split.values() if r['partition'] == 'locked' for k in ('key_1', 'key_2')}
    assert {r['key'] for r in records} == expected
    records.sort(key=lambda x: x['key'])
    verify_locked_controls(records)
    dataset = inference_dataset(records)
    summaries = {}; rows = {}
    for arm, model in models.items():
        ensure_budget()
        predicted = predict_model(model, dataset['X'])
        choices = original.choices_from_prediction(records, dataset, predicted, config)
        rows[arm] = [original.reference_metrics(r, c) for r, c in zip(records, choices)]
        with (OUT / ('locked_' + arm + '_rows.jsonl')).open('x') as stream:
            for row in rows[arm]:
                stream.write(json.dumps(row, ensure_ascii=False) + '\n')
        summaries[arm] = original.summarize(rows[arm], partition_code=1)
        save(OUT / ('locked_' + arm + '_summary.json'), summaries[arm])
    contrast = paired_contrast(rows['true'], rows['shuffle'], 1)
    save(OUT / 'locked_paired_true_minus_shuffle.json', contrast)
    primary = summaries['true']['20人']['episode_primary']
    verdict = adjudicate(primary, contrast['20人']['episode_primary'])
    result = {'status': '已验证通过', 'verdict': verdict, 'selected_candidate': config['id'],
              'twenty_person_primary': primary, 'twenty_person_paired': contrast['20人']['episode_primary'],
              'source_label_read_passes': 1, 'publication_remote_commit': receipt['remote_commit'],
              'no_further_locked_reads_or_fits': True, 'time': original.utcnow(),
              'limitations': ['Post-CV user amendment', 'Single training seed', 'Scalar inputs only',
                             'Historical stage0 aggregate exposure', 'Mother-policy continuation, no closed-loop claim']}
    save(OUT / 'LOCKED_TERMINAL.json', result)
    publish_manifest('FINAL', [ROOT / x['path'] for x in selection['models'].values()])
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['test', 'cv', 'locked'])
    parser.add_argument('--note-commit'); parser.add_argument('--publication-receipt')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True); (OUT / 'logs').mkdir(exist_ok=True)
    with threadpool_limits(limits=2):
        if args.mode == 'test':
            amended_tests(); return 0
        if args.mode == 'cv':
            return run_cv(args.note_commit or '')
        return run_locked(args.publication_receipt)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        marker = 'LOCKED_ABORTED.json' if (OUT / 'LOCKED_READ_STARTED.json').exists() else 'ABORTED.json'
        save(OUT / marker, {'status': '已确认失败', 'error': type(error).__name__ + ': ' + str(error),
             'locked_read_claimed': (OUT / 'LOCKED_READ_STARTED.json').exists(), 'time': original.utcnow()})
        raise
