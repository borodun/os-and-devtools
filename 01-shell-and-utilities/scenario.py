#!/usr/bin/env python3
from __future__ import annotations

import random
from dataclasses import dataclass

N_HACKERS = 6

NICK_POOL = [
    "Steve", "Alex", "Herobrine", "Dinnerbone", "Grumm",
    "jeb_", "NoobMaster69", "CreeperKing", "DiamondMiner",
    "RedstoneGuru", "EnderFan", "PufferQueen",
    "BlueTNT", "MegaBuilder", "ZombieSlayer", "IceQueen",
    "TNT_Tom", "CactusCarl",
]

CHAT_LINES = [
    "привет всем",
    "где спавн?",
    "кто продаст алмазы?",
    "нужна карта 3, кто занят?",
    "отличная погода",
    "побежали на эндер",
    "кто видел мою ферму?",
]

HACKER_CHAT = ["кто на спавне?", "ахаха", "здесь красиво было"]

GRIEF_TARGETS = ["спавн", "спавн", "ферма", "дом", "колодец", "склад", "ферма тростника"]

TRADE_ITEMS = ["diamond", "iron", "gold", "emerald", "coal"]

SERVER_NAMES = ["NightFall", "BlockStorm", "RedStone", "MineUtopia", "PixelLand"]
PORTS = [25500, 25566, 25577, 31212, 40000, 55000]
MAX_PLAYERS_POOL = [64, 100, 125, 200]
BROKEN_PORTS = [99999, 70000, 0, 999]

WORLD_FILES = [
    "data/world.dat",
    "data/maps/dungeon.dat",
    "data/playerdata/saves.dat",
    "data/plugins/antigrief.cfg",
]
HIDE_SPOTS = ["logs", "users", "bin", "docs"]

PAST_REASONS = ["cheating", "advertising"]
BAN_REASON = "griefing"


@dataclass
class Scenario:
    seed: int
    server_name: str
    port: int
    max_players: int
    spawn: tuple
    hackers: list
    players: list
    false_ban: str
    log: list
    moved: dict
    file_content: dict
    banlist_initial: list
    past_bans: list


def _file_content(rng: random.Random, path: str) -> str:
    if path.endswith("world.dat"):
        lines = ["# world chunk data"]
        for i in range(16):
            lines.append(f"chunk {i:03d}: {rng.randrange(16**8):08x}")
        return "\n".join(lines) + "\n"
    if path.endswith("dungeon.dat"):
        lines = ["# dungeon map"]
        for i in range(10):
            lines.append(f"{rng.randint(-50, 50)} {rng.randint(-50, 50)} {rng.randint(-50, 50)}")
        return "\n".join(lines) + "\n"
    if path.endswith("saves.dat"):
        return f"# player saves\nversion 3\nslots {rng.randint(1, 64)}\n"
    return f"# anti-grief plugin config\nenabled=true\nradius={rng.randint(5, 40)}\n"


def _build_log(rng: random.Random, hackers: list, players: list, false_ban: str) -> list:
    ev = []

    def ts(minute: int) -> str:
        h = (22 + minute // 60) % 24
        return f"2025-08-14 {h:02d}:{minute % 60:02d}:{rng.randint(0, 59):02d}"

    m = 0
    joins = rng.sample(players, rng.randint(8, 10))
    for p in joins:
        m += rng.randint(1, 4)
        ev.append((m, f"[{ts(m)}] [JOIN] {p}"))
    for _ in range(rng.randint(60, 90)):
        m += rng.randint(1, 5)
        p = rng.choice(joins)
        r = rng.random()
        if r < 0.4:
            ev.append((m, f"[{ts(m)}] [CHAT] {p}: {rng.choice(CHAT_LINES)}"))
        elif r < 0.75:
            ev.append((m, f"[{ts(m)}] [BREAK] {p}: {rng.randint(-100, 100)} "
                           f"{rng.randint(50, 80)} {rng.randint(-100, 100)}"))
        else:
            q = rng.choice([x for x in joins if x != p])
            ev.append((m, f"[{ts(m)}] [TRADE] {p} -> {q} {rng.randint(1, 40)} {rng.choice(TRADE_ITEMS)}"))
    m += 3
    ev.append((m, f"[{ts(m)}] [SYSTEM] плановое резервное копирование: users/backup-index.txt обновлён"))

    m += rng.randint(20, 40)
    for h in hackers:
        m += rng.randint(0, 2)
        ev.append((m, f"[{ts(m)}] [JOIN] {h}"))
    m += 1
    n_grief = rng.randint(50, 70)
    n_null = rng.randint(3, 5)
    null_idx = set(rng.sample(range(n_grief), n_null))
    for i in range(n_grief):
        m += rng.randint(0, 3)
        target = rng.choice(GRIEF_TARGETS)
        if i in null_idx:
            ev.append((m, f"[{ts(m)}] [GRIEF] : {target}"))
        else:
            ev.append((m, f"[{ts(m)}] [GRIEF] {rng.choice(hackers)}: {target}"))
    for _ in range(3):
        m += rng.randint(1, 3)
        ev.append((m, f"[{ts(m)}] [CHAT] {rng.choice(hackers)}: {rng.choice(HACKER_CHAT)}"))
    for h in hackers:
        m += rng.randint(0, 2)
        ev.append((m, f"[{ts(m)}] [LEAVE] {h}"))

    m += rng.randint(5, 10)
    ev.append((m, f"[{ts(m)}] [CHAT] {false_ban}: мой аккаунт взломали! Я это не делал, помогите"))

    return [line for _, line in sorted(ev)]


def from_seed(seed: int) -> Scenario:
    rng = random.Random(seed)

    nicks = list(NICK_POOL)
    rng.shuffle(nicks)
    hackers = nicks[:N_HACKERS]
    others = nicks[N_HACKERS:N_HACKERS + 3 + 8]
    past1, past2, false_ban = rng.sample(others, 3)
    players = [n for n in others if n != false_ban]

    server_name = rng.choice(SERVER_NAMES)
    port = rng.choice(PORTS)
    max_players = rng.choice(MAX_PLAYERS_POOL)
    spawn = (rng.randint(-256, 256), rng.choice([64, 65, 66, 70, 72]),
             rng.randint(-256, 256))

    spots = rng.sample(HIDE_SPOTS, len(WORLD_FILES))
    moved = {f: spots[i] for i, f in enumerate(WORLD_FILES)}
    file_content = {f: _file_content(rng, f) for f in WORLD_FILES}

    past_bans = [(past1, rng.choice(PAST_REASONS)), (past2, rng.choice(PAST_REASONS))]
    banlist = [f"{n} {r}" for n, r in past_bans]
    banlist.append(f"{past_bans[0][0]} {past_bans[0][1]}")
    banlist.append(f"{false_ban} {BAN_REASON}")
    rng.shuffle(banlist)

    log = _build_log(rng, hackers, players, false_ban)

    return Scenario(
        seed=seed, server_name=server_name, port=port,
        max_players=max_players, spawn=spawn,
        hackers=hackers, players=players, false_ban=false_ban,
        log=log, moved=moved, file_content=file_content,
        banlist_initial=banlist, past_bans=past_bans,
    )


def expected_hacker_lines(s: Scenario) -> set:
    return {line for line in s.log if any(h in line for h in s.hackers)}


def expected_banlist(s: Scenario) -> list:
    lines = [f"{n} {r}" for n, r in s.past_bans]
    lines += [f"{h} {BAN_REASON}" for h in s.hackers]
    return lines


def expected_conf(s: Scenario) -> str:
    return (f"SERVER_NAME={s.server_name}\n"
            f"PORT={s.port}\n"
            f"MAX_PLAYERS={s.max_players}\n"
            f"SPAWN={s.spawn[0]} {s.spawn[1]} {s.spawn[2]}\n")


def broken_conf(s: Scenario) -> str:
    return (f"SERVER_NAME={s.server_name}\n"
            f"PORT={rng_port(s.seed)}\n"
            f"# MAX_PLAYERS=?\n"
            f"SPAWN={s.spawn[0]} {s.spawn[1]}\n")


def rng_port(seed: int) -> int:
    return random.Random(seed + 1).choice(BROKEN_PORTS)
