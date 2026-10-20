"""Annotation integrity, agreement, and classification metrics for the held-out set."""
import csv
from collections import Counter
from pathlib import Path
import json
import math
ROOT = Path(__file__).resolve().parents[1]
NAMES = ('Jiachen_Lu', 'Siyuan_Chen', 'Xin_Chen')
LABELS = ('Coding', 'Research', 'Workflow', 'None')

def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def write_csv(path, rows, columns):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

def verify_annotations(folder=ROOT):
    """Reject changed tasks/IDs, missing values and duplicate rows; no auto-filled labels."""
    folder = Path(folder)
    scenarios = read_csv(folder / 'data/scenarios.csv')
    ids = [s['id'] for s in scenarios]
    if len(ids) != 60 or len(set(ids)) != 60 or sum((s['split'] == 'heldout' for s in scenarios)) != 20:
        raise ValueError('Scenario dataset must contain 60 unique items, including 20 held-out tasks')
    out = {}
    for name in NAMES:
        path = folder / 'data' / f'annotations_{name}.csv'
        rows = read_csv(path)
        record = {r['id']: r for r in rows}
        if len(rows) != 60 or set(record) != set(ids):
            raise ValueError(f'{name}: task IDs are missing, duplicated or do not match the dataset')
        for s in scenarios:
            entry = record[s['id']]
            if entry.get('task') != s['task']:
                raise ValueError(f"{name}: scenario {s['id']} text differs from the dataset")
            label = (entry.get('independent_label') or '').strip()
            if label not in LABELS:
                raise ValueError(f"{name}: missing/invalid label for {s['id']}")
        out[name] = record
    return (scenarios, out)

def fleiss_kappa(scenarios, annot):
    """Fleiss' kappa for three annotators / four nominal categories."""
    n_annotators = len(NAMES)
    n_items = len(scenarios)
    counts = []
    for scenario in scenarios:
        values = [annot[name][scenario['id']]['independent_label'].strip() for name in NAMES]
        counts.append(Counter(values))
    per_item = [sum((n * (n - 1) for n in row.values())) / (n_annotators * (n_annotators - 1)) for row in counts]
    pbar = sum(per_item) / n_items
    props = [sum((row.get(label, 0) for row in counts)) / (n_items * n_annotators) for label in LABELS]
    expected = sum((p * p for p in props))
    return (pbar - expected) / (1 - expected) if expected < 1 else 1.0

def adjudication_rows(scenarios, annot, prior=None):
    prior = prior or {}
    agreements = []
    disagreements = []
    for s in scenarios:
        votes = [annot[name][s['id']]['independent_label'].strip() for name in NAMES]
        if len(set(votes)) == 1:
            agreements.append({'id': s['id'], 'task': s['task'], 'consensus_label': votes[0], 'reason': 'unanimous', 'agreement': 'unanimous'})
        else:
            existing = prior.get(s['id'], {})
            same = existing.get('task') == s['task'] and all((existing.get(name) == vote for name, vote in zip(NAMES, votes)))
            disagreements.append({'id': s['id'], 'task': s['task'], **dict(zip(NAMES, votes)), 'consensus_label': existing.get('consensus_label', '') if same else '', 'resolution_reason': existing.get('resolution_reason', '') if same else ''})
    return (agreements, disagreements)

def complete_consensus(scenarios, agreed, disagreed):
    outcome = list(agreed)
    for row in disagreed:
        label = row['consensus_label'].strip()
        reason = row['resolution_reason'].strip()
        if label not in LABELS or not reason:
            return None
        outcome.append({'id': row['id'], 'task': row['task'], 'consensus_label': label, 'reason': reason, 'agreement': 'adjudicated'})
    order = {s['id']: i for i, s in enumerate(scenarios)}
    return sorted(outcome, key=lambda r: order[r['id']])

def _safe_ratio(a, b):
    return a / b if b else 0.0

def classification_metrics(pairs):
    """Unavailable predictions count as errors, not as legitimate 'None' predictions."""
    n = len(pairs)
    valid = [(gold, pred) for gold, pred in pairs if pred in LABELS]
    correct = sum((a == b for a, b in pairs if b in LABELS))
    counts = {}
    for label in LABELS:
        tp = sum((a == label and b == label for a, b in pairs))
        fp = sum((a != label and b == label for a, b in pairs))
        fn = sum((a == label and b != label for a, b in pairs))
        precision = _safe_ratio(tp, tp + fp)
        recall = _safe_ratio(tp, tp + fn)
        counts[label] = {'support': sum((a == label for a, b in pairs)), 'tp': tp, 'fp': fp, 'fn': fn, 'precision': precision, 'recall': recall, 'f1': _safe_ratio(2 * precision * recall, precision + recall)}
    return {'n': n, 'valid': len(valid), 'coverage': _safe_ratio(len(valid), n), 'correct': correct, 'accuracy': _safe_ratio(correct, n), 'accuracy_on_valid': _safe_ratio(correct, len(valid)), 'macro_precision': sum((x['precision'] for x in counts.values())) / len(LABELS), 'macro_recall': sum((x['recall'] for x in counts.values())) / len(LABELS), 'macro_f1': sum((x['f1'] for x in counts.values())) / len(LABELS), 'by_class': counts, 'confusion': {gold: {pred: sum((a == gold and (b if b in LABELS else 'Unavailable') == pred for a, b in pairs)) for pred in (*LABELS, 'Unavailable')} for gold in LABELS}}

def report_metrics(scenarios, annotations, consensus, predictions):
    held = [s for s in scenarios if s['split'] == 'heldout']
    gold = {row['id']: row['consensus_label'] for row in consensus}
    raw = {row['id']: row for row in predictions}
    if len(predictions) != len(held) or set(raw) != {s['id'] for s in held}:
        raise ValueError('Final predictions must contain exactly 20 unique held-out scenario IDs')
    for s in held:
        if raw[s['id']].get('task') != s['task']:
            raise ValueError(f"Prediction scenario text mismatch: {s['id']}")
    metrics = {}
    for method, column in (('baseline', 'baseline'), ('ollama', 'llm_category'), ('system', 'system_category')):
        metrics[method] = classification_metrics([(gold[s['id']], raw[s['id']].get(column, '')) for s in held])
    unanimity = sum((len({annotations[name][s['id']]['independent_label'].strip() for name in NAMES}) == 1 for s in scenarios))
    metrics['annotation'] = {'n': len(scenarios), 'annotators': len(NAMES), 'unanimous': unanimity, 'unanimous_rate': unanimity / len(scenarios), 'fleiss_kappa': fleiss_kappa(scenarios, annotations)}
    metrics['study'] = {'heldout_n': len(held), 'categories': list(LABELS), 'models': 'qwen2.5:3b-instruct (locally hosted)', 'scope': 'project-authored evaluation scenarios; not a population-level accuracy estimate'}
    return metrics

def error_rows(scenarios, consensus, predictions):
    gold = {r['id']: r['consensus_label'] for r in consensus}
    return [{'id': r['id'], 'task': r['task'], 'reference_label': gold[r['id']], 'baseline_prediction': r.get('baseline', ''), 'model_prediction': r.get('llm_category', ''), 'system_prediction': r.get('system_category', ''), 'model_error': r.get('error', ''), 'model_correct': str(r.get('llm_category') == gold[r['id']]), 'system_correct': str(r.get('system_category') == gold[r['id']])} for r in predictions]
