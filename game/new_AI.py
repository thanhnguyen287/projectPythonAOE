from player import player_list
from .utils import tile_founding, better_look_around, RESSOURCE_LIST
from units import Villager
from random import randint, random
from settings import MAP_SIZE_X, MAP_SIZE_Y


class new_AI:

    def __init__(self, player, map):
        self.player = player
        self.map = map
        self.tc_pos = self.player.towncenter_pos

        #we chose a behaviour between all the behaviours we defined
        self.behaviour_possible = ["neutral"]
        r = randint(0, len(self.behaviour_possible)-1)
        self.behaviour = self.behaviour_possible[r]

        # the range (in layers) that the AI will go to. It increase when the AI becomes stronger
        # or is lacking ressources
        self.range = 3

        # this will be used to know if the AI needs to gather or not, and to expand or not
        self.needed_ressource = []

        # number of each ressource needed per villager
        self.base_quantity_of_each_ressource = [400, 200, 100, 200]
        self.quantity_of_each_ressource = self.base_quantity_of_each_ressource

        #for defense
        self.has_defense = False
        self.tower_pos = None

        #the building queue for the building we want to build
        self.building_queue = []

        # a list of tiles to manage the gathering of ressources with the multiple units
        self.targeted_tiles = []

        # a list of the tiles where buildings are being built, to not build more on it
        self.in_building_tiles = []

        # a list of enemy units focused
        self.units_focused = []

        # to know if we are developping pop or not to know if we can build a building or not
        self.dev_pop = False

    # ==================================================================================================================
    # ----------------------------------------CONTROL AND RUNNING FUNCTIONS---------------------------------------------
    # ==================================================================================================================

    def chose_behaviour(self):
        # welook at the enemy units within 10 tiles of our town center to know if we should go in defense mode
        for p in player_list:
            if p != self.player:
                if self.behaviour == "defense":
                    break
                for u in p.unit_list:
                    if self.behaviour == "defense":
                        break
                    # if a enemy unit is in a 10 tiles range of the towncenter
                    if abs(self.tc_pos[0] - u.pos[0]) <= 1 and abs(self.tc_pos[1] - u.pos[1]) <= 1:  # in tiles
                        self.behaviour = "defense"
                        break
        # if we are the strongest we attack !
        if self.is_stronger():
            self.behaviour = "attack"
        # if we dont attack not defend, we are neutral
        elif self.behaviour != "defense":
            self.behaviour = "neutral"


    # this needs a little correction, it is too... confident
    def expand(self):
        # the idea is that the AI will check if she is stronger to know if she can expand
        if self.is_stronger():
            self.range += 1

        # WARNING i will modify this so the AI expand only if a ressource she needs is lacking
        # or if she is neutral but lacking ressources to gather
        elif self.behaviour == "neutral" and self.range < MAP_SIZE_X and self.range < MAP_SIZE_Y:
            ressources_available = []
            for r in self.needed_ressource:
                ressources_available = []
                tiles_to_gather = tile_founding(len(self.player.unit_list), 1, self.range, self.map.map, self.player, r)
                if len(tiles_to_gather) >= len(self.player.unit_list):
                    ressources_available.append(True)
                else:
                    ressources_available.append(False)

            if self.needed_ressource and True not in ressources_available:
                self.range += 1
                print(self.range)


    def run(self):
        if self.player.towncenter is not None:

            #we execute a different routine for each behaviour that exists
            if self.behaviour == "neutral":
                self.neutral_routine()
            elif self.behaviour == "defense":
                self.defense_routine()
            elif self.behaviour == "attack":
                self.attack_routine()

            # at the end, we try to expand (go to expand method to see the conditions)
            self.expand()


    # ==================================================================================================================
    # ------------------------------------------------MAIN ROUTINES-----------------------------------------------------
    # ==================================================================================================================

    # gather, build, spawn villagers
    def neutral_routine(self):
        self.planning_gathering()

        # if we dont need ressources, we are not training units, we have free pop space and we have at least as many
        # buildings as units, then we can train a new unit
        if not self.needed_ressource and self.player.towncenter.queue == 0 and \
                self.player.current_population < self.player.max_population:

            self.population_developpement_routine()
            self.dev_pop = True

        # if we dont train unit, we will try to gather or to build
        else:
            for u in self.player.unit_list:

                # if we need ressources and the unit is a villager and he is free, he will go gather
                if self.needed_ressource and isinstance(u, Villager) and u.building_to_create is None \
                        and not u.is_moving_to_attack and u.target is None:
                    if u.gathered_ressource_stack < u.stack_max:
                        self.gathering_routine(u)
                    else:
                        u.go_to_townhall()

                # if we dont need ressources the villager is going to build
                elif isinstance(u, Villager) and not u.is_moving_to_attack and u.target is None:
                    self.building_routine(u)

        #to reset frozen villagers
        for u in self.player.unit_list:
            if u.is_moving_to_gather and not u.searching_for_path:
                u.is_moving_to_gather = False
                print(u, "reseted")

        #to free tiles and to reset dev pop var
        self.free_tiles()
        self.dev_pop = False

    def defense_routine(self):
        for p in player_list:
            if p != self.player:
                for u in p.unit_list:
                    if abs(self.tc_pos[0] - u.pos[0]) <= 1 and abs(self.tc_pos[1] - u.pos[1]) <= 1 \
                            and not u in self.units_focused:  # in tiles

                        for my_u in self.player.unit_list:
                            # et rajouter si le type de l'unité n'est pas un villageois
                            self.reset_villager(my_u)

                            if my_u.target is None and not u in self.units_focused:
                                my_u.go_to_attack(u.pos)
                            self.units_focused.append(u)
        #creer une routine de repli des villageois près de l'hotel de ville


    def attack_routine(self):
        pass

    # TODO

    # ==================================================================================================================
    # -------------------------------------------------SUB ROUTINES-----------------------------------------------------
    # ==================================================================================================================

    def gathering_routine(self, unit):
        for r in self.needed_ressource:
            if unit.targeted_ressource is None:
                ressource = None
                if r == "wood": ressource = "tree"
                elif r == "stone": ressource = "rock"
                elif r == "gold": ressource = "gold"
                elif r == "berrybush": ressource = "food"

                if unit.gathered_ressource_stack == 0 or unit.stack_type == ressource:
                    tiles_to_gather = tile_founding(10, 1, self.range, self.map.map, self.player, r)
                    found = False
                    for i in range(len(tiles_to_gather)):
                        if tiles_to_gather:
                            pos_x = tiles_to_gather[i][0]
                            pos_y = tiles_to_gather[i][1]
                            if better_look_around(unit.pos, (pos_x, pos_y), self.map.map) and not found and \
                                    (pos_x, pos_y) not in self.targeted_tiles:
                                unit.go_to_ressource(tiles_to_gather[i])
                                self.targeted_tiles.append((pos_x, pos_y))
                                found = True

                else:
                    unit.go_to_townhall()

    def building_routine(self, u):
        if u.building_to_create is None:
            # first we try to build what's on the queue
            if self.building_queue:
                to_build = self.building_queue[0][0]
                pos = self.building_queue[0][1]
                u.go_to_build(pos, to_build)
                self.map.collision_matrix[pos[1]][pos[0]] = 0
                self.building_queue.remove(self.building_queue[0])

            #if there is nothing in the queue, we build a house if we have more than 70% of the pop
            elif self.player.current_population >= 0.7 * self.player.max_population:
                tiles_to_build = tile_founding(5, 2, self.range, self.map.map, self.player, "", self.map)
                if tiles_to_build:
                    r = randint(0, len(tiles_to_build)-1)
                    pos = tiles_to_build[r]
                    self.building_queue.append(("House", pos))
                    self.in_building_tiles.append(pos)

            #else we try to build a defense if we dont have one
            elif not self.has_defense:
                self.build_defense()


            #else we just build a farm
            else:
                tiles_to_build = tile_founding(5, 2, self.range, self.map.map, self.player, "", self.map)
                if tiles_to_build:
                    r = randint(0, len(tiles_to_build)-1)
                    pos = tiles_to_build[r]
                    self.building_queue.append(("Farm", pos))
                    self.in_building_tiles.append(pos)

        # to make the villager able to build other buildings after he buildt a building, we release him
        if u.building_to_create is not None:
            pos_x = u.building_to_create["pos"][0]
            pos_y = u.building_to_create["pos"][1]

            for b in u.owner.building_list:
                if b.pos[0] == pos_x and b.pos[1] == pos_y and not u.is_moving_to_build:
                    if not b.is_being_built:
                        self.in_building_tiles.remove(u.building_to_create["pos"])
                        u.building_to_create = None
                        u.is_building = False
                        print(u, "freed")

    def population_developpement_routine(self):
        nb_of_villagers = 0
        for u in self.player.unit_list:
            if isinstance(u, Villager):
                nb_of_villagers +=1
        if nb_of_villagers < 5:
            self.player.towncenter.train(Villager)
        else:
            pass
            #military unit training


    def poking_routine(self):
        for u in self.player.unit_list:
            for p in player_list:
                if p != self.player:
                    if u.building_to_create is None and not u.is_moving_to_gather and not u.is_moving_to_attack \
                            and u.targeted_ressource is None and not u.is_gathering and u.target is None:
                        r = random()
                        if r <= 0.001:
                            u.go_to_attack(p.towncenter.pos)

    # ==================================================================================================================
    # ---------------------------------------------USEFUL FUNCTIONS-----------------------------------------------------
    # ==================================================================================================================

    def planning_gathering(self):
        for i in range(4):
            if self.player.resources[i] <= self.quantity_of_each_ressource[i] and \
                    RESSOURCE_LIST[i] not in self.needed_ressource:
                self.needed_ressource.append(RESSOURCE_LIST[i])
            elif self.player.resources[i] > self.quantity_of_each_ressource[i] and \
                    RESSOURCE_LIST[i] in self.needed_ressource:
                self.needed_ressource.remove(RESSOURCE_LIST[i])

    def is_stronger(self):
        #we count the number of attack unit we get
        number_of_my_attack_unit = 0
        for u in self.player.unit_list:
            if type(u) != Villager:
                number_of_my_attack_unit += 1


    # for each enemy player we count the number of their enemy attack unit to know if we are stronger
        for p in player_list:
            number_of_their_attack_unit = 0
            if p != self.player:
                # we have at least 25% more units, only works without fog of war because we are looking at all
                # enemy units
                for u in p.unit_list:
                    if type(u) != Villager:
                        number_of_their_attack_unit += 1

                if number_of_my_attack_unit != 0 and number_of_my_attack_unit >= 1.25 * number_of_their_attack_unit:
                    return True
                else:
                    return False
        return False

    def free_tiles(self):
        for tile in self.targeted_tiles:
            if self.map.map[tile[0]][tile[1]]["tile"] == "":
                self.targeted_tiles.remove(tile)


    def reset_villager(self, u):
        u.is_moving_to_gather = False
        u.is_moving_to_attack = False
        u.is_moving_to_build = False

        u.building_to_create = None
        u.targeted_ressource = None
        u.target = None

        u.is_building = False
        u.is_gathering = False
        u.is_attacking = False

    def build_defense(self):
        #we find a place to build the tower
        nb_tiles = 1
        while not self.has_defense:
            tiles_to_build = tile_founding(nb_tiles, 3, self.range, self.map.map, self.player, "", self.map)
            if tiles_to_build:
                r = randint(0, len(tiles_to_build)-1)
                pos = tiles_to_build[r]
                if self.player.side == "top" and pos[0] >= self.player.towncenter_pos[0] and pos[1] >= self.player.towncenter_pos[1]-1:
                    self.building_queue.append(("Tower", pos))
                    self.in_building_tiles.append(pos)

                    self.has_defense = True
                    self.tower_pos = pos

                elif self.player.side == "bot" and pos[0] <= self.player.towncenter_pos[0]+1 and pos[1] <= self.player.towncenter_pos[1]:
                    self.building_queue.append(("Tower", pos))
                    self.in_building_tiles.append(pos)

                    self.has_defense = True
                    self.tower_pos = pos

                elif self.player.side == "left" and pos[0] >= self.player.towncenter_pos[0] and pos[1] <= self.player.towncenter_pos[1]:
                    self.building_queue.append(("Tower", pos))
                    self.in_building_tiles.append(pos)

                    self.has_defense = True
                    self.tower_pos = pos

                elif self.player.side == "right" and pos[0] <= self.player.towncenter_pos[0]+1 and pos[1] >= self.player.towncenter_pos[1]:
                    self.building_queue.append(("Tower", pos))
                    self.in_building_tiles.append(pos)

                    self.has_defense = True
                    self.tower_pos = pos
            nb_tiles += 1


        #we look for the eight surrounding position if we can build walls
        eight_pos = [(pos[0]+1, pos[1]-1), (pos[0]+1, pos[1]), (pos[0]+1, pos[1]+1), (pos[0], pos[1]+1),
                     (pos[0]-1, pos[1]+1), (pos[0]-1, pos[1]), (pos[0]-1, pos[1]-1), (pos[0], pos[1]-1)]

        for i in range(8):
            pos = eight_pos[i]
            if self.map.collision_matrix[pos[1]][pos[0]]:
                self.building_queue.append(("Wall", pos))
                self.in_building_tiles.append(pos)