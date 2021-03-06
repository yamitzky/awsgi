import base64
from io import StringIO, BytesIO
import sys
try:
    # Python 3
    from urllib.parse import urlencode

    # Convert bytes to str, if required
    def convert_str(s):
        return s.decode('utf-8') if isinstance(s, bytes) else s
except:
    # Python 2
    from urllib import urlencode

    # No conversion required
    def convert_str(s):
        return s


def response(app, event, context):
    sr = StartResponse()
    output = app(environ(event, context), sr)
    return sr.response(output)


class StartResponse:
    def __init__(self):
        self.status = 500
        self.headers = []
        self.body = StringIO()

    def __call__(self, status, headers, exc_info=None):
        self.status = status.split()[0]
        self.headers[:] = headers
        return self.body.write

    def response(self, output):
        headers = dict(self.headers)
        ret = {
            'statusCode': str(self.status),
            'headers': headers,
        }
        ct = headers.get('Content-Type', '')
        if (headers.get('Content-Encoding') == 'gzip'
                or (not ct.startswith("text/") and ct != "application/json")):
            ret['body'] = base64.b64encode(
                self.body.getvalue().encode('utf-8') + b''.join(output)).decode('utf-8')
            ret["isBase64Encoded"] = "true"
        else:
            ret['body'] = self.body.getvalue() + ''.join(map(convert_str, output))
        return ret


def environ(event, context):
    if event.get('isBase64Encoded'):
        body = base64.b64decode(event.get('body', ''))
    else:
        body = (event.get('body', '') or '').encode('utf-8')
    environ = {
        'REQUEST_METHOD': event['httpMethod'],
        'SCRIPT_NAME': '',
        'PATH_INFO': event['path'],
        'QUERY_STRING': urlencode(event['queryStringParameters'] or {}),
        'REMOTE_ADDR': '127.0.0.1',
        'CONTENT_LENGTH': str(len(body)),
        'HTTP': 'on',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'REMOTE_ADDR': '127.0.0.1',
        'SERVER_NAME': 'awsgi',
        'SERVER_PORT': '80',
        'wsgi.url_scheme': 'http',
        'wsgi.version': (1, 0),
        'wsgi.input': BytesIO(body),
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
    }
    headers = event.get('headers', {}) or {}
    for k, v in headers.items():
        k = k.upper().replace('-', '_')

        if k == 'CONTENT_TYPE':
            environ['CONTENT_TYPE'] = v
        elif k == 'HOST':
            environ['SERVER_NAME'] = v
        elif k == 'X_FORWARDED_FOR':
            environ['REMOTE_ADDR'] = v.split(', ')[0]
        elif k == 'X_FORWARDED_PROTO':
            environ['wsgi.url_scheme'] = v
        elif k == 'X_FORWARDED_PORT':
            environ['SERVER_PORT'] = v

        environ['HTTP_' + k] = v

    return environ
