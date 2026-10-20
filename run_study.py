"""Generate group consensus, evaluation metrics, and report figures."""
from pathlib import Path
import json
import sys
from app.figures import comparison, confusion, per_class
from app.study import NAMES, LABELS, ROOT, read_csv, write_csv, verify_annotations, adjudication_rows, complete_consensus, report_metrics, error_rows
ADJ_COLS = ['id', 'task', *NAMES, 'consensus_label', 'resolution_reason']
GOLD_COLS = ['id', 'task', 'consensus_label', 'reason', 'agreement']
ERROR_COLS = ['id', 'task', 'reference_label', 'baseline_prediction', 'model_prediction', 'system_prediction', 'model_error', 'model_correct', 'system_correct']

def main():
    print('Study evaluation')
    try:
        scenarios, annotations = verify_annotations(ROOT)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        print(f'Human annotations not ready: {exc}')
        print('Each team member must independently complete all 60 labels in data/annotations_<name>.csv.')
        return 2
    print('Three-person annotation check: 180/180 valid labels.')
    path = ROOT / 'results/adjudication.csv'
    previous = {row['id']: row for row in read_csv(path)} if path.exists() else {}
    agreed, disagreements = adjudication_rows(scenarios, annotations, previous)
    if disagreements:
        write_csv(path, disagreements, ADJ_COLS)
        unresolved = [row['id'] for row in disagreements if row['consensus_label'] not in LABELS or not row['resolution_reason'].strip()]
        print(f'Unanimous: {len(agreed)}/60; disagreements: {len(disagreements)}.')
        if unresolved:
            print('Group discussion needed for:', ', '.join(unresolved))
            print('Complete the consensus_label and resolution_reason columns in results/adjudication.csv.')
            print('Then run the same command again. No model evaluation has been started.')
            return 2
    else:
        print('All 60 labels agree; no adjudication needed.')
    consensus = complete_consensus(scenarios, agreed, disagreements)
    if consensus is None:
        print('Incomplete group decisions. See results/adjudication.csv.')
        return 2
    write_csv(ROOT / 'results/consensus.csv', consensus, GOLD_COLS)
    print('Consensus ready; running held-out evaluation (one local model call per scenario).')
    from app.evaluation import run
    rows = run()
    metrics = report_metrics(scenarios, annotations, consensus, rows)
    out = ROOT / 'results'
    (out / 'metrics.json').write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    write_csv(out / 'case_analysis.csv', error_rows(scenarios, consensus, rows), ERROR_COLS)
    comparison(metrics, out / 'comparison.svg')
    confusion(metrics, out / 'confusion_model.svg', 'ollama')
    confusion(metrics, out / 'confusion_system.svg', 'system')
    per_class(metrics, out / 'per_class_f1.svg')
    lines = ['STUDY RESULTS', '==============', 'Evaluation set: 20 held-out authored scenarios', 'Consensus labels: three independent human annotations and recorded disagreement resolution', f"Unanimous initial agreement: {metrics['annotation']['unanimous']}/60", f"Fleiss kappa: {metrics['annotation']['fleiss_kappa']:.3f}", '']
    for key, name in [('baseline', 'Keyword baseline'), ('ollama', 'Local language model'), ('system', 'Guidance system')]:
        r = metrics[key]
        lines += [name, f"Correct: {r['correct']}/{r['n']}", f"Accuracy: {r['accuracy']:.3f}", f"Macro F1: {r['macro_f1']:.3f}", f"Coverage: {r['coverage']:.3f}", '']
    lines += ['INTERPRETATION', 'Models were evaluated on 20 authored, non-representative cases.', 'No conclusion about general population performance is justified by this sample.', 'A failed model output is counted as an incorrect prediction.', 'Check individual errors in case_analysis.csv.', '', 'Figures: comparison.svg, confusion_model.svg, confusion_system.svg, per_class_f1.svg']
    (out / 'summary.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines[:20]))
    print('Saved: results/metrics.json, summary.txt, case_analysis.csv and four SVG figures.')
    return 0
if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        print(f'Could not complete the study: {exc}')
        sys.exit(1)
