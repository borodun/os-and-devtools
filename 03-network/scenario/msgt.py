#!/usr/bin/env python3
import os
import secrets
import socket
import threading

STATEDIR = "/var/lib/kampus"

tok = secrets.token_hex(4)
os.makedirs(STATEDIR, exist_ok=True)
with open(os.path.join(STATEDIR, "tok"), "w") as f:
    f.write(tok)

F4 = "FLAG{10of10-%s}" % tok


def handle(conn, addr):
    buf = b""
    n = 0
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            break
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            if not line.strip():
                continue
            n += 1
            conn.sendall(("msg-t. принято: %s\n" % line.decode(errors="replace").strip()).encode())
            if n == 10:
                conn.sendall(("msg-t. получено 10 из 10 — надёжный канал. " + F4 + "\n").encode())
                conn.close()
                return
    if n:
        conn.sendall(("msg-t. получено %d из 10, ждёт ещё.\n" % n).encode())
    conn.close()


def serve(port, handler):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port))
    s.listen(8)
    while True:
        conn, addr = s.accept()
        t = threading.Thread(target=handler, args=(conn, addr), daemon=True)
        t.start()


def ctl(conn, addr):
    conn.recv(1024)
    conn.sendall(F4.encode())
    conn.close()


threading.Thread(target=serve, args=(9011, ctl), daemon=True).start()
serve(9010, handle)
