#!/usr/bin/env python3
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
GW_IP = "172.30.1.254"
MUST = ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8"]


def docker_inspect(name, net=None):
    out = subprocess.run(
        ["docker", "inspect", name], capture_output=True, text=True
    ).stdout
    if not out.strip():
        return None
    import json

    d = json.loads(out)[0]
    nets = d["NetworkSettings"]["Networks"]
    if net is None:
        net = next(iter(nets))
    try:
        return nets[net]["MacAddress"].lower()
    except (KeyError, StopIteration):
        return None


def ctr_file(name, path):
    r = subprocess.run(
        ["docker", "compose", "exec", "-T", name, "cat", path],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def norm(s):
    return (s or "").strip().lower()


def read_flags():
    d = {}
    if not os.path.exists("flags.txt"):
        return d
    for line in open("flags.txt"):
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        d[norm(k)] = norm(v)
    return d


def read_hints():
    used = {}
    if os.path.exists(".hints"):
        for line in open(".hints"):
            parts = line.split()
            if len(parts) == 2:
                s = parts[0].lower()
                t = int(parts[1])
                used[s] = max(used.get(s, 0), t)
    return used


def main():
    flags = read_flags()
    hints = read_hints()

    mac_you = docker_inspect("you")
    mac_node = docker_inspect("node")
    node_toks = ctr_file("node", "/var/lib/kampus/node.tok")
    msgt_tok = ctr_file("msg-t", "/var/lib/kampus/tok")
    dns_tok = ctr_file("dnsd", "/var/lib/kampus/tok")
    web_tok = ctr_file("web", "/var/lib/kampus/tok")
    web_path = ctr_file("web", "/var/lib/kampus/path")

    expected = {}
    if mac_you and node_toks:
        t = node_toks.splitlines()
        expected["f1"] = "flag{%s-%s}" % (GW_IP, t[0])
        expected["f2"] = "flag{%s-%s}" % (mac_you, t[1])
        expected["f3"] = "flag{%s-%s}" % (GW_IP, t[2])
        expected["f7"] = "flag{%s%s-%s}" % (mac_you, mac_node, t[3])
        expected["f8"] = "flag{7777-%s}" % t[4]
    if msgt_tok:
        expected["f4"] = "flag{10of10-%s}" % msgt_tok
    if dns_tok:
        expected["f5"] = "flag{172.30.2.10-%s}" % dns_tok
    if web_tok and web_path:
        expected["f6"] = "flag{%s-%s}" % (web_path, web_tok)

    if not expected:
        print("не могу пересчитать фрагменты: стенд не запущен?")
        sys.exit(1)

    solved = {k: flags.get(k) == v for k, v in expected.items()}
    all_must = all(solved.get(k, False) for k in MUST)

    hint_by_must = {k: hints.get(k[1:], 0) for k in MUST}

    print("Кампус — проверка")
    for k in MUST:
        print(
            "  %-2s %s"
            % (k, "выполнено" if solved.get(k, False) else "не выполнено")
            + ("  (подсказки: %d)" % hint_by_must[k] if hint_by_must[k] else "")
        )

    if all_must:
        m = max(hint_by_must.values())
        if m <= 1:
            grade = 5
        elif m <= 2:
            grade = 4
        else:
            grade = 3
    else:
        grade = 2
    print("Оценка: %d" % grade)


if __name__ == "__main__":
    main()
