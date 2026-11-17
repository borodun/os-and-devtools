#!/usr/bin/env python3
import os
import secrets
import socket
import subprocess
import threading
import time

NODE_IP = os.environ.get("NODE_IP", "172.30.1.20")
GW_IP = os.environ.get("GW_IP", "172.30.1.254")
STATEDIR = "/var/lib/kampus"


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def own_mac():
    return sh("ip -br link show eth0").split()[2].lower()


def gw_mac():
    for _ in range(60):
        subprocess.run("ping -c1 -W1 %s >/dev/null 2>&1" % GW_IP, shell=True)
        line = sh("ip neigh show %s" % GW_IP)
        if "lladdr" in line:
            return line.split("lladdr")[1].split()[0].lower()
    raise SystemExit("gateway mac unresolved")


def peer_mac(ip):
    line = sh("ip neigh show %s" % ip)
    if "lladdr" in line:
        return line.split("lladdr")[1].split()[0].lower()
    return None


def norm(s):
    return s.strip().lower().replace(":", "").replace("-", "")


tokens = [secrets.token_hex(4) for _ in range(5)]
os.makedirs(STATEDIR, exist_ok=True)
with open(os.path.join(STATEDIR, "node.tok"), "w") as f:
    f.write("\n".join(tokens))

MY_MAC = own_mac()
GW_MAC = gw_mac()
F1 = "FLAG{%s-%s}" % (GW_IP, tokens[0])
F3 = "FLAG{%s-%s}" % (GW_IP, tokens[2])
B2 = "FLAG{7777-%s}" % (tokens[4])

state = {}
lock = threading.Lock()


def read_lines(conn, n, timeout=8.0):
    buf = b""
    conn.settimeout(timeout)
    while buf.count(b"\n") < n:
        try:
            chunk = conn.recv(4096)
        except socket.timeout:
            break
        if not chunk:
            break
        buf += chunk
    conn.settimeout(0.3)
    try:
        while True:
            extra = conn.recv(4096)
            if not extra:
                break
            buf += extra
    except socket.timeout:
        pass
    return [l for l in buf.decode(errors="replace").splitlines() if l.strip()]


def send(conn, text):
    conn.sendall((text + "\n").encode())


QUESTIONS = [
    ("node. в заметке передачи: кто у тебя шлюз по умолчанию? назови его ip (одной строкой).",
     1, 15.0),
    ("node. два вопроса о соседях: 1-й строкой — свой mac-адрес, 2-й строкой — mac-адрес шлюза.",
     2, 60.0),
    ("node. какой у тебя шлюз по умолчанию? назови ip.",
     1, 15.0),
    ("node. покажи, что видел в кадрах: mac-адрес отправителя и mac-адрес получателя кадра, летевшего ко мне, двумя строками (сначала отправитель, потом получатель).",
     2, 180.0),
]


def handle_main(conn, addr):
    ip = addr[0]
    pmac = peer_mac(ip)
    with lock:
        step = state.get(ip, 0)
    if step >= len(QUESTIONS):
        send(conn, "node. все вопросы получены.")
        conn.close()
        return
    question, nlines, timeout = QUESTIONS[step]
    send(conn, question)
    lines = read_lines(conn, nlines, timeout)
    if step == 0:
        ok = bool(lines) and lines[0].strip() == GW_IP
    elif step == 1:
        ok = (
            pmac is not None
            and len(lines) >= 2
            and norm(lines[0]) == norm(pmac)
            and norm(lines[1]) == norm(GW_MAC)
        )
    elif step == 2:
        ok = bool(lines) and lines[0].strip() == GW_IP
    else:
        ok = (
            pmac is not None
            and len(lines) >= 2
            and norm(lines[0]) == norm(pmac)
            and norm(lines[1]) == norm(MY_MAC)
        )
    if ok:
        if step == 0:
            send(conn, "верно. " + F1)
            send(conn, "следующий вопрос будет про соседей.")
        elif step == 1:
            send(conn, "верно. FLAG{%s-%s}" % (pmac, tokens[1]))
            send(conn, "следующий вопрос — про путь.")
        elif step == 2:
            send(conn, "верно. " + F3)
            send(conn, "этап 3 завершён. дальше — этапы 4–8.")
        else:
            send(conn, "вижу. FLAG{%s%s-%s}" % (pmac, MY_MAC, tokens[3]))
        with lock:
            state[ip] = step + 1
    elif lines:
        send(conn, "неверно. подключись и попробуй ещё раз.")
    else:
        send(conn, "время ожидания ответа истекло. подключись ещё раз и ответь быстрее.")
    conn.close()


def handle_back(conn, addr):
    conn.sendall((B2 + "\n").encode())
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


threading.Thread(target=serve, args=(7777, handle_back), daemon=True).start()
serve(8888, handle_main)
