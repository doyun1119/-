# -*- coding: utf-8 -*-
"""
rogue_core.py
=============
ROGUE(1980) 스타일 던전 게임의 '데이터'와 '던전 생성'을 담당하는 모듈.

이 파일에는 게임 규칙이 들어있지 않습니다.
- 지도 크기, 타일, 몬스터/아이템 표 같은 상수
- Room / Player / Monster / Item / Trap / Stairs / Treasure 클래스
- 랜덤 던전 생성 + 연결 검증

규칙과 턴 처리는 rogue_game.py 가 담당합니다.
"""

import random

# ---------------------------------------------------------------- 상수

MAP_WIDTH = 60
MAP_HEIGHT = 25

WALL = "#"
FLOOR = "."

MIN_ROOM_WIDTH = 5
MAX_ROOM_WIDTH = 12
MIN_ROOM_HEIGHT = 4
MAX_ROOM_HEIGHT = 8
MAX_ROOMS = 8

MAX_FLOOR = 5          # 최종 층
VIEW_RADIUS = 5        # 시야 반경
CHASE_RADIUS = 8       # 몬스터가 플레이어를 쫓기 시작하는 거리


MONSTER_TYPES = {
    "Rat":    {"char": "r", "hp": 5,  "attack": 2, "defense": 0, "xp": 3},
    "Goblin": {"char": "g", "hp": 10, "attack": 4, "defense": 1, "xp": 5},
    "Orc":    {"char": "o", "hp": 16, "attack": 6, "defense": 2, "xp": 9},
    "Troll":  {"char": "T", "hp": 24, "attack": 8, "defense": 3, "xp": 15},
}

ITEM_TYPES = {
    "Potion": {"symbol": "!", "item_type": "heal", "value": 10},
    "Gold":   {"symbol": "$", "item_type": "gold", "value": 10},
}


# ---------------------------------------------------------------- 클래스

class Room:
    """던전의 방 하나."""

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def center(self):
        return (self.x + self.width // 2,
                self.y + self.height // 2)

    def intersects(self, other, margin=1):
        return (
            self.x - margin < other.x + other.width
            and self.x + self.width + margin > other.x
            and self.y - margin < other.y + other.height
            and self.y + self.height + margin > other.y
        )


class Player:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
        self.reset()

    def reset(self):
        self.max_hp = 20
        self.hp = 20
        self.attack = 5
        self.defense = 2
        self.level = 1
        self.xp = 0
        self.next_xp = 10
        self.gold = 0
        self.inventory = []
        self.poisoned = False
        self.poison_turns = 0
        self.alive = True


class Monster:
    def __init__(self, name, char, x, y, hp, attack, defense, xp):
        self.name = name
        self.char = char
        self.x = x
        self.y = y
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.xp = xp
        self.alive = True


class Item:
    def __init__(self, name, symbol, item_type, value=0, x=0, y=0):
        self.name = name
        self.symbol = symbol
        self.item_type = item_type
        self.value = value
        self.x = x
        self.y = y


class Trap:
    def __init__(self, x, y, damage):
        self.x = x
        self.y = y
        self.damage = damage
        self.symbol = "^"
        self.visible = False


class Stairs:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.symbol = ">"


class Treasure:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.symbol = "*"


def create_monster(name, x, y):
    data = MONSTER_TYPES[name]
    return Monster(
        name=name,
        char=data["char"],
        x=x,
        y=y,
        hp=data["hp"],
        attack=data["attack"],
        defense=data["defense"],
        xp=data["xp"],
    )


def create_item(name, x=0, y=0):
    data = ITEM_TYPES[name]
    return Item(
        name=name,
        symbol=data["symbol"],
        item_type=data["item_type"],
        value=data["value"],
        x=x,
        y=y,
    )


# ---------------------------------------------------------------- 던전 생성

def create_empty_dungeon():
    """전부 벽으로 채워진 던전을 만든다."""
    return [[WALL for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]


def create_room(dungeon, room):
    """던전에 방 하나를 파낸다."""
    for y in range(room.y, room.y + room.height):
        for x in range(room.x, room.x + room.width):
            dungeon[y][x] = FLOOR


def generate_rooms():
    """서로 겹치지 않는 방들을 만든다."""
    rooms = []

    for _ in range(MAX_ROOMS * 5):
        if len(rooms) >= MAX_ROOMS:
            break

        width = random.randint(MIN_ROOM_WIDTH, MAX_ROOM_WIDTH)
        height = random.randint(MIN_ROOM_HEIGHT, MAX_ROOM_HEIGHT)

        x = random.randint(1, MAP_WIDTH - width - 2)
        y = random.randint(1, MAP_HEIGHT - height - 2)

        new_room = Room(x, y, width, height)

        if any(new_room.intersects(other) for other in rooms):
            continue

        rooms.append(new_room)

    return rooms


def create_horizontal_corridor(dungeon, x1, x2, y):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        dungeon[y][x] = FLOOR


def create_vertical_corridor(dungeon, y1, y2, x):
    for y in range(min(y1, y2), max(y1, y2) + 1):
        dungeon[y][x] = FLOOR


def connect_rooms(dungeon, room_a, room_b):
    """두 방의 중심을 ㄱ자 통로로 잇는다."""
    x1, y1 = room_a.center()
    x2, y2 = room_b.center()

    if random.random() < 0.5:
        create_horizontal_corridor(dungeon, x1, x2, y1)
        create_vertical_corridor(dungeon, y1, y2, x2)
    else:
        create_vertical_corridor(dungeon, y1, y2, x1)
        create_horizontal_corridor(dungeon, x1, x2, y2)


def flood_fill(dungeon, start_x, start_y):
    """시작점에서 걸어갈 수 있는 모든 바닥 칸."""
    visited = set()
    stack = [(start_x, start_y)]

    while stack:
        x, y = stack.pop()

        if (x, y) in visited:
            continue
        if x < 0 or x >= MAP_WIDTH or y < 0 or y >= MAP_HEIGHT:
            continue
        if dungeon[y][x] != FLOOR:
            continue

        visited.add((x, y))

        stack.append((x, y - 1))
        stack.append((x, y + 1))
        stack.append((x - 1, y))
        stack.append((x + 1, y))

    return visited


def validate_dungeon(dungeon, rooms):
    """모든 방이 첫 번째 방에서 걸어서 도달 가능한지 검사."""
    if len(rooms) < 2:
        return False

    start_x, start_y = rooms[0].center()
    reachable = flood_fill(dungeon, start_x, start_y)

    for room in rooms:
        if room.center() not in reachable:
            return False

    return True


def generate_dungeon():
    """검증을 통과한 랜덤 던전을 만든다. (dungeon, rooms) 반환."""
    for _ in range(50):
        dungeon = create_empty_dungeon()
        rooms = generate_rooms()

        if len(rooms) < 2:
            continue

        for i in range(1, len(rooms)):
            connect_rooms(dungeon, rooms[i - 1], rooms[i])

        if validate_dungeon(dungeon, rooms):
            return dungeon, rooms

    # 50번 실패하면 마지막 결과라도 돌려준다 (사실상 발생하지 않음)
    return dungeon, rooms
