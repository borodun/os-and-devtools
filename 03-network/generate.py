#!/usr/bin/env python3
import subprocess

COMPOSE = """\
services:
  you:
    image: nicolaka/netshoot
    container_name: you
    cap_add:
      - NET_ADMIN
    command: sh -c "ip addr flush dev eth0 2>/dev/null; ip route del default 2>/dev/null; ip route add 172.30.2.0/24 via 172.30.1.99 dev eth0 onlink 2>/dev/null; exec sleep infinity"
    networks:
      net-a:
        ipv4_address: 172.30.1.10
  node:
    image: nicolaka/netshoot
    container_name: node
    environment:
      NODE_IP: 172.30.1.20
      GW_IP: 172.30.1.254
    command: python3 /opt/svcs/node.py
    volumes:
      - ./scenario:/opt/svcs:ro
    networks:
      net-a:
        ipv4_address: 172.30.1.20
  dummy-1:
    image: nicolaka/netshoot
    container_name: dummy-1
    command: sleep infinity
    networks:
      net-a:
        ipv4_address: 172.30.1.41
  dummy-2:
    image: nicolaka/netshoot
    container_name: dummy-2
    command: sleep infinity
    networks:
      net-a:
        ipv4_address: 172.30.1.42
  dummy-3:
    image: nicolaka/netshoot
    container_name: dummy-3
    command: sleep infinity
    networks:
      net-a:
        ipv4_address: 172.30.1.43
  core:
    image: nicolaka/netshoot
    container_name: core
    privileged: true
    command: sh -c "sysctl -w net.ipv4.ip_forward=1; iptables -A FORWARD -d 172.30.2.30 -p udp --dport 9009 -m statistic --mode nth --every 3 --packet 1 -j DROP; iptables -A FORWARD -d 172.30.2.31 -p tcp --dport 9010 -m statistic --mode nth --every 3 --packet 1 -j DROP; exec sleep infinity"
    volumes:
      - ./scenario:/opt/svcs:ro
    networks:
      net-a:
        ipv4_address: 172.30.1.254
      net-c:
        ipv4_address: 172.30.2.254
  web:
    image: nicolaka/netshoot
    container_name: web
    cap_add:
      - NET_ADMIN
    command: sh -c "for i in 1 2 3 4 5 6 7 8; do ip route replace default via 172.30.2.254 dev eth0 2>/dev/null; sleep 0.5; done; exec python3 /opt/svcs/web.py"
    volumes:
      - ./scenario:/opt/svcs:ro
    networks:
      net-c:
        ipv4_address: 172.30.2.10
  dnsd:
    image: nicolaka/netshoot
    container_name: dnsd
    cap_add:
      - NET_ADMIN
    command: sh -c "for i in 1 2 3 4 5 6 7 8; do ip route replace default via 172.30.2.254 dev eth0 2>/dev/null; sleep 0.5; done; exec python3 /opt/svcs/dnsd.py"
    volumes:
      - ./scenario:/opt/svcs:ro
    networks:
      net-c:
        ipv4_address: 172.30.2.20
  msg-u:
    image: nicolaka/netshoot
    container_name: msg-u
    cap_add:
      - NET_ADMIN
    command: sh -c "for i in 1 2 3 4 5 6 7 8; do ip route replace default via 172.30.2.254 dev eth0 2>/dev/null; sleep 0.5; done; exec python3 /opt/svcs/msgu.py"
    volumes:
      - ./scenario:/opt/svcs:ro
    networks:
      net-c:
        ipv4_address: 172.30.2.30
  msg-t:
    image: nicolaka/netshoot
    container_name: msg-t
    cap_add:
      - NET_ADMIN
    command: sh -c "for i in 1 2 3 4 5 6 7 8; do ip route replace default via 172.30.2.254 dev eth0 2>/dev/null; sleep 0.5; done; exec python3 /opt/svcs/msgt.py"
    volumes:
      - ./scenario:/opt/svcs:ro
    networks:
      net-c:
        ipv4_address: 172.30.2.31
networks:
  net-a:
    ipam:
      config:
        - subnet: 172.30.1.0/24
  net-c:
    ipam:
      config:
        - subnet: 172.30.2.0/24
"""


def main():
    with open("compose.yaml", "w") as f:
        f.write(COMPOSE)
    print("compose.yaml готов. Поднимаю стенд…")
    subprocess.run(["docker", "compose", "up", "-d"], check=False)
    print(
        "Стенд поднят. Дальше:\n"
        "  1. docker compose exec you sh\n"
        "  2. работай по README.md\n"
        "  3. когда закончишь: python3 check.py\n"
        "  4. ПОСЛЕ СДАЧИ ОБЯЗАТЕЛЬНО: python3 clean.py (иначе контейнеры останутся запущенными)"
    )


if __name__ == "__main__":
    main()
