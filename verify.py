"""One-command local installation and integration check; does not alter study data."""
from http.client import HTTPConnection
from threading import Thread
import json
import subprocess
import sys
from app.core import advise, MODEL
from app.server import create_server

def main():
    print('1/3  Automated tests', flush=True)
    run = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'], capture_output=True, text=True)
    if run.returncode:
        print(run.stdout, run.stderr)
        print('FAILED: automated tests')
        return 1
    count = next((line for line in run.stderr.splitlines() if line.startswith('Ran ')), 'Tests completed')
    print('PASS:', count, flush=True)
    print('2/3  Local web service', flush=True)
    server = create_server('127.0.0.1', 0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection('127.0.0.1', server.server_address[1], timeout=5)
        conn.request('GET', '/api/health')
        response = conn.getresponse()
        payload = json.loads(response.read())
        conn.close()
        if response.status != 200 or payload.get('status') != 'ok':
            print('FAILED: web service health check')
            return 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)
    print('PASS: HTTP health endpoint', flush=True)
    print(f'3/3  Local Ollama inference ({MODEL})', flush=True)
    result = advise('Please help debug a Python function and write unit tests.')
    if not result['llm_category']:
        print('Model check did not succeed:', result['model_error'])
        print('Confirm Ollama is open and the qwen2.5:3b-instruct model has been downloaded.')
        return 2
    print(f"PASS: model returned '{result['llm_category']}' and practical guidance.")
    print('READY: application and study workflow are operational.')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
