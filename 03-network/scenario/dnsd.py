#!/usr/bin/env python3
import os
import secrets
import socket
import struct

STATEDIR = "/var/lib/kampus"

tok = secrets.token_hex(4)
os.makedirs(STATEDIR, exist_ok=True)
with open(os.path.join(STATEDIR, "tok"), "w") as f:
    f.write(tok)

ZONE = "osi.local"
A = {
    "web." + ZONE: "172.30.2.10",
    "dns." + ZONE: "172.30.2.20",
    ZONE: "172.30.2.10",
}
CNAME = {
    "vault." + ZONE: "web." + ZONE,
}
TXT = {
    "key." + ZONE: "FLAG{172.30.2.10-%s}" % tok,
}


def parse_name(buf, off):
    labels = []
    jumps = 0
    while True:
        l = buf[off]
        if l == 0:
            off += 1
            break
        if l & 0xC0:
            off += 2
            if jumps == 0:
                ptr = struct.unpack(">H", buf[off - 2 : off])[0] & 0x3FFF
                sub, _ = parse_name(buf, ptr)
                labels.append(sub)
                jumps += 1
            continue
        labels.append(buf[off + 1 : off + 1 + l].decode())
        off += 1 + l
        jumps += 1
    return ".".join(labels), off


def wire(name):
    if name == ZONE:
        return b"\x03osi\x05local\x00"
    parts = name.rstrip(".").split(".")
    return b"".join(bytes([len(p)]) + p.encode() for p in parts) + b"\x00"


def rr(name, rtype, rdata):
    return wire(name) + struct.pack(">HHHI", rtype, 1, 60, len(rdata)) + rdata


def answer_a(name):
    out = []
    if name in CNAME:
        t = CNAME[name]
        out.append(rr(name, 5, wire(t)))
        out.append(rr(t, 1, socket.inet_aton(A[t])))
    elif name in A:
        out.append(rr(name, 1, socket.inet_aton(A[name])))
    return out


def answer_txt(name):
    if name in TXT:
        val = TXT[name].encode()
        return [rr(name, 16, bytes([len(val)]) + val)]
    return []


def reply(qid, question, answers):
    head = struct.pack(">HHHHHH", qid, 0x8580, 1, len(answers), 0, 0)
    return head + question + b"".join(answers)


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", 53))

while True:
    buf, addr = s.recvfrom(1024)
    qid = struct.unpack(">H", buf[0:2])[0]
    name, off = parse_name(buf, 12)
    qtype = struct.unpack(">H", buf[off : off + 2])[0]
    question = buf[12 : off + 4]
    name = name.lower()
    if qtype == 1:
        answers = answer_a(name)
    elif qtype == 16:
        answers = answer_txt(name)
    else:
        answers = []
    s.sendto(reply(qid, question, answers), addr)
