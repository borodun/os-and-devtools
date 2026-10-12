#!/usr/bin/env python3
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
TARGETS = [ROOT / "server", ROOT / ".seed", ROOT / "seed.txt", ROOT / ".attempts"]


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    assume_yes = "--yes" in args

    found = [p for p in TARGETS if p.exists()]
    if not found:
        print("Нечего чистить.")
        return

    print("Будет удалено:")
    for p in found:
        kind = "dir" if p.is_dir() else "file"
        print(f"  [{kind}] {p.name}")

    if dry:
        print("\n--dry-run: ничего не удалено.")
        return

    if not assume_yes:
        ans = input("\nУдалить? [y/N] ").strip().lower()
        if ans not in ("y", "yes", "д", "да"):
            print("Отменено.")
            return

    for p in found:
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        print(f"  удалено: {p.name}")
    print("Готово. Можно запустить python3 generate.py заново.")


if __name__ == "__main__":
    main()
