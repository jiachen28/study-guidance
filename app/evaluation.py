"""Reproducible inference for the study evaluation dataset."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from app.core import advise, MODEL
from app.study import LABELS, read_csv, write_csv
ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['id', 'task', 'baseline', 'llm_category', 'system_category', 'source', 'error', 'model', 'utc_timestamp', 'run_fingerprint', 'raw_response']

def fingerprint():
    assets = ('app/core.py', 'app/policy.py', 'app/retrieval.py', 'app/evaluation.py', 'app/study.py', 'data/knowledge.json', 'data/scenarios.csv')
    h = hashlib.sha256()
    for name in assets:
        h.update((ROOT / name).read_bytes())
    h.update(MODEL.encode('utf-8'))
    return h.hexdigest()[:20]

def run(*, fresh=False, transport=None):
    scenarios = [x for x in read_csv(ROOT / 'data/scenarios.csv') if x['split'] == 'heldout']
    if len(scenarios) != 20:
        raise ValueError('Expected 20 held-out scenarios')
    path = ROOT / 'results/evaluation_raw.csv'
    run_id = fingerprint()
    existing = {}
    if path.exists() and (not fresh):
        old = read_csv(path)
        if len({r['id'] for r in old}) == len(old) and all((r.get('run_fingerprint') == run_id and r.get('model') == MODEL for r in old)):
            existing = {r['id']: r for r in old}
        else:
            print('Previous evaluation uses different code/data; generating final results.', flush=True)
    outcomes = {}
    for i, s in enumerate(scenarios, 1):
        prev = existing.get(s['id'])
        if prev and prev['task'] == s['task']:
            outcomes[s['id']] = prev
            print(f"{i:02}/20 {s['id']}: existing observation retained", flush=True)
            continue
        try:
            result = advise(s['task'], transport=transport)
        except Exception as exc:
            raise RuntimeError(f"{s['id']} failed unexpectedly: {exc}") from exc
        outcomes[s['id']] = {'id': s['id'], 'task': s['task'], 'baseline': result['baseline_category'], 'llm_category': result['llm_category'] or '', 'system_category': result['category'], 'source': result['source'], 'error': result['model_error'] or '', 'model': MODEL, 'utc_timestamp': datetime.now(timezone.utc).isoformat(), 'run_fingerprint': run_id, 'raw_response': result['raw_response'] or ''}
        write_csv(path, [outcomes[x['id']] for x in scenarios if x['id'] in outcomes], FIELDS)
        print(f"{i:02}/20 {s['id']}: baseline={result['baseline_category']} model={result['llm_category'] or 'unavailable'} system={result['category']}", flush=True)
    rows = [outcomes[s['id']] for s in scenarios]
    write_csv(path, rows, FIELDS)
    valid = sum((r['llm_category'] in LABELS for r in rows))
    print(f'Final inference complete: {len(rows)}/20, valid model predictions: {valid}/20.')
    print('Results: results/evaluation_raw.csv')
    return rows

def main():
    parser = argparse.ArgumentParser(description='Run final held-out inference using a local Ollama model')
    parser.add_argument('--fresh', action='store_true', help='Deliberately replace the final evaluation with a new experimental run')
    args = parser.parse_args()
    try:
        run(fresh=args.fresh)
    except (ValueError, OSError) as exc:
        print('Evaluation could not finish:', str(exc))
        sys.exit(1)
if __name__ == '__main__':
    main()
