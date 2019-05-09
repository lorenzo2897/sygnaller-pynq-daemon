#!/usr/bin/env python3

import http.server
import urllib.parse
import json
import uuid
import traceback

import transfer
import runtime
import compiler


class DaemonServer(http.server.BaseHTTPRequestHandler):

    def _error(self, err):
        return {
            'error': err
        }

    def api(self, command, data):
        if command == 'echo':
            return data

        elif command == 'ping':
            return {
                "ping": "pong",
                "mac": "%012X" % uuid.getnode(),
                "running": runtime.is_running()
            }

        elif command == 'upload_files':
            return transfer.upload_files(data)

        elif command == 'run_python':
            return runtime.run_python(data)

        elif command == 'stop_python':
            return runtime.stop_python()

        elif command == 'python_terminal':
            return runtime.terminal(data)

        elif command == 'clear_build_cache':
            return compiler.clear_cache(data)

        elif command == 'start_build':
            return compiler.run_build(data)

        elif command == 'get_build_progress':
            return compiler.get_build_status(data)

        else:
            return self._error('Command not supported')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', '*')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()


    def do_GET(self):
        try:
            command = urllib.parse.urlparse(self.path).path[1:]
            resp = self.api(command, {})
        except KeyError:
            resp = self._error('Missing data (use POST)')
        except Exception as e:
            print(type(e).__name__, e)
            resp = self._error('Server error')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(bytes(json.dumps(resp), encoding='utf-8'))
        self.wfile.write(b'\n')


    def do_POST(self):
        command = ''
        try:
            url_string = urllib.parse.urlparse(self.path)
            d_length = int(self.headers['content-length'])

            command = url_string.path[1:]
            if d_length == 0:
                data = None
            else:
                data = json.loads(self.rfile.read(d_length))

            resp = self.api(command, data)

        except json.decoder.JSONDecodeError:
            resp = self._error('Invalid JSON')

        except KeyError:
            resp = self._error('Missing data')

        except Exception as e:
            print(type(e).__name__, e)
            traceback.print_exc()
            resp = self._error('Server error (%s encountered %s)' % (command, type(e).__name__))

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(bytes(json.dumps(resp), encoding='utf-8'))
        self.wfile.write(b'\n')


def start_server(port=8000):
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, DaemonServer)
    print('Starting httpd on port %d...' % port)
    httpd.serve_forever()


if __name__ == '__main__':
    start_server()
