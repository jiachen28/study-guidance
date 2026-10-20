"""Single-process local HTTP server with a small JSON API and static UI."""
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse
from .core import advise, MAX_TASK, MODEL
STATIC = Path(__file__).parent / 'static'

class Handler(BaseHTTPRequestHandler):
    server_version = 'StudyGuidance/1.0'

    def _respond(self, code, body, kind='application/json; charset=utf-8'):
        payload = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'")
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/health':
            return self._respond(200, {'status': 'ok', 'model': MODEL, 'mode': 'local'})
        paths = {'/': ('index.html', 'text/html; charset=utf-8'), '/static/styles.css': ('styles.css', 'text/css; charset=utf-8'), '/static/app.js': ('app.js', 'application/javascript; charset=utf-8')}
        if path in paths:
            name, kind = paths[path]
            return self._respond(200, (STATIC / name).read_bytes(), kind)
        if path == '/favicon.ico':
            return self._respond(204, b'', 'image/x-icon')
        return self._respond(404, {'error': 'Not found'})

    def do_POST(self):
        if urlparse(self.path).path != '/api/advise':
            return self._respond(404, {'error': 'Not found'})
        try:
            n = int(self.headers.get('Content-Length', '0'))
            if n < 1 or n > 12000:
                return self._respond(413, {'error': 'Invalid request size'})
            obj = json.loads(self.rfile.read(n).decode('utf-8'))
            if not isinstance(obj, dict):
                raise ValueError('Expected a JSON object')
            task = obj.get('task')
            if not isinstance(task, str) or len(task) > MAX_TASK:
                raise ValueError('Please enter a task under 2500 characters')
            result = advise(task)
            result.pop('raw_response', None)
            return self._respond(200, result)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            return self._respond(400, {'error': str(exc)[:200]})
        except Exception:
            self.log_error('Unhandled request error')
            return self._respond(500, {'error': 'Unable to process the request'})

    def log_message(self, format, *args):
        if not str(args[0] if args else '').startswith('POST'):
            return super().log_message(format, *args)

def create_server(host='127.0.0.1', port=8765):
    return ThreadingHTTPServer((host, port), Handler)

def main():
    print('Study Guidance — http://127.0.0.1:8765', flush=True)
    print('Use Ctrl+C to stop.', flush=True)
    server = create_server()
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
if __name__ == '__main__':
    main()
