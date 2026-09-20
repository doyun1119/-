# -*- coding: utf-8 -*-
"""
rogue_game.py
=============
게임 규칙 담당. 모든 상태를 Game 클래스 하나가 들고 있습니다.

추가된 것
- 장비: 근접무기 / 원거리무기 / 방어구 / 반지 2개
- 원거리 공격 (F): 시야가 트인 가장 가까운 적을 화살로 쏜다
- 10층 구성, 층이 깊을수록 높은 등급의 장비가 나온다
- 인벤토리 번호키(1~9)로 사용/장착

화면 출력(print)은 하지 않습니다. 메시지는 self.messages 에 쌓이고
그리기는 노트북(UI)에서 담당합니다.
"""

import random

from rogue_core import (
    MAP_WIDTH, MAP_HEIGHT, WALL, FLOOR,
    MAX_FLOOR, VIEW_RADIUS, CHASE_RADIUS,
    MONSTER_TYPES,
    SLOT_MELEE, SLOT_RANGED, SLOT_ARMOR, SLOT_RING1, SLOT_RING2,
    SLOT_LABELS,
    Player, Trap, Stairs, Treasure,
    create_monster, create_simple_item, random_equipment,
    floor_base_tier, generate_dungeon,
)

MAX_MESSAGES = 6
MAX_INVENTORY = 9      # 번호키 1~9


class Game:

    # ------------------------------------------------------------ 초기화

    def __init__(self):
        self.player = Player()
        self.new_game()

    def new_game(self):
        self.player.reset()

        self.floor = 1
        self.turn = 0

        self.running = True
        self.won = False

        self.messages = []
        self.show_inventory = True     # 장비 시스템이 생겼으니 기본으로 펼침
        self.drop_mode = False

        self.build_floor()

        self.log("던전에 들어섰습니다. WASD 이동 · F 사격 · G 줍기")

    def build_floor(self):
        """현재 층을 새로 만든다."""
        self.dungeon, self.rooms = generate_dungeon()

        self.monsters = []
        self.items = []
        self.traps = []
        self.stairs = None
        self.treasure = None

        self.explored = set()

        self.player.x, self.player.y = self.rooms[0].center()

        if self.floor < MAX_FLOOR:
            x, y = self.random_free_position()
            self.stairs = Stairs(x, y)

        # 몬스터
        for _ in range(4 + (self.floor * 2) // 3):
            self.spawn_monster()

        # 소모품
        for _ in range(2 + self.floor // 2):
            self.spawn_simple_item("물약")
        for _ in range(2):
            self.spawn_simple_item("골드")
        for _ in range(2):
            self.spawn_simple_item("화살")

        # 장비 (층마다 2~3개)
        for _ in range(random.randint(2, 3)):
            self.spawn_equipment()

        # 함정
        for _ in range(1 + self.floor // 2):
            self.spawn_trap()

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
        candidates = [
            (x, y)
            for y in range(MAP_HEIGHT)
            for x in range(MAP_WIDTH)
            if self.dungeon[y][x] == FLOOR and not self.is_occupied(x, y)
        ]

        if not candidates:
            candidates = [
                (x, y)
                for y in range(MAP_HEIGHT)
                for x in range(MAP_WIDTH)
                if self.dungeon[y][x] == FLOOR
            ]

        return random.choice(candidates)

    # ------------------------------------------------------------ 배치

    def spawn_monster(self):
        """그 층에 등장 가능한 몬스터 중에서 고른다."""
        names = [
            name for name, data in MONSTER_TYPES.items()
            if data["floor"] <= self.floor
        ]

        # 희귀도 기준. 너무 낮은 층 몬스터는 점점 덜 나온다.
        weights = []
        for name in names:
            data = MONSTER_TYPES[name]
            weight = data["rarity"]

            if self.floor - data["floor"] > 5:
                weight = max(1, weight // 3)

            weights.append(weight)

        name = random.choices(names, weights=weights, k=1)[0]

        x, y = self.random_free_position()
        self.monsters.append(create_monster(name, x, y, self.floor))

    def spawn_simple_item(self, name):
        x, y = self.random_free_position()
        self.items.append(create_simple_item(name, x, y, self.floor))

    def spawn_equipment(self):
        x, y = self.random_free_position()
        self.items.append(random_equipment(self.floor, x, y))

    def spawn_trap(self):
        x, y = self.random_free_position()
        damage = random.randint(2, 4 + self.floor)
        self.traps.append(Trap(x, y, damage))

    # ------------------------------------------------------------ 시야

    def reveal_area(self, radius=VIEW_RADIUS):
        px, py = self.player.x, self.player.y

        for y in range(max(0, py - radius), min(MAP_HEIGHT, py + radius + 1)):
            for x in range(max(0, px - radius), min(MAP_WIDTH, px + radius + 1)):
                if abs(px - x) + abs(py - y) <= radius:
                    self.explored.add((x, y))

    def is_explored(self, x, y):
        return (x, y) in self.explored

    def has_line_of_sight(self, x1, y1, x2, y2):
        """두 점 사이에 벽이 없는지 (브레젠험 직선)."""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)

        x, y = x1, y1
        sx = 1 if x2 > x1 else -1
        sy = 1 if y2 > y1 else -1

        error = dx - dy

        while True:
            if (x, y) != (x1, y1) and (x, y) != (x2, y2):
                if not self.is_walkable(x, y):
                    return False

            if x == x2 and y == y2:
                return True

            double_error = error * 2

            if double_error > -dy:
                error -= dy
                x += sx

            if double_error < dx:
                error += dx
                y += sy

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
        power = self.player.attack

        damage = random.randint(max(1, power - 2), power + 2)

        critical = random.random() < self.player.crit_chance
        if critical:
            damage *= 2

        damage = max(1, damage - monster.defense)
        monster.hp -= damage

        weapon = self.player.equipment[SLOT_MELEE]
        weapon_name = weapon.base_name if weapon else "맨손"

        if critical:
            self.log(f"치명타! {weapon_name}(으)로 {monster.name}에게 {damage} 피해!")
        else:
            self.log(f"{weapon_name}(으)로 {monster.name}에게 {damage} 피해!")

        self.check_monster_death(monster)

    def fire_ranged(self):
        """가장 가까운, 시야가 트인 적을 쏜다."""
        weapon = self.player.equipment[SLOT_RANGED]

        if weapon is None:
            self.log("원거리 무기를 장착하지 않았습니다.")
            return False

        if self.player.arrows <= 0:
            self.log("화살이 없습니다. ( 를 주우세요.")
            return False

        target = self.find_ranged_target()

        if target is None:
            self.log("사거리 안에 보이는 적이 없습니다.")
            return False

        self.player.arrows -= 1

        power = self.player.ranged_attack
        damage = random.randint(max(1, power - 1), power + 2)

        critical = random.random() < self.player.crit_chance
        if critical:
            damage *= 2

        damage = max(1, damage - target.defense // 2)   # 원거리는 방어 관통 절반
        target.hp -= damage

        if critical:
            self.log(f"치명타! {weapon.base_name} → {target.name} {damage} 피해!")
        else:
            self.log(f"{weapon.base_name} → {target.name} {damage} 피해! (화살 {self.player.arrows})")

        self.check_monster_death(target)
        return True

    def find_ranged_target(self):
        reach = self.player.ranged_range
        best = None
        best_distance = None

        for monster in self.monsters:
            if not monster.alive:
                continue

            distance = max(
                abs(monster.x - self.player.x),
                abs(monster.y - self.player.y),
            )

            if distance > reach:
                continue

            if not self.has_line_of_sight(
                self.player.x, self.player.y, monster.x, monster.y
            ):
                continue

            if best is None or distance < best_distance:
                best = monster
                best_distance = distance

        return best

    def check_monster_death(self, monster):
        if monster.hp > 0:
            return

        monster.hp = 0
        monster.alive = False

        if monster in self.monsters:
            self.monsters.remove(monster)

        self.log(f"{monster.name} 처치! 경험치 +{monster.xp}")

        self.player.xp += monster.xp
        self.check_level_up()

        # 장비를 떨어뜨릴 때가 있다
        if random.random() < 0.18 and not self.is_occupied(monster.x, monster.y):
            self.items.append(random_equipment(self.floor, monster.x, monster.y))
            self.log("무언가를 떨어뜨렸습니다.")

    def monster_attack(self, monster):
        damage = random.randint(max(1, monster.attack - 1), monster.attack + 1)
        damage = max(1, damage - self.player.defense)
        self.damage_player(damage, source=monster.name)

    def check_level_up(self):
        while self.player.xp >= self.player.next_xp:
            self.player.xp -= self.player.next_xp
            self.player.level += 1

            self.player.base_max_hp += 5
            self.player.hp = self.player.max_hp
            self.player.base_attack += 1
            self.player.base_defense += 1
            self.player.next_xp = int(self.player.next_xp * 1.5)

            self.log(f"레벨 업! LV {self.player.level} (HP 완전 회복)")

    # ------------------------------------------------------------ 몬스터 턴

    def monster_distance(self, monster):
        return abs(monster.x - self.player.x) + abs(monster.y - self.player.y)

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
        """골드와 화살은 밟으면 자동으로 줍는다."""
        item = self.item_at(self.player.x, self.player.y)
        if item is None:
            return

        if item.item_type == "gold":
            self.player.gold += item.value
            self.items.remove(item)
            self.log(f"{item.value} 골드를 얻었습니다.")

        elif item.item_type == "ammo":
            self.player.arrows += item.value
            self.items.remove(item)
            self.log(f"화살 {item.value}개 (보유 {self.player.arrows})")

    def pickup_item(self):
        item = self.item_at(self.player.x, self.player.y)

        if item is None:
            if self.is_on_treasure():
                return self.collect_treasure()

            self.log("여기에는 아이템이 없습니다.")
            return False

        if item.item_type == "gold":
            self.player.gold += item.value
            self.items.remove(item)
            self.log(f"{item.value} 골드를 얻었습니다.")
            return True

        if item.item_type == "ammo":
            self.player.arrows += item.value
            self.items.remove(item)
            self.log(f"화살 {item.value}개 (보유 {self.player.arrows})")
            return True

        if len(self.player.inventory) >= MAX_INVENTORY:
            self.log(f"가방이 가득 찼습니다. (최대 {MAX_INVENTORY})")
            return False

        self.items.remove(item)
        self.player.inventory.append(item)
        self.log(f"{item.name} 획득")

        return True

    # ------------------------------------------------------------ 인벤토리 / 장비

    def use_slot(self, index):
        """인벤토리 index(0부터) 아이템을 쓰거나 장착한다."""
        if index < 0 or index >= len(self.player.inventory):
            self.log("그 칸은 비어 있습니다.")
            return False

        item = self.player.inventory[index]

        if item.item_type == "heal":
            return self.drink_potion(index)

        if item.is_equipment():
            return self.equip(index)

        self.log("사용할 수 없는 아이템입니다.")
        return False

    def drop_slot(self, index):
        """인벤토리 index 아이템을 바닥에 버린다."""
        if index < 0 or index >= len(self.player.inventory):
            self.log("그 칸은 비어 있습니다.")
            return False

        if self.item_at(self.player.x, self.player.y):
            self.log("여기에는 이미 아이템이 있습니다.")
            return False

        item = self.player.inventory.pop(index)
        item.x = self.player.x
        item.y = self.player.y
        self.items.append(item)

        self.log(f"{item.name}을(를) 버렸습니다.")
        return True

    def drink_potion(self, index=None):
        """index 가 없으면 가방에서 물약을 알아서 찾는다."""
        if index is None:
            for i, item in enumerate(self.player.inventory):
                if item.item_type == "heal":
                    index = i
                    break

        if index is None:
            self.log("물약이 없습니다.")
            return False

        item = self.player.inventory[index]

        old_hp = self.player.hp
        self.player.hp = min(self.player.max_hp, self.player.hp + item.value)
        healed = self.player.hp - old_hp

        self.player.inventory.pop(index)
        self.log(f"{item.name} 사용. HP +{healed}")

        if self.player.poisoned:
            self.player.poisoned = False
            self.player.poison_turns = 0
            self.log("독이 해소되었습니다.")

        return True

    def choose_ring_slot(self):
        """빈 반지 칸을 먼저, 둘 다 차 있으면 반지1을 교체."""
        if self.player.equipment[SLOT_RING1] is None:
            return SLOT_RING1
        if self.player.equipment[SLOT_RING2] is None:
            return SLOT_RING2
        return SLOT_RING1

    def equip(self, index):
        item = self.player.inventory[index]

        if item.item_type == "ring":
            slot = self.choose_ring_slot()
        else:
            slot = item.slot()

        old = self.player.equipment[slot]

        self.player.equipment[slot] = item
        self.player.inventory.pop(index)

        if old is not None:
            self.player.inventory.append(old)
            self.log(f"{SLOT_LABELS[slot]}: {old.name} → {item.name}")
        else:
            self.log(f"{SLOT_LABELS[slot]} 장착: {item.name}")

        # 활력의 반지를 벗으면 최대 HP가 줄 수 있다
        if self.player.hp > self.player.max_hp:
            self.player.hp = self.player.max_hp

        return True

    def apply_poison(self):
        if not self.player.poisoned:
            return

        self.damage_player(1, source="독")
        self.player.poison_turns -= 1

        if self.player.poison_turns <= 0:
            self.player.poisoned = False
            self.log("독이 사라졌습니다.")

    def apply_regen(self):
        """재생의 반지: 값이 클수록 자주 1 회복."""
        rate = self.player.regen_rate
        if rate <= 0:
            return

        interval = max(2, 8 - rate)

        if self.turn % interval == 0 and self.player.hp < self.player.max_hp:
            self.player.hp += 1

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
        self.log(f"{self.floor}층 도착 — 이 층의 기준 등급 {floor_base_tier(self.floor)}")
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

        elif key == "f":
            took_turn = self.fire_ranged()

        elif key == "g":
            took_turn = self.pickup_item()

        elif key == "u":
            took_turn = self.drink_potion()

        elif key.isdigit() and key != "0":
            index = int(key) - 1
            if self.drop_mode:
                took_turn = self.drop_slot(index)
                self.drop_mode = False
            else:
                took_turn = self.use_slot(index)

        elif key == "x":
            self.drop_mode = not self.drop_mode
            if self.drop_mode:
                self.show_inventory = True
                self.log("버리기 모드: 숫자키로 버릴 칸을 고르세요. (X 취소)")
            else:
                self.log("버리기 모드 취소")
            return

        elif key == ">":
            if self.descend():
                return
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

        self.apply_regen()
        self.monsters_turn()

        if not self.player.alive:
            return

        self.reveal_area()
