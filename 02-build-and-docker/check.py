#!/usr/bin/env python3
import json
import os
import stat
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
COMPOSE_FILE = ROOT / "compose.yaml"
COMPOSE_FILE_ALT = ROOT / "docker-compose.yaml"

CORE = []
BONUS = []


class Check:
    def __init__(self, key, title, bonus=False):
        self.key = key
        self.title = title
        self.bonus = bonus
        self.ok = None
        self.detail = ""

    def __call__(self):
        def deco(fn):
            fn()
            return self
        return deco


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), **kw)


def remove_file(path):
    try:
        path.chmod(0o644)
    except OSError:
        pass
    try:
        path.unlink()
    except OSError:
        pass


def compose_bin():
    return run(["docker", "compose", "version"])


# ---------------------------------------------------------------------------
# A. локальная сборка
# ---------------------------------------------------------------------------

def a_make_clean():
    c = Check("A1", "make clean выполняется без ошибок")
    r = run(["make", "clean"])
    c.ok = r.returncode == 0
    c.detail = "" if c.ok else r.stderr.strip().splitlines()[-1] if r.stderr else "код ошибки"
    CORE.append(c)


def a_make():
    c = Check("A2", "make из корня собирает проект")
    r = run(["make"])
    c.ok = r.returncode == 0
    c.detail = "" if c.ok else r.stderr.strip().splitlines()[-1] if r.stderr else "код ошибки"
    CORE.append(c)


def a_artifacts():
    c = Check("A3", "после make есть build/lib/libcommon.a и три исполняемых файла")
    needed = [
        ROOT / "build" / "lib" / "libcommon.a",
        ROOT / "apps" / "backend" / "backend",
        ROOT / "apps" / "balancer" / "balancer",
        ROOT / "apps" / "loadgen" / "loadgen",
    ]
    missing = [p.relative_to(ROOT).as_posix() for p in needed if not p.exists()]
    c.ok = not missing
    c.detail = "" if c.ok else "нет: " + ", ".join(missing)
    CORE.append(c)


def a_env_override():
    c = Check("A4", "Makefile берут CC и CFLAGS из окружения")
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "cc.log"
        wrapper = Path(tmp) / "cc"
        wrapper.write_text(
            "#!/bin/sh\necho \"$@\" >> " + str(log) + "\nexec gcc \"$@\"\n")
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)
        run(["make", "clean"])
        r = run(["make"], env={**os.environ,
                               "CC": str(wrapper), "CFLAGS": "-Wall -Werror"})
        if r.returncode != 0:
            c.ok = False
            c.detail = "сборка с заданными CC/CFLAGS завершилась ошибкой"
        elif not log.exists() or "-Wall" not in log.read_text():
            c.ok = False
            c.detail = "CFLAGS из окружения не попали в вызовы компилятора"
        else:
            c.ok = True
            c.detail = ""
        run(["make", "clean"])
        run(["make"])
    CORE.append(c)


# ---------------------------------------------------------------------------
# B. docker
# ---------------------------------------------------------------------------

def compose_file():
    if COMPOSE_FILE.exists():
        return COMPOSE_FILE
    if COMPOSE_FILE_ALT.exists():
        return COMPOSE_FILE_ALT
    return None


def compose(*args):
    return run(["docker", "compose", *args])


def compose_services():
    r = compose("config")
    if r.returncode != 0:
        return None, r.stderr.strip().splitlines()[-1] if r.stderr else ""
    try:
        cfg = json.loads(run(["docker", "compose", "config", "--format", "json"]).stdout)
        return cfg.get("services", {}), ""
    except (json.JSONDecodeError, IndexError):
        return None, "compose-файл не разбирается"


def compose_images():
    r = run(["docker", "compose", "config", "--images"])
    if r.returncode != 0:
        return []
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def b_compose():
    c = Check("B1", "compose-файл описывает все четыре сервиса")
    if compose_file() is None:
        c.ok = False
        c.detail = "compose.yaml не найден в корне проекта"
        CORE.append(c)
        return
    services, err = compose_services()
    if services is None:
        c.ok = False
        c.detail = err
    else:
        missing = [n for n in ("backend-1", "backend-2", "balancer", "loadgen")
                   if n not in services]
        c.ok = not missing
        c.detail = "" if c.ok else "нет сервисов: " + ", ".join(missing)
    CORE.append(c)


def ps_table():
    r = run(["docker", "compose", "ps", "--format", "json", "-a"])
    rows = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows


def published_ports(row):
    ports = []
    for pub in row.get("Publishers") or []:
        if pub.get("PublishedPort"):
            ports.append(pub["PublishedPort"])
    return ports


def b_images():
    c = Check("B2", "образы всех сервисов собраны")
    images = compose_images()
    if not images:
        c.ok = False
        c.detail = "образы не найдены"
        CORE.append(c)
        return
    missing = []
    for img in images:
        r = run(["docker", "image", "inspect", img])
        if r.returncode != 0:
            missing.append(img)
    c.ok = not missing
    c.detail = "" if c.ok else "не собраны: " + ", ".join(missing)
    CORE.append(c)


def b_multistage():
    c = Check("B3", "в финальных образах нет компилятора")
    images = compose_images()
    if not images:
        c.ok = False
        c.detail = "образы не собраны (см. B2)"
        CORE.append(c)
        return
    bad = []
    for img in images:
        r = run(["docker", "run", "--rm", img, "sh",
                 "-c", "command -v gcc || true"])
        if r.returncode == 0 and r.stdout.strip():
            bad.append(img)
    c.ok = not bad
    c.detail = "" if c.ok else "gcc найден в: " + ", ".join(bad)
    CORE.append(c)


def image_sizes():
    sizes = {}
    for img in compose_images():
        r = run(["docker", "image", "inspect", "--format", "{{.Size}}", img])
        if r.returncode == 0:
            try:
                sizes[img] = int(r.stdout.strip())
            except ValueError:
                pass
    return sizes


def b_image_size():
    c = Check("B4", "размер финальных образов меньше 500 МБ")
    sizes = image_sizes()
    if not sizes:
        c.ok = False
        c.detail = "образы не собраны (см. B2)"
        CORE.append(c)
        return
    bad = {i: s for i, s in sizes.items() if s > 500 * 1024 * 1024}
    c.ok = not bad
    c.detail = "" if c.ok else "большие образы: " + ", ".join(
        f"{i} ({sz // (1024 * 1024)} МБ)" for i, sz in bad.items())
    CORE.append(c)


def ps_by_service():
    by = {}
    for row in ps_table():
        by.setdefault(row.get("Service", ""), []).append(row)
    return by


def b_containers():
    c = Check("B5", "контейнеры запущены (backend-1, backend-2, balancer работают, loadgen отработал)")
    by = ps_by_service()
    problems = []
    for name in ("backend-1", "backend-2", "balancer"):
        rows = by.get(name, [])
        if not any(r.get("State") == "running" for r in rows):
            problems.append(name)
    lg = by.get("loadgen", [])
    if not lg:
        problems.append("loadgen")
    elif not any(
            r.get("State") == "running"
            or (r.get("State") == "exited" and r.get("ExitCode") == 0)
            for r in lg):
        codes = sorted({r.get("ExitCode") for r in lg if r.get("State") == "exited"})
        problems.append(f"loadgen (код выхода {codes or '—'})")
    c.ok = not problems
    c.detail = "" if c.ok else (
        "не запущены: " + ", ".join(problems)
        if any(r.get("State") for r in ps_table()) else "контейнеры не запускались")
    CORE.append(c)


def b_ports():
    c = Check("B6", "наружу опубликован только порт 8080 (balancer)")
    by = ps_by_service()
    problems = []
    for name in ("backend-1", "backend-2", "loadgen"):
        ports = set()
        for row in by.get(name, []):
            ports.update(published_ports(row))
        if ports:
            problems.append(f"{name} публикует порты {sorted(ports)}")
    bal_rows = by.get("balancer", [])
    bal_ports = set()
    for row in bal_rows:
        bal_ports.update(published_ports(row))
    if not any(r.get("State") == "running" for r in bal_rows):
        problems.append("balancer не запущен")
    elif 8080 not in bal_ports:
        problems.append("у balancer не опубликован порт 8080")
    c.ok = not problems
    c.detail = "" if c.ok else "; ".join(problems)
    CORE.append(c)


def b_round_robin():
    c = Check("B7", "балансировщик чередует ответы двух backend (200)")
    names = []
    statuses = []
    for _ in range(8):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080/", timeout=5) as resp:
                statuses.append(resp.status)
                names.append(resp.headers.get("X-Backend", ""))
        except Exception as e:
            c.ok = False
            c.detail = f"запрос к balancer не удался: {e.__class__.__name__}"
            CORE.append(c)
            return
    if any(s != 200 for s in statuses):
        c.ok = False
        c.detail = f"есть ответы не 200: {statuses}"
    elif set(names) != {"backend-1", "backend-2"}:
        c.ok = False
        c.detail = f"ответы пришли только от: {sorted(set(n for n in names if n)) or ['?']}"
    else:
        c.ok = True
    CORE.append(c)


def b_csv():
    c = Check("B8", "results/result.csv: 1001 строка, верный заголовок, 200, оба backend")
    p = ROOT / "results" / "result.csv"
    if not p.exists():
        c.ok = False
        c.detail = "файл results/result.csv не найден"
        CORE.append(c)
        return
    lines = p.read_text(encoding="utf-8").splitlines()
    if len(lines) != 1001:
        c.ok = False
        c.detail = f"строк: {len(lines)}, ожидается 1001"
        CORE.append(c)
        return
    if lines[0] != "request_id,backend,latency_ms,status":
        c.ok = False
        c.detail = f"заголовок: {lines[0]!r}"
        CORE.append(c)
        return
    rows = [l.split(",") for l in lines[1:]]
    bad_status = [r for r in rows if len(r) != 4 or r[3] != "200"]
    backends = {r[1] for r in rows if len(r) == 4}
    if bad_status:
        c.ok = False
        c.detail = f"строк со статусом не 200: {len(bad_status)}"
    elif backends != {"backend-1", "backend-2"}:
        c.ok = False
        c.detail = f"backend в CSV: {sorted(backends)}"
    else:
        c.ok = True
    CORE.append(c)


def b_no_rebuild():
    c = Check("B9", "loadgen запускается повторно без пересборки (REQUEST_COUNT=100 -> 101 строка)")
    if compose_file() is None:
        c.ok = False
        c.detail = "compose.yaml не найден"
        CORE.append(c)
        return
    out = ROOT / "results" / "check100.csv"
    remove_file(out)
    r = run(["docker", "compose", "run", "--rm", "--no-deps",
             "-e", "REQUEST_COUNT=100", "-e", "OUTPUT_FILE=/results/check100.csv",
             "loadgen"])
    if r.returncode != 0:
        c.ok = False
        last = r.stderr.strip().splitlines()
        c.detail = last[-1] if last else "запуск loadgen завершился ошибкой"
    elif not out.exists():
        c.ok = False
        c.detail = "results/check100.csv не создан"
    else:
        n = len(out.read_text(encoding="utf-8").splitlines())
        c.ok = n == 101
        c.detail = "" if c.ok else f"строк: {n}, ожидается 101"
    remove_file(out)
    CORE.append(c)


# ---------------------------------------------------------------------------
# B*. бонус
# ---------------------------------------------------------------------------

def x_healthcheck():
    c = Check("B1", "бонус: backend со status healthy, balancer ждёт здоровье", bonus=True)
    by = ps_by_service()
    problems = []
    for name in ("backend-1", "backend-2"):
        rows = by.get(name, [])
        if not any(r.get("State") == "running" and r.get("Health") == "healthy"
                   for r in rows):
            problems.append(f"{name} не healthy")
    services, _ = compose_services() or ({}, "")
    bal = services.get("balancer", {}) if services else {}
    dep = bal.get("depends_on", {})
    if isinstance(dep, dict):
        bad = [k for k, v in dep.items()
               if isinstance(v, dict) and v.get("condition") != "service_healthy"]
        if "backend-1" in dep or "backend-2" in dep:
            if any(k in ("backend-1", "backend-2") for k in bad):
                problems.append("у balancer нет depends_on condition: service_healthy")
        else:
            problems.append("balancer не зависит от backend")
    elif isinstance(dep, list) and dep:
        problems.append("balancer зависит от backend без условия service_healthy")
    else:
        problems.append("balancer не зависит от backend")
    c.ok = not problems
    c.detail = "; ".join(problems)
    BONUS.append(c)


def x_small_image():
    c = Check("B2", "бонус: все финальные образы меньше 150 МБ", bonus=True)
    sizes = image_sizes()
    if not sizes:
        c.ok = False
        c.detail = "образы не собраны"
    else:
        bad = {i: s for i, s in sizes.items() if s > 150 * 1024 * 1024}
        c.ok = not bad
        c.detail = "" if c.ok else ", ".join(
            f"{i} ({sz // (1024 * 1024)} МБ)" for i, sz in bad.items())
    BONUS.append(c)


def x_env_file():
    c = Check("B3", "бонус: .env в корне и подстановка переменных в compose-файле", bonus=True)
    env = ROOT / ".env"
    cf = compose_file()
    problems = []
    if not (env.exists() and env.read_text(encoding="utf-8").strip()):
        problems.append(".env отсутствует или пуст")
    if cf is None:
        problems.append("compose-файл не найден")
    else:
        text = cf.read_text(encoding="utf-8")
        if "${" not in text:
            problems.append("в compose-файле нет подстановки ${...}")
    c.ok = not problems
    c.detail = "; ".join(problems)
    BONUS.append(c)


# ---------------------------------------------------------------------------

def main():
    a_make_clean()
    a_make()
    a_artifacts()
    a_env_override()
    b_compose()
    b_images()
    b_multistage()
    b_image_size()
    b_containers()
    b_ports()
    b_round_robin()
    b_csv()
    b_no_rebuild()
    x_healthcheck()
    x_small_image()
    x_env_file()

    core_ok = sum(1 for c in CORE if c.ok)
    bonus_ok = sum(1 for c in BONUS if c.ok)

    print("=" * 56)
    print("Лабораторная «Сборка и Docker» — самопроверка")
    print("=" * 56)
    for group, checks, title in (
        (None, [c for c in CORE], "Обязательные"),
        (None, BONUS, "Бонусные (сверх зачёта)"),
    ):
        print(f"--- {title} ---")
        for c in checks:
            mark = "OK " if c.ok else "НЕТ"
            line = f"[{c.key}] {mark}  {c.title}"
            print(line)
            if not c.ok and c.detail:
                print(f"       {c.detail}")
    print("-" * 56)
    verdict = "ЗАЧЁТ" if core_ok == len(CORE) else f"НЕ ЗАЧЁТ ({len(CORE) - core_ok} пунктов не выполнены)"
    print(f"Обязательные: {core_ok}/{len(CORE)}  —  {verdict}")
    print(f"Бонусные: {bonus_ok}/{len(BONUS)}")
    sys.exit(0 if core_ok == len(CORE) else 1)


if __name__ == "__main__":
    main()
