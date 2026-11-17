#!/usr/bin/env python3
import http.server
import os
import secrets
import socket

STATEDIR = "/var/lib/kampus"
MSGT_HOST = ("172.30.2.31", 9011)

path8 = secrets.token_hex(4)
tok = secrets.token_hex(4)
os.makedirs(STATEDIR, exist_ok=True)
with open(os.path.join(STATEDIR, "path"), "w") as f:
    f.write(path8)
with open(os.path.join(STATEDIR, "tok"), "w") as f:
    f.write(tok)

F6 = "FLAG{%s-%s}" % (path8, tok)

LANDING = """<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>ОСИ</title></head>
<body>
<h1>ООО «ОСИ»</h1>
<p>Оператор сети кампуса.</p>
<p>Служебный вход: /%s</p>
</body>
</html>
""" % path8

_f4_cache = None


def get_f4():
    global _f4_cache
    if _f4_cache is None:
        s = socket.create_connection(MSGT_HOST, timeout=5)
        s.sendall(b"GET /flag HTTP/1.0\r\n\r\n")
        chunks = []
        while True:
            c = s.recv(4096)
            if not c:
                break
            chunks.append(c)
        s.close()
        _f4_cache = b"".join(chunks).decode().strip()
    return _f4_cache


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/":
            body = LANDING.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/" + path8:
            try:
                expected = get_f4()
            except Exception:
                self.send_response(500)
                self.end_headers()
                return
            got = self.headers.get("X-Handshake", "")
            if got.strip() == expected:
                body = ("доступ. фрагмент: " + F6 + "\n").encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(403)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True


Server(("0.0.0.0", 80), Handler).serve_forever()
