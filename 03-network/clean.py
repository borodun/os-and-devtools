#!/usr/bin/env python3
import subprocess

subprocess.run(["docker", "compose", "down", "--remove-orphans"], check=False)
print("Стенд разобран — это финальный шаг сдачи. Файлы flags.txt и .hints сохранены; по ним преподаватель ставит оценку.")
