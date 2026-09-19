# -*- coding: utf-8 -*-
"""
rogue_game.py
=============
게임 규칙 담당. 모든 상태를 Game 클래스 하나가 들고 있습니다.

원래 노트북은 dungeon, player, monsters, items ... 를 전부 전역 변수로 두고
함수마다 global 을 선언하는 방식이었습니다. 이러면
 - 함수 하나만 빠져도(예: monsters_turn) 조용히 무너지고
 - 층을 새로 만들 때 초기화를 빠뜨리기 쉽습니다.
그래서 상태를 Game 객체 안에 모았습니다.

화면 출력(print)은 하지 않습니다. 모든 메시지는 self.messages 에 쌓이고,
그리기는 rogue_ui.py 쪽에서 담당합니다.
"""

import random

from rogue_core import (
    MAP_WIDTH, MAP_HEIGHT, WALL, FLOOR,
    MAX_FLOOR, VIEW_RADIUS, CHASE_RADIUS,
    MONSTER_TYPES, ITEM_TYPES,
    Player, Trap, Stairs, Treasure,
    create_monster, create_item, generate_dungeon,
)

MAX_MESSAGES = 6      # 화면에 보여줄 메시지 줄 수


class Game:

    # ------------------------------------------------------------ 초기화

    def __init__(self):
        self.player = Player()
        self.new_game()

    def new_game(self):
        """완전히 새 게임을 시작한다."""
        self.player.reset()

        self.floor = 1
        self.turn = 0

        self.running = True
        self.won = False

        self.messages = []
        self.show_inventory = False

        self.build_floor()

        self.log("던전에 들어섰습니다. WASD로 이동하세요.")

    def build_floor(self):
        """현재 층의 던전/몬스터/아이템/함정을 새로 만든다."""
        self.dungeon, self.rooms = generate_dungeon()

        self.monsters = []
        self.items = []
        self.traps = []
        self.stairs = None
        self.treasure = None

        self.explored = set()

        self.player.x, self.player.y = self.rooms[0].center()

        # 계단은 마지막 층에는 없다
        if self.floor < MAX_FLOOR:
            x, y = self.random_free_position()
            self.stairs = Stairs(x, y)

        # 몬스터 (층이 깊을수록 많이)
        for _ in range(2 + self.floor * 2):
            self.spawn_monster()

        # 아이템
        for _ in range(2 + self.floor):
            self.spawn_item("Potion")
        for _ in range(2):
            self.spawn_item("Gold")

        # 함정
        for _ in range(1 + self.floor):
            self.spawn_trap()

        # 최종 층에만 보물
        if self.floor == MAX_FLOOR:
            x, y = self.random_free_position()
            self.treasure = Treasure(x, y)

        self.reveal_area()

    # ------------------------------------------------------------ 메시지

    def log(self, message):
        self.messages.append(message)
        if len(self.messages) > MAX_MESSAGES:
            self.messages.pop(0)

    # ------------------------------------------------------------ 위치 조회

    def is_walkable(self, x, y):
        if x < 0 or x >= MAP_WIDTH or y < 0 or y >= MAP_HEIGHT:
            return False
        return self.dungeon[y][x] == FLOOR

    def monster_at(self, x, y):
        for monster in self.monsters:
            if monster.alive and monster.x == x and monster.y == y:
                return monster
        return None

    def item_at(self, x, y):
        for item in self.items:
            if item.x == x and item.y == y:
                return item
        return None

    def trap_at(self, x, y):
        for trap in self.traps:
            if trap.x == x and trap.y == y:
                return trap
        return None

    def is_occupied(self, x, y):
        """플레이어/몬스터/아이템/함정/계단/보물이 이미 있는 칸인가."""
        if self.player.x == x and self.player.y == y:
            return True
        if self.monster_at(x, y):
            return True
        if self.item_at(x, y):
            return True
        if self.trap_at(x, y):
            return True
        if self.stairs and self.stairs.x == x and self.stairs.y == y:
            return True
        if self.treasure and self.treasure.x == x and self.treasure.y == y:
            return True
        return False

    def random_free_position(self):
        """아무것도 없는 바닥 칸 하나를 고른다."""
        candidates = [
            (x, y)
            for y in range(MAP_HEIGHT)
            for x in range(MAP_WIDTH)
            if self.dungeon[y][x] == FLOOR and not self.is_occupied(x, y)
        ]

        if not candidates:
            # 최악의 경우: 아무 바닥이나
            candidates = [
                (x, y)
                for y in range(MAP_HEIGHT)
                for x in range(MAP_WIDTH)
                if self.dungeon[y][x] == FLOOR
            ]

        return random.choice(candidates)

    # ------------------------------------------------------------ 생성

    def spawn_monster(self):
        # 깊은 층일수록 센 몬스터가 나오게 가중치를 준다
        names = list(MONSTER_TYPES.keys())
        weights = []
        for i, _ in enumerate(names):
            weights.append(max(1, 10 - abs(i - (self.floor - 1)) * 4))

        name = random.choices(names, weights=weights, k=1)[0]

        x, y = self.random_free_position()
        self.monsters.append(create_monster(name, x, y))

    def spawn_item(self, name):
        x, y = self.random_free_position()
        self.items.append(create_item(name, x, y))

    def spawn_trap(self):
        x, y = self.random_free_position()
        self.traps.append(Trap(x, y, random.randint(2, 4 + self.floor)))

    # ------------------------------------------------------------ 시야

    def reveal_area(self, radius=VIEW_RADIUS):
        px, py = self.player.x, self.player.y

        for y in range(max(0, py - radius), min(MAP_HEIGHT, py + radius + 1)):
            for x in range(max(0, px - radius), min(MAP_WIDTH, px + radius + 1)):
                if abs(px - x) + abs(py - y) <= radius:
                    self.explored.add((x, y))

    def is_explored(self, x, y):
        return (x, y) in self.explored

    # ------------------------------------------------------------ 전투

    def damage_player(self, damage, source=""):
        self.player.hp -= damage

        if source:
            self.log(f"{source} → 플레이어 {damage} 피해!")
        else:
            self.log(f"플레이어가 {damage} 피해를 입었습니다.")

        if self.player.hp <= 0:
            self.player.hp = 0
            self.player.alive = False
            self.running = False
            self.log("당신은 쓰러졌습니다...")

    def attack_monster(self, monster):
        damage = random.randint(max(1, self.player.attack - 2),
                                self.player.attack + 2)

        critical = random.random() < 0.1
        if critical:
            damage *= 2

        damage = max(1, damage - monster.defense)

        monster.hp -= damage

        if critical:
            self.log(f"치명타! {monster.name}에게 {damage} 피해!")
        else:
            self.log(f"{monster.name}에게 {damage} 피해!")

        if monster.hp <= 0:
            monster.hp = 0
            monster.alive = False

            if monster in self.monsters:
                self.monsters.remove(monster)

            self.log(f"{monster.name} 처치! 경험치 +{monster.xp}")

            self.player.xp += monster.xp
            self.check_level_up()

    def monster_attack(self, monster):
        damage = random.randint(max(1, monster.attack - 1),
                                monster.attack + 1)

        damage = max(1, damage - self.player.defense)

        self.damage_player(damage, source=monster.name)

    def check_level_up(self):
        while self.player.xp >= self.player.next_xp:
            self.player.xp -= self.player.next_xp
            self.player.level += 1

            self.player.max_hp += 5
            self.player.hp = self.player.max_hp
            self.player.attack += 1
            self.player.defense += 1
            self.player.next_xp = int(self.player.next_xp * 1.5)

            self.log(f"레벨 업! LV {self.player.level} (HP 회복)")

    # ------------------------------------------------------------ 몬스터 턴

    def monster_distance(self, monster):
        return (abs(monster.x - self.player.x)
                + abs(monster.y - self.player.y))

    def move_monster_random(self, monster):
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        random.shuffle(directions)

        for dx, dy in directions:
            nx, ny = monster.x + dx, monster.y + dy

            if not self.is_walkable(nx, ny):
                continue
            if nx == self.player.x and ny == self.player.y:
                continue
            if self.monster_at(nx, ny):
                continue

            monster.x, monster.y = nx, ny
            return

    def chase_player(self, monster):
        dx = self.player.x - monster.x
        dy = self.player.y - monster.y

        # 가로/세로 중 더 먼 쪽부터 좁힌다. 막히면 다른 축으로.
        if abs(dx) > abs(dy):
            steps = [(1 if dx > 0 else -1, 0), (0, 1 if dy > 0 else -1)]
        else:
            steps = [(0, 1 if dy > 0 else -1), (1 if dx > 0 else -1, 0)]

        for sx, sy in steps:
            if sx == 0 and sy == 0:
                continue

            nx, ny = monster.x + sx, monster.y + sy

            if not self.is_walkable(nx, ny):
                continue
            if nx == self.player.x and ny == self.player.y:
                continue
            if self.monster_at(nx, ny):
                continue

            monster.x, monster.y = nx, ny
            return

        self.move_monster_random(monster)

    def monsters_turn(self):
        """원래 노트북에서 통째로 빠져 있던 함수."""
        for monster in list(self.monsters):
            if not monster.alive:
                continue

            if self.monster_distance(monster) == 1:
                self.monster_attack(monster)
            elif self.monster_distance(monster) <= CHASE_RADIUS:
                self.chase_player(monster)
            else:
                self.move_monster_random(monster)

            if not self.player.alive:
                break

    # ------------------------------------------------------------ 플레이어 행동

    def move_or_attack(self, dx, dy):
        """이동. 그 칸에 몬스터가 있으면 공격. 턴 소모 여부를 반환."""
        nx = self.player.x + dx
        ny = self.player.y + dy

        monster = self.monster_at(nx, ny)
        if monster:
            self.attack_monster(monster)
            return True

        if nx < 0 or nx >= MAP_WIDTH or ny < 0 or ny >= MAP_HEIGHT:
            self.log("맵 밖으로는 나갈 수 없습니다.")
            return False

        if self.dungeon[ny][nx] == WALL:
            self.log("벽에 막혔습니다.")
            return False

        self.player.x = nx
        self.player.y = ny

        self.check_trap()
        self.auto_pickup()

        return True

    def check_trap(self):
        trap = self.trap_at(self.player.x, self.player.y)
        if trap is None:
            return

        # 이미 한 번 터진 함정은 지도에 ^ 로 남기고 다시 발동하지 않는다
        if trap.visible:
            return

        trap.visible = True

        self.log("함정을 밟았습니다!")
        self.damage_player(trap.damage, source="함정")

        if self.player.alive and random.random() < 0.4:
            self.player.poisoned = True
            self.player.poison_turns = 5
            self.log("독에 걸렸습니다!")

    def auto_pickup(self):
        """금화는 밟으면 자동으로 줍는다. 물약은 G로 줍는다."""
        item = self.item_at(self.player.x, self.player.y)

        if item and item.item_type == "gold":
            self.player.gold += item.value
            self.items.remove(item)
            self.log(f"{item.value} 골드를 얻었습니다.")

    def pickup_item(self):
        item = self.item_at(self.player.x, self.player.y)

        if item is None:
            # 보물 위라면 보물 획득 시도
            if self.is_on_treasure():
                return self.collect_treasure()

            self.log("여기에는 아이템이 없습니다.")
            return False

        if item.item_type == "gold":
            self.player.gold += item.value
            self.log(f"{item.value} 골드를 얻었습니다.")
        else:
            self.player.inventory.append(item)
            self.log(f"{item.name}을(를) 주웠습니다.")

        self.items.remove(item)
        return True

    def use_potion(self):
        """input() 없이 물약을 사용한다 (콜백 안에서 input은 멈춘다)."""
        for i, item in enumerate(self.player.inventory):
            if item.item_type != "heal":
                continue

            old_hp = self.player.hp
            self.player.hp = min(self.player.max_hp,
                                 self.player.hp + item.value)
            healed = self.player.hp - old_hp

            self.player.inventory.pop(i)

            self.log(f"{item.name} 사용. HP +{healed}")

            if self.player.poisoned:
                self.player.poisoned = False
                self.player.poison_turns = 0
                self.log("독이 해소되었습니다.")

            return True

        self.log("사용할 물약이 없습니다.")
        return False

    def apply_poison(self):
        if not self.player.poisoned:
            return

        self.damage_player(1, source="독")
        self.player.poison_turns -= 1

        if self.player.poison_turns <= 0:
            self.player.poisoned = False
            self.log("독이 사라졌습니다.")

    # ------------------------------------------------------------ 층 이동 / 승리

    def is_on_stairs(self):
        return (self.stairs is not None
                and self.player.x == self.stairs.x
                and self.player.y == self.stairs.y)

    def is_on_treasure(self):
        return (self.treasure is not None
                and self.player.x == self.treasure.x
                and self.player.y == self.treasure.y)

    def descend(self):
        if not self.is_on_stairs():
            self.log("계단 위에 있지 않습니다. (>)")
            return False

        self.floor += 1
        self.build_floor()
        self.log(f"{self.floor}층으로 내려갑니다.")
        return True

    def collect_treasure(self):
        if not self.is_on_treasure():
            return False

        self.treasure = None
        self.won = True
        self.running = False
        self.log("최종 보물을 손에 넣었습니다!")
        return True

    # ------------------------------------------------------------ 명령 처리

    def handle_key(self, key):
        """
        키 하나를 처리한다.
        반환값은 없고, 상태만 바뀐다. 화면은 UI 쪽에서 다시 그린다.
        """
        if key is None:
            return

        key = str(key).lower().strip()

        if not self.running:
            if key == "r":
                self.new_game()
            return

        moves = {
            "w": (0, -1),
            "s": (0, 1),
            "a": (-1, 0),
            "d": (1, 0),
        }

        took_turn = False

        if key in moves:
            dx, dy = moves[key]
            took_turn = self.move_or_attack(dx, dy)

        elif key == "g":
            took_turn = self.pickup_item()

        elif key == "u":
            took_turn = self.use_potion()

        elif key == ">":
            took_turn = self.descend()
            if took_turn:
                # 층을 새로 만들었으므로 몬스터 턴은 건너뛴다
                return

        elif key == "i":
            self.show_inventory = not self.show_inventory
            return

        elif key in (".", " ", "z"):
            self.log("잠시 기다립니다.")
            took_turn = True

        elif key == "q":
            self.running = False
            self.log("게임을 종료했습니다. (R: 다시 시작)")
            return

        else:
            return

        if not took_turn:
            return

        self.turn += 1

        if not self.player.alive or self.won:
            return

        self.apply_poison()

        if not self.player.alive:
            return

        self.monsters_turn()

        if not self.player.alive:
            return

        self.reveal_area()
