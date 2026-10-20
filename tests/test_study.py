import csv
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from app.study import (LABELS,NAMES,read_csv,write_csv,verify_annotations,
    adjudication_rows,complete_consensus,fleiss_kappa,classification_metrics,report_metrics)
from app.evaluation import fingerprint,FIELDS

class StudyTests(unittest.TestCase):
    def test_real_dataset_structure(self):
        rows=read_csv('data/scenarios.csv')
        self.assertEqual(len(rows),60)
        self.assertEqual(len({r['task'] for r in rows}),60)
        self.assertEqual(sum(r['split']=='development' for r in rows),40)
        self.assertEqual(sum(r['split']=='heldout' for r in rows),20)
        self.assertNotIn('provisional_category',rows[0])
    def test_annotation_files_match_scenarios(self):
        scenarios={r['id']:r['task'] for r in read_csv('data/scenarios.csv')}
        for name in NAMES:
            rows=read_csv(f'data/annotations_{name}.csv')
            self.assertEqual(len(rows),60)
            self.assertEqual({r['id']:r['task'] for r in rows},scenarios)
    def test_team_annotation_schemas(self):
        for name in ('Siyuan_Chen','Xin_Chen'):
            a=read_csv(f'data/annotations_{name}.csv')
            self.assertEqual(len(a),60)
            self.assertTrue(all(r['independent_label'] in (*LABELS,'') for r in a))
    def test_missing_annotators_not_accepted(self):
        # Use a temporary copy so the check remains valid even after teammates fill in real labels.
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);(folder/'data').mkdir()
            copyfile('data/scenarios.csv',folder/'data/scenarios.csv')
            for name in NAMES:
                rows=read_csv(f'data/annotations_{name}.csv')
                if name=='Xin_Chen':rows[0]['independent_label']=''
                write_csv(folder/'data'/f'annotations_{name}.csv',rows,
                         ['id','task','independent_label','reason'])
            with self.assertRaisesRegex(ValueError,'missing/invalid'):
                verify_annotations(folder)
    def test_annotation_adjudication_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);(folder/'data').mkdir()
            copyfile('data/scenarios.csv',folder/'data/scenarios.csv')
            scenarios=read_csv('data/scenarios.csv')
            for i,name in enumerate(NAMES):
                records=[]
                for j,s in enumerate(scenarios):
                    label='Coding' if j%2==0 else 'Research'
                    if i==1 and j==0:label='Workflow'
                    records.append({'id':s['id'],'task':s['task'],'independent_label':label,'reason':'independent judgement'})
                write_csv(folder/'data'/f'annotations_{name}.csv',records,['id','task','independent_label','reason'])
            _,annotations=verify_annotations(folder)
            good,bad=adjudication_rows(scenarios,annotations)
            self.assertEqual(len(good),59)
            self.assertEqual(len(bad),1)
            self.assertIsNone(complete_consensus(scenarios,good,bad))
            bad[0]['consensus_label']='Coding';bad[0]['resolution_reason']='Shared assessment of primary task'
            final=complete_consensus(scenarios,good,bad)
            self.assertEqual(len(final),60)
            self.assertEqual(final[0]['consensus_label'],'Coding')
            self.assertGreaterEqual(fleiss_kappa(scenarios,annotations),0)
            prior={x['id']:x for x in bad}
            _,updated=adjudication_rows(scenarios,annotations,prior)
            self.assertEqual(updated[0]['consensus_label'],'Coding')
    def test_metrics_nonuniform(self):
        pairs=[('Coding','Coding'),('Research','None'),('Workflow',''),('None','None')]
        r=classification_metrics(pairs)
        self.assertEqual(r['n'],4)
        self.assertEqual(r['valid'],3)
        self.assertEqual(r['correct'],2)
        self.assertAlmostEqual(r['accuracy'],.5)
        self.assertAlmostEqual(r['coverage'],.75)
        self.assertEqual(r['confusion']['Workflow']['Unavailable'],1)
    def test_prediction_fingerprint(self):
        self.assertEqual(len(fingerprint()),20)
        self.assertEqual(fingerprint(),fingerprint())
    def test_http_heldout_prediction_fields(self):
        self.assertIn('system_category',FIELDS)
        self.assertIn('run_fingerprint',FIELDS)
