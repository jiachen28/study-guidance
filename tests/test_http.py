import http.client
import json
from threading import Thread
import unittest
from unittest.mock import patch
from app.server import create_server

class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=create_server('127.0.0.1',0)
        cls.port=cls.server.server_address[1]
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(2)
    def call(self,method,path,data=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=3)
        headers={'Content-Type':'application/json'} if data is not None else {}
        conn.request(method,path,body=json.dumps(data) if data is not None else None,headers=headers)
        r=conn.getresponse();content=r.read();status=r.status;head=dict(r.getheaders());conn.close()
        return status,content,head
    def test_home(self):
        status,content,head=self.call('GET','/')
        self.assertEqual(status,200)
        self.assertIn(b'Get recommendation',content)
        self.assertIn('Content-Security-Policy',head)
    def test_styles(self):
        code,body,_=self.call('GET','/static/styles.css')
        self.assertEqual(code,200);self.assertIn(b'.workspace',body)
    def test_js(self):
        code,body,_=self.call('GET','/static/app.js')
        self.assertEqual(code,200);self.assertIn(b'textContent',body)
    def test_health(self):
        code,body,_=self.call('GET','/api/health')
        self.assertEqual(code,200);self.assertEqual(json.loads(body)['status'],'ok')
    def test_bad_input(self):
        code,body,_=self.call('POST','/api/advise',{'task':''})
        self.assertEqual(code,400)
    def test_valid_api(self):
        with patch('app.server.advise') as a:
            a.return_value={'category':'Coding','raw_response':'sensitive','tool':{'title':'Coding'}}
            code,body,_=self.call('POST','/api/advise',{'task':'Python debugging'})
            self.assertEqual(code,200)
            data=json.loads(body)
            self.assertEqual(data['category'],'Coding')
            self.assertNotIn('raw_response',data)
    def test_unregistered_path(self):
        status,_,_=self.call('GET','/../../data/annotations_Jiachen_Lu.csv')
        self.assertEqual(status,404)
