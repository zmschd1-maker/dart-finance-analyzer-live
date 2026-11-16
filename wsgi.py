"""
WSGI 엔트리포인트 — Vercel Python 런타임이 이 파일의 `app` 을 불러 요청을 전달한다.

원본 `app.py`(→ app_core.py)는 표준 라이브러리 `http.server.BaseHTTPRequestHandler`
기반 서버다. UI/기능은 한 줄도 바꾸지 않고, 여기서 원본 `Handler` 를 그대로 호출한
뒤 응답만 WSGI 형식으로 넘겨준다. (로컬에서는 기존처럼 `python app_core.py` 로 실행)
"""

import io
import traceback

import app_core
from app_core import Handler

# 원본 응답에서 걸러낼 헤더 (WSGI 계층이 직접 관리)
_SKIP_HEADERS = {
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailers', 'transfer-encoding', 'upgrade',
    'content-length', 'server', 'date',
}


class _StubServer:
    """BaseHTTPRequestHandler 가 참조할 수 있는 최소 서버 객체."""
    server_name = 'dart-finance-analyzer'
    server_port = 443
    allow_reuse_address = True


def _build_raw_request(environ):
    method = (environ.get('REQUEST_METHOD') or 'GET').upper()
    path = environ.get('PATH_INFO') or '/'
    if path != '/':
        path = path.rstrip('/') or '/'
    query = environ.get('QUERY_STRING') or ''
    target = path + ('?' + query if query else '')

    head = [f'{method} {target} HTTP/1.1']
    host_set = False
    for key, value in environ.items():
        if not key.startswith('HTTP_'):
            continue
        name = key[5:].replace('_', '-').title()
        if name.lower() in _SKIP_HEADERS:
            continue
        if name.lower() == 'host':
            host_set = True
        head.append(f'{name}: {value}')
    if not host_set:
        host = environ.get('SERVER_NAME') or 'localhost'
        head.append(f'Host: {host}')
    content_type = environ.get('CONTENT_TYPE')
    if content_type:
        head.append(f'Content-Type: {content_type}')
    content_length = environ.get('CONTENT_LENGTH') or ''
    if content_length:
        head.append(f'Content-Length: {content_length}')

    body = b''
    try:
        length = int(content_length) if content_length else 0
    except ValueError:
        length = 0
    if length > 0:
        stream = environ.get('wsgi.input')
        if stream is not None:
            body = stream.read(length) or b''

    raw = '\r\n'.join(head).encode('latin-1', 'replace') + b'\r\n\r\n' + body
    return raw


def _client_ip(environ):
    forwarded = environ.get('HTTP_X_FORWARDED_FOR') or ''
    if forwarded:
        return forwarded.split(',')[0].strip()
    return environ.get('REMOTE_ADDR') or '127.0.0.1'


def _ensure_corp_list(environ):
    """원본은 시작 시 상장사 목록을 미리 받아 둔다. 서버리스에서는 첫 검색 때 로드한다.
    (저장소에 번들된 스냅샷을 쓰므로 0.2초 수준)"""
    if app_core.CORP_LIST:
        return
    path = environ.get('PATH_INFO') or ''
    if path.rstrip('/') == '/api/search':
        app_core.load_corp_list()


def _run_original(environ):
    """원본 Handler 한 번 호출 → (status, reason, headers, body)."""
    _ensure_corp_list(environ)
    raw = _build_raw_request(environ)

    handler = Handler.__new__(Handler)
    handler.request = None
    handler.client_address = (_client_ip(environ), 0)
    handler.server = _StubServer()
    handler.rfile = io.BytesIO(raw)
    handler.wfile = io.BytesIO()
    handler.close_connection = True
    handler.protocol_version = 'HTTP/1.1'
    handler.request_version = 'HTTP/1.1'
    handler.command = None
    handler.path = None
    handler.requestline = ''
    handler.raw_requestline = b''
    handler.headers = None
    handler._headers_buffer = []

    handler.handle_one_request()
    raw_response = handler.wfile.getvalue()

    head, _, body = raw_response.partition(b'\r\n\r\n')
    lines = head.decode('latin-1', 'replace').split('\r\n') if head else []
    status, reason = 500, 'Internal Server Error'
    if lines:
        parts = lines[0].split(' ', 2)
        if len(parts) >= 2 and parts[1].isdigit():
            status = int(parts[1])
            reason = parts[2] if len(parts) > 2 else ''
    headers = []
    for line in lines[1:]:
        name, sep, value = line.partition(':')
        if not sep:
            continue
        if name.strip().lower() in _SKIP_HEADERS:
            continue
        headers.append((name.strip(), value.strip()))
    if not headers or not any(k.lower() == 'content-type' for k, _ in headers):
        headers.append(('Content-Type', 'application/json; charset=utf-8'))
    return status, reason, headers, body


def app(environ, start_response):
    try:
        status, reason, headers, body = _run_original(environ)
    except Exception:
        traceback.print_exc()
        status, reason = 500, 'Internal Server Error'
        headers = [('Content-Type', 'application/json; charset=utf-8')]
        body = '{"status":"error","message":"서버 내부 오류가 발생했습니다."}'.encode('utf-8')
    status_line = f'{status} {reason}'.strip()
    start_response(status_line, headers)
    return [body]
