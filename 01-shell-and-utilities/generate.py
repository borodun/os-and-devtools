#!/usr/bin/env python3
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
ASSETS = ROOT / "assets"
SERVER_DIR = ROOT / "server"
SEED_FILE = ROOT / ".seed"

from scenario import Scenario, from_seed, broken_conf, WORLD_FILES


def read_or_create_seed() -> int:
    if SEED_FILE.exists():
        seed = int(SEED_FILE.read_text().strip())
    else:
        seed = int.from_bytes(os.urandom(4), "big") % 900_000 + 100_000
        SEED_FILE.write_text(f"{seed}\n")
    return seed


def build_server(server_dir: Path, s: Scenario) -> None:
    (server_dir / "bin").mkdir(parents=True, exist_ok=True)
    (server_dir / "conf").mkdir(parents=True, exist_ok=True)
    (server_dir / "data").mkdir(parents=True, exist_ok=True)
    (server_dir / "docs").mkdir(parents=True, exist_ok=True)
    (server_dir / "logs").mkdir(parents=True, exist_ok=True)
    (server_dir / "users").mkdir(parents=True, exist_ok=True)

    mcserver = server_dir / "bin" / "mcserver"
    shutil.copyfile(ASSETS / "mcserver", mcserver)
    os.chmod(mcserver, 0o755)

    (server_dir / "conf" / "server.conf").write_text(broken_conf(s), encoding="utf-8")
    (server_dir / "conf" / "server.conf.bak").write_text(
        f"SERVER_NAME={s.server_name}\nPORT={s.port}\n"
        f"MAX_PLAYERS={s.max_players}\n"
        f"SPAWN={s.spawn[0]} {s.spawn[1]} {s.spawn[2]}\n", encoding="utf-8")

    shutil.copyfile(ASSETS / "NOTES.md", server_dir / "docs" / "NOTES.md")
    shutil.copyfile(ASSETS / "mcserver.8", server_dir / "docs" / "mcserver.8")

    (server_dir / "logs" / "server.log").write_text(
        "\n".join(s.log) + "\n", encoding="utf-8")

    for path, spot in s.moved.items():
        name = os.path.basename(path)
        dest = server_dir / spot / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(s.file_content[path], encoding="utf-8")

    (server_dir / "users" / "players.txt").write_text(
        "\n".join(s.hackers + s.players) + "\n", encoding="utf-8")
    (server_dir / "users" / "banlist.txt").write_text(
        "\n".join(s.banlist_initial) + "\n", encoding="utf-8")
    (server_dir / "users" / "backup-index.txt").write_text(
        "\n".join(sorted(WORLD_FILES)) + "\n", encoding="utf-8")


def main():
    if SERVER_DIR.exists():
        print("Директория server/ уже существует.", file=sys.stderr)
        print("Запустите python3 clean.py, чтобы перезапустить квест.", file=sys.stderr)
        sys.exit(1)

    seed = read_or_create_seed()
    s = from_seed(seed)
    build_server(SERVER_DIR, s)

    print("Окружение создано. Сид:", seed)
    print("Квест начинается: открой README.md")


if __name__ == "__main__":
    main()
