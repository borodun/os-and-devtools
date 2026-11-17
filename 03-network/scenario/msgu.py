#!/usr/bin/env python3
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", 9009))

while True:
    data, addr = s.recvfrom(1024)
    msg = data.decode(errors="replace").strip()
    s.sendto(("msg-u. принято: %s\n" % msg).encode(), addr)
