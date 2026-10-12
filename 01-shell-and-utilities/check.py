#!/usr/bin/env python3
import hashlib
import math
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
SERVER_DIR = ROOT / "server"
SEED_FILE = ROOT / ".seed"
ATTEMPT_FILE = ROOT / ".attempts"

MAX_ATTEMPTS = 1000

from scenario import (from_seed, WORLD_FILES, BAN_REASON,
                      expected_hacker_lines, expected_banlist, expected_conf)
from generate import build_server

TASK_MAX = {"t1": 6, "t2": 4, "t3": 5, "t4": 4, "t5": 4}
TOTAL = sum(TASK_MAX.values())


def half(x: float) -> float:
    return math.floor(x * 2) / 2


def read_lines(path: Path) -> list:
    if not path.exists():
        return []
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def ratio_score(points: float, expected: set, submitted: set) -> float:
    if not expected:
        return points
    hit = len(submitted & expected)
    return half(points * hit / max(len(expected), len(submitted)))


def task1(s, srv: Path):
    sub_nicks = sub_dump = 0
    det = []

    sus = read_lines(srv / "suspects.txt")
    if sus:
        expected = set(s.hackers)
        sub_nicks = ratio_score(3, expected, set(sus))
        det.append(f"ники хакеров: {sub_nicks:g}/3")
    else:
        det.append("suspects.txt не найден: 0/3")

    dump_exp = expected_hacker_lines(s)
    dump = read_lines(srv / "hacker_actions.log")
    if dump:
        sub_dump = ratio_score(3, dump_exp, set(dump))
        det.append(f"лог действий: {sub_dump:g}/3")
    else:
        det.append("hacker_actions.log не найден: 0/3")

    return sub_nicks + sub_dump, det


def task2(s, srv: Path):
    det = []
    score = 0
    ok = []
    for path in WORLD_FILES:
        p = srv / path
        try:
            good = p.exists() and p.read_text(encoding="utf-8") == s.file_content[path]
        except OSError:
            good = False
        if good:
            score += 1
            ok.append(path)
    det.append(f"файлы мира: {score}/4"
               + ("" if score == 4 else f" (на месте: {', '.join(ok) if ok else '—'})"))
    return score, det


def task3(s, srv: Path):
    lines = read_lines(srv / "users" / "banlist.txt")
    det = []
    score = 0

    need = [f"{h} {BAN_REASON}" for h in s.hackers]
    found = sum(1 for n in need if n in lines)
    sub = half(3 * found / len(need))
    score += sub
    det.append(f"забанено хакеров: {found}/{len(need)} ({sub:g}/3)")

    nicks = [l.split()[0] for l in lines if l.split()]
    dupes = len(nicks) - len(set(nicks))
    if not lines or dupes == 0:
        score += 1
        det.append("дубликаты: нет (1)")
    else:
        det.append(f"дубликаты: {dupes} (0)")

    if s.false_ban not in nicks:
        score += 1
        det.append("ложный бан снят (1)")
    else:
        det.append("ложный бан не снят (0)")

    return score, det


def parse_conf(path: Path) -> dict:
    conf = {}
    if not path.exists():
        return conf
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        conf[key.strip()] = value.strip()
    return conf


def task4(s, srv: Path):
    conf = parse_conf(srv / "conf" / "server.conf")
    det = []
    score = 0

    if conf.get("SERVER_NAME") == s.server_name:
        score += 1
    else:
        det.append("SERVER_NAME: неверно (0)")
    try:
        if int(conf.get("PORT", "x")) == s.port:
            score += 1
        else:
            det.append("PORT: неверно (0)")
    except ValueError:
        det.append("PORT: не число (0)")
    try:
        if int(conf.get("MAX_PLAYERS", "x")) == s.max_players:
            score += 1
        else:
            det.append("MAX_PLAYERS: неверно (0)")
    except ValueError:
        det.append("MAX_PLAYERS: не число (0)")
    try:
        parts = conf.get("SPAWN", "").split()
        if [int(p) for p in parts] == list(s.spawn):
            score += 1
        else:
            det.append("SPAWN: неверно (0)")
    except ValueError:
        det.append("SPAWN: не 3 целых (0)")

    if not det:
        det.append("конфиг восстановлен: 4/4")
    return score, det


def task5(s, srv: Path):
    p = srv / "server-started.ok"
    if p.exists() and p.read_text(encoding="utf-8").strip() == \
            f"OK {s.server_name} {s.port}":
        return 4, ["сервер запущен: 4/4"]
    return 0, ["сервер не запущен корректно: 0/4"]


def run_checks(s, srv: Path):
    results = {
        "t1": task1(s, srv), "t2": task2(s, srv), "t3": task3(s, srv),
        "t4": task4(s, srv), "t5": task5(s, srv),
    }
    titles = {
        "t1": "Задание 1. Кто они", "t2": "Задание 2. Восстановление",
        "t3": "Задание 3. Бан", "t4": "Задание 4. Конфигурация",
        "t5": "Задание 5. Запуск",
    }
    print("=" * 46)
    print('Квест "Ночная смена" — результат')
    print("=" * 46)
    total = 0
    for key in ("t1", "t2", "t3", "t4", "t5"):
        score, details = results[key]
        total += score
        print(f"{titles[key]}: {score:g}/{TASK_MAX[key]}")
        for d in details:
            print(f"  - {d}")
    print("-" * 46)
    print(f"ИТОГО: {total:g}/{TOTAL} ({total * 100 // TOTAL}%)")
    return total


def solve_reference(srv: Path, s) -> None:
    (srv / "suspects.txt").write_text("\n".join(s.hackers) + "\n", encoding="utf-8")
    lines = sorted(expected_hacker_lines(s))
    (srv / "hacker_actions.log").write_text("\n".join(lines) + "\n", encoding="utf-8")

    for path in WORLD_FILES:
        spot = s.moved[path]
        name = Path(path).name
        src = srv / spot / name
        dst = srv / path
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.replace(dst)

    (srv / "users" / "banlist.txt").write_text(
        "\n".join(expected_banlist(s)) + "\n", encoding="utf-8")
    (srv / "conf" / "server.conf").write_text(expected_conf(s), encoding="utf-8")

    r = subprocess.run(
        [sys.executable, str(srv / "bin" / "mcserver"),
         "--conf", "conf/server.conf"],
        cwd=srv, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"mcserver failed in reference: {r.stderr}")


def main():
    if "--reference" in sys.argv:
        i = sys.argv.index("--reference")
        seed = int(sys.argv[i + 1])
        with tempfile.TemporaryDirectory() as tmp:
            srv = Path(tmp) / "server"
            s = from_seed(seed)
            build_server(srv, s)
            solve_reference(srv, s)
            total = run_checks(s, srv)
        if total != TOTAL:
            print(f"!! эталонное решение получило {total}/{TOTAL}")
            sys.exit(1)
        print(f"reference OK: {TOTAL}/{TOTAL} (seed {seed})")
        return

    if not SEED_FILE.exists():
        print("Файл .seed не найден. Сначала запусти python3 generate.py")
        sys.exit(1)
    if not SERVER_DIR.exists():
        print("Директория server/ не найдена.")
        sys.exit(1)

    n_attempts = 0
    if ATTEMPT_FILE.exists():
        try:
            n_attempts = int(ATTEMPT_FILE.read_text().strip())
        except ValueError:
            n_attempts = 0
    if n_attempts >= MAX_ATTEMPTS:
        print(f"Попыток самопроверки больше {MAX_ATTEMPTS}: "
              "покажи результат преподавателю.")
        sys.exit(1)
    ATTEMPT_FILE.write_text(f"{n_attempts + 1}\n")

    s = from_seed(int(SEED_FILE.read_text().strip()))
    total = run_checks(s, SERVER_DIR)
    sig = hashlib.sha256(f"{s.seed}:{total}".encode()).hexdigest()[:8]
    print(f"Подпись для журнала: {sig}")


if __name__ == "__main__":
    main()
