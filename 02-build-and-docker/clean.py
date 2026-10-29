#!/usr/bin/env python3
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent

ARTIFACTS = [
    ROOT / "build",
    ROOT / "results",
]


def compose_available():
    return (ROOT / "compose.yaml").exists() or (ROOT / "docker-compose.yaml").exists()


def main():
    dry = "--dry-run" in sys.argv
    assume_yes = "--yes" in sys.argv

    to_remove = [p for p in ARTIFACTS if p.exists()]
    stop_containers = compose_available()

    print("Удаление артефактов сборки:")
    for p in to_remove:
        print(f"  [dir] {p.relative_to(ROOT)}/")
    if stop_containers:
        print("  [docker] docker compose down (остановка контейнеров)")

    if not to_remove and not stop_containers:
        print("Нечего чистить.")
        return

    if not assume_yes and not dry:
        answer = input("Удалить? [y/N] ").strip().lower()
        if answer not in ("y", "yes", "да"):
            print("Отменено.")
            return

    if dry:
        print("--dry-run: ничего не удаляю")
        return

    for p in to_remove:
        try:
            shutil.rmtree(p)
        except OSError:
            print(f"Не удалось удалить {p.relative_to(ROOT)}/ "
                  f"(каталог создан Docker от имени root).")
            print(f"Удалите вручную: sudo rm -rf {p}")

    if stop_containers:
        subprocess.run(["docker", "compose", "down"], cwd=str(ROOT),
                       capture_output=True)

    print("Готово.")


if __name__ == "__main__":
    main()
