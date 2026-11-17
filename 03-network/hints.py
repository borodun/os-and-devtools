#!/usr/bin/env python3
import base64
import json
import os
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(ROOT, "hints.bin")
MAGIC = b"KPS1"

STAGE_NAMES = {
    "1": "Адрес",
    "2": "Соседи",
    "3": "Путь",
    "4": "Канал",
    "5": "Имя",
    "6": "Страница",
    "7": "Кадры",
    "8": "Двери",
}


def load_hints():
    if not os.path.exists(BIN):
        print("подсказки не загружены: нет hints.bin (преподаватель: python3 make-hints.py)")
        sys.exit(1)
    with open(BIN, "rb") as f:
        blob = f.read()
    if not blob.startswith(MAGIC):
        print("подсказки не загружены: hints.bin повреждён")
        sys.exit(1)
    try:
        data = zlib.decompress(base64.b64decode(blob[len(MAGIC):]))
        return json.loads(data)
    except Exception:
        print("подсказки не загружены: hints.bin повреждён")
        sys.exit(1)


def main():
    HINTS = load_hints()
    if len(sys.argv) < 2:
        print("использование: python3 hints.py <этап> [уровень]")
        print("этапы: %s; уровни: 1 2 3 (по умолчанию 1)" % " ".join(HINTS))
        sys.exit(1)
    stage = sys.argv[1].lower()
    if stage not in HINTS:
        print("нет такого этапа: %s (есть: %s)" % (stage, " ".join(HINTS)))
        sys.exit(1)
    tier = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    if tier < 1 or tier > 3:
        print("уровень 1, 2 или 3")
        sys.exit(1)
    log = []
    if os.path.exists(".hints"):
        for line in open(".hints"):
            parts = line.split()
            if len(parts) == 2:
                log.append((parts[0].lower(), int(parts[1])))
    if tier > 1 and (stage, tier - 1) not in log:
        print(
            "Подсказка: сначала покажите уровень %d по этапу «%s»."
            % (tier - 1, STAGE_NAMES.get(stage, stage))
        )
        sys.exit(1)
    if (stage, tier) in log:
        print("Подсказка: эта подсказка уже была показана.")
        return
    with open(".hints", "a") as f:
        f.write("%s %d\n" % (stage, tier))
    print(HINTS[stage][tier - 1])


if __name__ == "__main__":
    main()
