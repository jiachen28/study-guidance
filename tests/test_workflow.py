import json
import tempfile
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from shutil import copyfile
from unittest import TestCase
from unittest.mock import patch
import run_study
from app import evaluation
from app import study

class CompleteWorkflowTests(TestCase):
    def test_annotation_dispute_final_results_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for sub in ['app','data','results']:(root/sub).mkdir()
            for source in ['core.py','policy.py','retrieval.py','evaluation.py','study.py']:
                copyfile(Path('app')/source,root/'app'/source)
            copyfile('data/knowledge.json',root/'data/knowledge.json')
            copyfile('data/scenarios.csv',root/'data/scenarios.csv')
            scenarios=study.read_csv('data/scenarios.csv')
            for participant_index,name in enumerate(study.NAMES):
                records=[]
                for item_index,scenario in enumerate(scenarios):
                    label=study.LABELS[item_index % len(study.LABELS)]
                    if participant_index == 1 and item_index == 0:
                        label='Research'
                    records.append({'id':scenario['id'], 'task':scenario['task'],
                                    'independent_label':label, 'reason':'Test fixture'})
                study.write_csv(root/'data'/f'annotations_{name}.csv',records,
                    ['id','task','independent_label','reason'])
            def model(payload):
                return {'response':json.dumps({'category':'Coding',
                    'explanation':'Coding task.',
                    'verification':'Test all changes.',
                    'limitations':'May be incorrect.'})}
            real_run=evaluation.run
            with patch.object(study,'ROOT',root), patch.object(run_study,'ROOT',root), \
                 patch.object(evaluation,'ROOT',root), \
                 patch.object(evaluation,'run',side_effect=lambda:real_run(transport=model)), redirect_stdout(StringIO()):
                self.assertEqual(run_study.main(),2)
                adj=root/'results/adjudication.csv'
                self.assertTrue(adj.exists())
                records=study.read_csv(adj)
                self.assertGreaterEqual(len(records),1)
                for row in records:
                    row['consensus_label']='Coding'
                    row['resolution_reason']='Fixture decision'
                study.write_csv(adj,records,run_study.ADJ_COLS)
                self.assertEqual(run_study.main(),0)
                self.assertTrue((root/'results/metrics.json').exists())
                self.assertEqual(len(study.read_csv(root/'results/evaluation_raw.csv')),20)
                self.assertEqual(len(study.read_csv(root/'results/consensus.csv')),60)
                self.assertEqual(len(study.read_csv(root/'results/case_analysis.csv')),20)
                for name in ('comparison.svg','confusion_model.svg','confusion_system.svg','per_class_f1.svg'):
                    self.assertIn('<svg',(root/'results'/name).read_text(encoding='utf-8'))
                metrics=json.loads((root/'results/metrics.json').read_text(encoding='utf-8'))
                self.assertEqual(metrics['annotation']['n'],60)
                self.assertEqual(metrics['ollama']['valid'],20)
                self.assertEqual(metrics['system']['n'],20)
