# -*- coding: utf-8 -*-
"""
rogue_core.py
=============
ROGUE(1980) 스타일 던전 게임의 '데이터'와 '던전 생성' 담당.

담고 있는 것
- 지도/층 상수, 등급표, 몬스터표, 장비표
- Room / Player / Monster / Item / Trap / Stairs / Treasure
- 등급에 맞는 랜덤 장비 생성
- 랜덤 던전 생성 + 연결 검증

게임 규칙(이동·전투·턴)은 rogue_game.py 가 담당합니다.
"""

import random

# ---------------------------------------------------------------- 지도 상수

MAP_WIDTH = 60
MAP_HEIGHT = 25

WALL = "#"
FLOOR = "."

MIN_ROOM_WIDTH = 5
MAX_ROOM_WIDTH = 12
MIN_ROOM_HEIGHT = 4
MAX_ROOM_HEIGHT = 8
MAX_ROOMS = 8

MAX_FLOOR = 10         # 최종 층
VIEW_RADIUS = 5        # 시야 반경
CHASE_RADIUS = 8       # 몬스터가 추적을 시작하는 거리


# ---------------------------------------------------------------- 아이템 등급
#
# 등급은 1~5. 층이 깊어질수록 높은 등급이 나온다.
#   1~2층 → 1등급 중심,  9~10층 → 5등급 중심
# floor_tier_weights() 가 층별 등급 확률을 만든다.

MAX_TIER = 5

TIER_NAMES = {
    1: "녹슨",
    2: "평범한",
    3: "강철",
    4: "미스릴",
    5: "전설의",
}

TIER_MARKS = {
    1: "",
    2: "+",
    3: "++",
    4: "★",
    5: "★★",
}


def floor_base_tier(floor):
    """그 층의 '기준' 등급. 1~2층=1, 3~4층=2, ... 9~10층=5."""
    tier = (floor + 1) // 2
    return max(1, min(MAX_TIER, tier))


def floor_tier_weights(floor):
    """
    기준 등급을 중심으로 한 확률 분포.
    기준 등급이 가장 흔하고, ±1 등급이 가끔 섞인다.
    """
    base = floor_base_tier(floor)

    weights = []
    for tier in range(1, MAX_TIER + 1):
        distance = abs(tier - base)

        if distance == 0:
            weights.append(60)
        elif distance == 1:
            weights.append(20)
        elif distance == 2:
            weights.append(4)
        else:
            weights.append(0)

    # 기준보다 높은 등급은 조금 더 귀하게
    for i, tier in enumerate(range(1, MAX_TIER + 1)):
        if tier > base:
            weights[i] = max(1, weights[i] // 2)

    return weights


def roll_tier(floor):
    tiers = list(range(1, MAX_TIER + 1))
    return random.choices(tiers, weights=floor_tier_weights(floor), k=1)[0]


# ---------------------------------------------------------------- 장비표
#
# power  : 등급 1 기준 수치
# step   : 등급이 1 오를 때마다 오르는 수치

MELEE_WEAPONS = {
    "단검":   {"power": 3, "step": 2},
    "장검":   {"power": 5, "step": 3},
    "전투도끼": {"power": 7, "step": 4},
}

RANGED_WEAPONS = {
    "단궁": {"power": 3, "step": 2, "range": 6},
    "장궁": {"power": 5, "step": 3, "range": 8},
    "석궁": {"power": 7, "step": 4, "range": 10},
}

ARMORS = {
    "가죽갑옷": {"power": 2, "step": 1},
    "사슬갑옷": {"power": 4, "step": 2},
    "판금갑옷": {"power": 6, "step": 3},
}

# ring_effect: 게임 로직이 읽는 효과 키
RINGS = {
    "힘의 반지":   {"effect": "attack",  "power": 1, "step": 1},
    "수호의 반지": {"effect": "defense", "power": 1, "step": 1},
    "활력의 반지": {"effect": "max_hp",  "power": 4, "step": 3},
    "재생의 반지": {"effect": "regen",   "power": 1, "step": 1},
    "행운의 반지": {"effect": "crit",    "power": 5, "step": 4},   # 치명타 %
}

RING_EFFECT_TEXT = {
    "attack":  "공격력 +{v}",
    "defense": "방어력 +{v}",
    "max_hp":  "최대 HP +{v}",
    "regen":   "{v}턴마다 HP 1 회복",
    "crit":    "치명타 +{v}%",
}


# 슬롯 이름
SLOT_MELEE = "melee"
SLOT_RANGED = "ranged"
SLOT_ARMOR = "armor"
SLOT_RING1 = "ring1"
SLOT_RING2 = "ring2"

SLOT_LABELS = {
    SLOT_MELEE: "근접",
    SLOT_RANGED: "원거리",
    SLOT_ARMOR: "방어구",
    SLOT_RING1: "반지1",
    SLOT_RING2: "반지2",
}


# ---------------------------------------------------------------- 몬스터표

MONSTER_TYPES = {
    "Rat":     {"char": "r", "hp": 5,  "attack": 2,  "defense": 0, "xp": 3,  "floor": 1,  "rarity": 10},
    "Goblin":  {"char": "g", "hp": 10, "attack": 4,  "defense": 1, "xp": 5,  "floor": 1,  "rarity": 10},
    "Orc":     {"char": "o", "hp": 16, "attack": 6,  "defense": 2, "xp": 9,  "floor": 3,  "rarity": 8},
    "Troll":   {"char": "T", "hp": 24, "attack": 8,  "defense": 3, "xp": 15, "floor": 4,  "rarity": 6},
    "Wraith":  {"char": "W", "hp": 30, "attack": 11, "defense": 4, "xp": 22, "floor": 6,  "rarity": 4},
    "Golem":   {"char": "G", "hp": 45, "attack": 13, "defense": 7, "xp": 30, "floor": 7,  "rarity": 3},
    "Dragon":  {"char": "D", "hp": 60, "attack": 17, "defense": 8, "xp": 45, "floor": 9,  "rarity": 2},
}

ITEM_TYPES = {
    "물약":   {"symbol": "!", "item_type": "heal",  "value": 10},
    "골드":   {"symbol": "$", "item_type": "gold",  "value": 10},
    "화살":   {"symbol": "(", "item_type": "ammo",  "value": 6},
}


# ---------------------------------------------------------------- 클래스

class Room:
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


class Item:
    """
    소모품과 장비를 모두 표현한다.

    item_type
      heal / gold / ammo          : 소모품
      weapon_melee / weapon_ranged / armor / ring : 장비
    """

    def __init__(self, name, symbol, item_type, value=0, x=0, y=0,
                 tier=1, ring_effect=None, attack_range=0, base_name=""):
        self.name = name
        self.base_name = base_name or name
        self.symbol = symbol
        self.item_type = item_type
        self.value = value          # 회복량 / 골드 / 화살 수 / 장비 수치
        self.x = x
        self.y = y
        self.tier = tier
        self.ring_effect = ring_effect
        self.attack_range = attack_range

    # --- 분류 도우미 ---

    def is_equipment(self):
        return self.item_type in (
            "weapon_melee", "weapon_ranged", "armor", "ring"
        )

    def slot(self):
        if self.item_type == "weapon_melee":
            return SLOT_MELEE
        if self.item_type == "weapon_ranged":
            return SLOT_RANGED
        if self.item_type == "armor":
            return SLOT_ARMOR
        if self.item_type == "ring":
            return SLOT_RING1        # 실제 배치는 game 쪽에서 결정
        return None

    def describe(self):
        """인벤토리 한 줄 설명."""
        if self.item_type == "heal":
            return f"{self.name} (HP +{self.value})"

        if self.item_type == "ammo":
            return f"{self.name} x{self.value}"

        if self.item_type == "gold":
            return f"{self.name} {self.value}"

        if self.item_type == "weapon_melee":
            return f"{self.name} (공격 +{self.value})"

        if self.item_type == "weapon_ranged":
            return f"{self.name} (공격 +{self.value}, 사거리 {self.attack_range})"

        if self.item_type == "armor":
            return f"{self.name} (방어 +{self.value})"

        if self.item_type == "ring":
            if self.ring_effect == "regen":
                interval = max(2, 8 - self.value)
                return f"{self.name} ({interval}턴마다 HP 1 회복)"

            text = RING_EFFECT_TEXT.get(self.ring_effect, "?")
            return f"{self.name} ({text.format(v=self.value)})"

        return self.name


class Player:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
        self.reset()

    def reset(self):
        self.base_max_hp = 20
        self.hp = 20
        self.base_attack = 5
        self.base_defense = 2

        self.level = 1
        self.xp = 0
        self.next_xp = 10
        self.gold = 0
        self.arrows = 8

        self.inventory = []
        self.equipment = {
            SLOT_MELEE: None,
            SLOT_RANGED: None,
            SLOT_ARMOR: None,
            SLOT_RING1: None,
            SLOT_RING2: None,
        }

        self.poisoned = False
        self.poison_turns = 0
        self.alive = True

    # --- 장착 아이템 합산 ---

    def rings(self):
        return [
            self.equipment[slot]
            for slot in (SLOT_RING1, SLOT_RING2)
            if self.equipment[slot] is not None
        ]

    def ring_bonus(self, effect):
        return sum(r.value for r in self.rings() if r.ring_effect == effect)

    @property
    def max_hp(self):
        return self.base_max_hp + self.ring_bonus("max_hp")

    @property
    def attack(self):
        weapon = self.equipment[SLOT_MELEE]
        bonus = weapon.value if weapon else 0
        return self.base_attack + bonus + self.ring_bonus("attack")

    @property
    def defense(self):
        armor = self.equipment[SLOT_ARMOR]
        bonus = armor.value if armor else 0
        return self.base_defense + bonus + self.ring_bonus("defense")

    @property
    def ranged_attack(self):
        weapon = self.equipment[SLOT_RANGED]
        if weapon is None:
            return 0
        return weapon.value + self.ring_bonus("attack")

    @property
    def ranged_range(self):
        weapon = self.equipment[SLOT_RANGED]
        if weapon is None:
            return 0
        return weapon.attack_range

    @property
    def crit_chance(self):
        return 0.10 + self.ring_bonus("crit") / 100.0

    @property
    def regen_rate(self):
        """0 이면 재생 없음. 값이 클수록 자주 회복."""
        return self.ring_bonus("regen")


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


# ---------------------------------------------------------------- 생성 함수

def scaled_value(base, step, tier):
    return base + step * (tier - 1)


def tier_name(name, tier):
    mark = TIER_MARKS[tier]
    label = TIER_NAMES[tier]
    if mark:
        return f"{label} {name}{mark}"
    return f"{label} {name}"


def create_monster(name, x, y, floor=1):
    """층이 깊을수록 능력치를 조금씩 올려서 만든다."""
    data = MONSTER_TYPES[name]
    scale = 1.0 + (floor - 1) * 0.14

    return Monster(
        name=name,
        char=data["char"],
        x=x,
        y=y,
        hp=int(data["hp"] * scale),
        attack=int(round(data["attack"] * scale)),
        defense=data["defense"] + (floor - 1) // 4,
        xp=int(data["xp"] * scale),
    )


def create_simple_item(name, x=0, y=0, floor=1):
    """물약 / 골드 / 화살."""
    data = ITEM_TYPES[name]
    value = data["value"]

    if data["item_type"] == "gold":
        value = random.randint(5, 15) * floor
    elif data["item_type"] == "heal":
        value = 10 + floor
    elif data["item_type"] == "ammo":
        value = random.randint(4, 8)

    return Item(
        name=name,
        symbol=data["symbol"],
        item_type=data["item_type"],
        value=value,
        x=x,
        y=y,
        base_name=name,
    )


def create_equipment(category, base, tier, x=0, y=0):
    """
    category : "weapon_melee" | "weapon_ranged" | "armor" | "ring"
    base     : 각 표의 키 이름 (예: "장궁")
    """
    if category == "weapon_melee":
        data = MELEE_WEAPONS[base]
        return Item(
            name=tier_name(base, tier),
            symbol=")",
            item_type="weapon_melee",
            value=scaled_value(data["power"], data["step"], tier),
            x=x, y=y, tier=tier, base_name=base,
        )

    if category == "weapon_ranged":
        data = RANGED_WEAPONS[base]
        return Item(
            name=tier_name(base, tier),
            symbol="}",
            item_type="weapon_ranged",
            value=scaled_value(data["power"], data["step"], tier),
            attack_range=data["range"],
            x=x, y=y, tier=tier, base_name=base,
        )

    if category == "armor":
        data = ARMORS[base]
        return Item(
            name=tier_name(base, tier),
            symbol="[",
            item_type="armor",
            value=scaled_value(data["power"], data["step"], tier),
            x=x, y=y, tier=tier, base_name=base,
        )

    if category == "ring":
        data = RINGS[base]
        return Item(
            name=tier_name(base, tier),
            symbol="=",
            item_type="ring",
            value=scaled_value(data["power"], data["step"], tier),
            ring_effect=data["effect"],
            x=x, y=y, tier=tier, base_name=base,
        )

    raise ValueError(f"알 수 없는 장비 종류: {category}")


def random_equipment(floor, x=0, y=0):
    """그 층에 어울리는 등급의 장비를 랜덤으로 하나 만든다."""
    category = random.choices(
        ["weapon_melee", "weapon_ranged", "armor", "ring"],
        weights=[30, 25, 30, 15],
        k=1,
    )[0]

    tables = {
        "weapon_melee": MELEE_WEAPONS,
        "weapon_ranged": RANGED_WEAPONS,
        "armor": ARMORS,
        "ring": RINGS,
    }

    base = random.choice(list(tables[category].keys()))
    tier = roll_tier(floor)

    return create_equipment(category, base, tier, x, y)


# ---------------------------------------------------------------- 던전 생성

def create_empty_dungeon():
    return [[WALL for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]


def create_room(dungeon, room):
    for y in range(room.y, room.y + room.height):
        for x in range(room.x, room.x + room.width):
            dungeon[y][x] = FLOOR


def generate_rooms():
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
    x1, y1 = room_a.center()
    x2, y2 = room_b.center()

    if random.random() < 0.5:
        create_horizontal_corridor(dungeon, x1, x2, y1)
        create_vertical_corridor(dungeon, y1, y2, x2)
    else:
        create_vertical_corridor(dungeon, y1, y2, x1)
        create_horizontal_corridor(dungeon, x1, x2, y2)


def flood_fill(dungeon, start_x, start_y):
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
    if len(rooms) < 2:
        return False

    start_x, start_y = rooms[0].center()
    reachable = flood_fill(dungeon, start_x, start_y)

    for room in rooms:
        if room.center() not in reachable:
            return False

    return True


def generate_dungeon():
    """검증을 통과한 랜덤 던전. (dungeon, rooms) 반환."""
    for _ in range(50):
        dungeon = create_empty_dungeon()
        rooms = generate_rooms()

        if len(rooms) < 2:
            continue

        for room in rooms:
            create_room(dungeon, room)

        for i in range(1, len(rooms)):
            connect_rooms(dungeon, rooms[i - 1], rooms[i])

        if validate_dungeon(dungeon, rooms):
            return dungeon, rooms

    return dungeon, rooms
