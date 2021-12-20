import random
import noise
import pygame.mouse
from .utils import decarte_to_iso, iso_to_decarte
from settings import *
from builds import Farm, TownCenter, House
from player import playerOne
from New_ressources import *
from units import Villager


class Map:
    def __init__(self, hud, entities, grid_length_x, grid_length_y, width, height):
        self.hud = hud
        self.entities = entities
        self.grid_length_x = grid_length_x
        self.grid_length_y = grid_length_y
        self.width = width
        self.height = height
        # anything >1 or <-1, otherwise pnoise will return 0
        self.perlin_scale = grid_length_x / 2
        self.grass_tiles = pygame.Surface(
            (grid_length_x * TILE_SIZE * 2, grid_length_y * TILE_SIZE + 2 * TILE_SIZE)).convert_alpha()
        self.tiles = self.load_images()
        # lists of lists
        self.buildings = [[None for x in range(self.grid_length_x)] for y in range(self.grid_length_y)]
        self.units = [[None for x in range(self.grid_length_x)] for y in range(self.grid_length_y)]
        self.map = self.create_map()
        # used in the fonction that places the townhall randomly on the map
        self.townhall_placed = False
        self.place_x = 0
        self.place_y = 0
        # here we place the townhall randomly on the map
        self.place_townhall()
        self.collision_matrix = self.create_collision_matrix()
        # new_villager = Villager((0, 0), playerOne, self.map)
        # self.units[0][0] = new_villager
        # used when selecting a tile to build
        self.temp_tile = None
        # used when examining elements of the map
        self.examined_tile = None
        # starting unit
        start_unit = Villager(self.map[5][5]["grid"], playerOne, self)
        self.units[5][5] = start_unit
        self.collision_matrix[start_unit.pos[1]][start_unit.pos[0]] = 0
        self.map[start_unit.pos[0]][start_unit.pos[1]]["collision"] = True

    def create_map(self):
        map = []
        for grid_x in range(self.grid_length_x):
            map.append([])
            for grid_y in range(self.grid_length_y):
                map_tile = self.grid_to_map(grid_x, grid_y)
                map[grid_x].append(map_tile)
                render_pos = map_tile["render_pos"]
                # self.grass_tiles.getwidth()/2 : offset
                self.grass_tiles.blit(self.tiles["grass"],
                                      (render_pos[0] + self.grass_tiles.get_width() / 2, render_pos[1]))
                scroll = pygame.Vector2(0, 0)
                scroll.x = 0
                scroll.y = 0
        return map

    def update(self, camera, screen):
        mouse_pos = pygame.mouse.get_pos()
        mouse_action = pygame.mouse.get_pressed()
        self.temp_tile = None

        # the player selects a building in the hud
        if self.hud.selected_tile is not None and self.hud.examined_tile is not None:
            grid_pos = self.mouse_to_grid(mouse_pos[0], mouse_pos[1], camera.scroll)
            # if we can't place the building on the tile, there's no need to do the following
            if self.can_place_tile(grid_pos):
                if self.hud.examined_tile.name == "Villager":
                    self.hud.bottom_left_menu = self.hud.villager_menu
                elif self.hud.examined_tile.name == "Town Center":
                    self.hud.bottom_left_menu = self.hud.town_hall_menu

                image = self.hud.selected_tile["image"].copy()
                name = self.hud.selected_tile["name"]
                # setting transparency to make sure player understands it's not built
                image.set_alpha(100)
                collision = None
                if grid_pos[0] < self.grid_length_x and grid_pos[1] < self.grid_length_y:
                    render_pos = self.map[grid_pos[0]][grid_pos[1]]["render_pos"]
                    iso_poly = self.map[grid_pos[0]][grid_pos[1]]["iso_poly"]
                    collision = self.map[grid_pos[0]][grid_pos[1]]["collision"]

                    self.temp_tile = {
                        "name" : name,
                        "image": image,
                        "render_pos": render_pos,
                        "iso_poly": iso_poly,
                        "collision": collision,
                        "2x2_collision": False
                    }

                else:
                    pass
                # if we left_click to build : we will place the building in the map if the targeted tile is empty
                if mouse_action[0] and not collision:
                    # we create an instance of the selected building
                    if self.hud.selected_tile["name"] == "Farm":
                        new_building = Farm((grid_pos[0], grid_pos[1]), self, playerOne)
                        # to add it to the entities list on our map
                        self.entities.append(new_building)
                        # grid_pos 0 and grid_pos 1 means : grid_pos_x and grid_pos_y, not the specific tile near the origin
                        self.buildings[grid_pos[0]][grid_pos[1]] = new_building

                    elif self.hud.selected_tile["name"] == "Town center":
                        new_building = TownCenter((grid_pos[0], grid_pos[1]), self, playerOne)
                        self.entities.append(new_building)
                        self.buildings[grid_pos[0]][grid_pos[1]] = new_building
                        # additional collision bc town center is 2x2 tile, not 1x1
                        self.collision_matrix[grid_pos[1]][grid_pos[0] + 1] = 0
                        self.collision_matrix[grid_pos[1] - 1][grid_pos[0] + 1] = 0
                        self.collision_matrix[grid_pos[1] - 1][grid_pos[0]] = 0

                        self.map[grid_pos[0] + 1][grid_pos[1]]["collision"] = True
                        self.map[grid_pos[0]][grid_pos[1] - 1]["collision"] = True
                        self.map[grid_pos[0] + 1][grid_pos[1] - 1]["collision"] = True
                        self.map[grid_pos[0]][grid_pos[1]]["2x2_collision"] = True

                    elif self.hud.selected_tile["name"] == "House":
                        new_building = House((grid_pos[0], grid_pos[1]), self, playerOne)
                        self.entities.append(new_building)
                        self.buildings[grid_pos[0]][grid_pos[1]] = new_building

                    self.map[grid_pos[0]][grid_pos[1]]["collision"] = True
                    self.collision_matrix[grid_pos[1]][grid_pos[0]] = 0
                    self.hud.selected_tile = None

        # the player hasn't selected something to build, he will interact with what's on the map
        else:
            grid_pos = self.mouse_to_grid(mouse_pos[0], mouse_pos[1], camera.scroll)
            if grid_pos[0] < self.grid_length_x and grid_pos[1] < self.grid_length_y:
                collision2 = self.map[grid_pos[0]][grid_pos[1]]["collision"]
                # we deselect the object examined when left-clicking if not on hud
                if mouse_action[0] and not collision2 and not self.hud.bottom_hud_rect.collidepoint(mouse_pos):
                    self.examined_tile = None
                    self.hud.examined_tile = None
                    self.hud.bottom_left_menu = None
            # if on the map and left click and the tile isn't empty
            if self.can_place_tile(grid_pos):
                if grid_pos[0] < self.grid_length_x and grid_pos[1] < self.grid_length_y:
                    building = self.buildings[grid_pos[0]][grid_pos[1]]
                    unit = self.units[grid_pos[0]][grid_pos[1]]
                    if mouse_action[0]:
                        self.examined_tile = grid_pos
                        if building is not None:
                            self.hud.examined_tile = building
                            if building.name == "Town center":
                                self.hud.bottom_left_menu = self.hud.town_hall_menu
                            else:
                                self.hud.bottom_left_menu = None

                        else:
                            if unit is not None:
                                self.hud.examined_tile = unit
                                if unit.name == "Villager":
                                    self.hud.bottom_left_menu = self.hud.villager_menu
                                else:
                                    self.hud.bottom_left_menu = None

                else:
                    pass

        # right click, gathering and moving units (fighting in future)
        if mouse_action[2] and 0 <= grid_pos[0] <= 50 and 0 <= grid_pos[1] <= 50:
            if self.hud.examined_tile is not None and self.hud.examined_tile.name == "Villager":
                villager_pos = self.hud.examined_tile.pos

                # if the villager isnt gathering/planning to gather, and there is not collision on the tile we right click on, then he moves
                if not self.map[grid_pos[0]][grid_pos[1]]["collision"] and not \
                        self.units[villager_pos[0]][
                            villager_pos[1]].gathering and self.units[villager_pos[0]][
                    villager_pos[1]].target is None:
                    self.units[villager_pos[0]][villager_pos[1]].move_to(
                        self.map[grid_pos[0]][grid_pos[1]])

                # we check if the tile we right click on is a ressource and if its on an adjacent tile of the villager pos, and if the villager isnt moving
                pos_mouse = self.mouse_to_grid(mouse_pos[0], mouse_pos[1], camera.scroll)
                pos_x = pos_mouse[0]
                pos_y = pos_mouse[1]
                # if the tile next to him is a ressource and we right click on it and he is not moving, he will gather it
                if not self.units[villager_pos[0]][villager_pos[1]].searching_for_path \
                        and (self.map[pos_x][pos_y]["tile"] == "tree" or self.map[pos_x][pos_y][
                    "tile"] == "rock"):

                    if (abs(pos_x - villager_pos[0]) <= 1 and abs(
                            pos_y - villager_pos[1]) == 0) \
                            or (abs(pos_x - villager_pos[0]) == 0 and abs(
                        pos_y - villager_pos[1]) <= 1):

                        self.units[villager_pos[0]][villager_pos[1]].target = \
                            self.map[pos_x][pos_y]
                        self.units[villager_pos[0]][villager_pos[1]].gathering = True

                    # if the tile we right click on is a ressource, he will travel to it and then gather it
                    else:

                        if self.map[pos_x - 1][pos_y]["tile"] == "":
                            self.units[villager_pos[0]][villager_pos[1]].move_to(
                                self.map[pos_x - 1][pos_y])
                            self.units[villager_pos[0]][villager_pos[1]].target = \
                                self.map[pos_x][pos_y]
                        elif self.map[pos_x + 1][pos_y]["tile"] == "":
                            self.units[villager_pos[0]][villager_pos[1]].move_to(
                                self.map[pos_x + 1][pos_y])
                            self.units[villager_pos[0]][villager_pos[1]].target = \
                                self.map[pos_x][pos_y]
                        elif self.map[pos_x][pos_y - 1]["tile"] == "":
                            self.units[villager_pos[0]][villager_pos[1]].move_to(
                                self.map[pos_x][pos_y - 1])
                            self.units[villager_pos[0]][villager_pos[1]].target = \
                                self.map[pos_x][pos_y]
                        elif self.map[pos_x][pos_y + 1]["tile"] == "":
                            self.units[villager_pos[0]][villager_pos[1]].move_to(
                                self.map[pos_x][pos_y + 1])
                            self.units[villager_pos[0]][villager_pos[1]].target = \
                                self.map[pos_x][pos_y]
                        else:
                            self.units[villager_pos[0]][villager_pos[1]].target = None

    def draw(self, screen, camera):
        # Rendering "block", as Surface grass_tiles is in the same dimension of screen so just add (0,0)
        screen.blit(self.grass_tiles, (camera.scroll.x, camera.scroll.y))
        # FOR THE MAP
        for x in range(self.grid_length_x):
            for y in range(self.grid_length_y):
                render_pos = self.map[x][y]["render_pos"]

                # HERE WE DRAW THE MAP TILES
                # Rendering what's on the map, if it is not a tree or rock then render nothing as we already had block with green grass
                tile = self.map[x][y]["tile"]

                # if the tile isnt empty and inst destroyed, we display it
                if tile != "" and tile != "building":
                    screen.blit(self.tiles[tile], (
                        render_pos[0] + self.grass_tiles.get_width() / 2 + camera.scroll.x,
                        render_pos[1] - (self.tiles[tile].get_height() - TILE_SIZE) + camera.scroll.y)
                                )

                    # here we display the health bar of the ressources
                    if (self.examined_tile is not None and x == self.examined_tile[0] and y == self.examined_tile[1]) \
                            or self.map[x][y]["health"] != self.map[x][y]["max_health"]:
                        display_health(screen,
                                       render_pos[0] + self.grass_tiles.get_width() / 2 + camera.scroll.x + 10,
                                       render_pos[1] - (self.tiles[tile].get_height() - TILE_SIZE) + camera.scroll.y,
                                       self.map[x][y]["health"], self.map[x][y]["max_health"])
                        display_health(screen,
                                       render_pos[0] + self.grass_tiles.get_width() / 2 + camera.scroll.x + 10,
                                       render_pos[1] - (self.tiles[tile].get_height() - TILE_SIZE) + camera.scroll.y,
                                       self.map[x][y]["health"], self.map[x][y]["max_health"])

                # HERE WE DRAW THE BUILDINGS ON THE MAP
                # we extract from the buildings list the building we want to display
                building = self.buildings[x][y]
                if building is not None and building.current_health <= 0:
                    self.buildings[x][y] = None
                    self.map[x][y]["collision"] = False
                    self.examined_tile = None
                    self.hud.examined_tile = None
                if building is not None:
                    screen.blit(building.sprite, (
                        render_pos[0] + self.grass_tiles.get_width() / 2 + camera.scroll.x,
                        render_pos[1] - (building.sprite.get_height() - TILE_SIZE) + camera.scroll.y)
                                )
                    # have we clicked on this tile ? if yes we will highlight the building
                    if self.examined_tile is not None:
                        if (x == self.examined_tile[0]) and (y == self.examined_tile[1]):
                            # outline in white the object selected
                            mask = pygame.mask.from_surface(building.sprite).outline()
                            mask = [(x + render_pos[0] + self.grass_tiles.get_width() / 2 + camera.scroll.x,
                                     y + render_pos[1] - (building.sprite.get_height() - TILE_SIZE) + camera.scroll.y)
                                    for x, y in mask]
                            pygame.draw.polygon(screen, (255, 255, 255), mask, 3)

                            if type(building) != TownCenter:
                                temp_coor = self.grid_to_map(self.examined_tile[0], self.examined_tile[1])
                                iso_poly = temp_coor["iso_poly"]
                                iso_poly = [(x + self.grass_tiles.get_width() / 2 + camera.scroll.x, y + camera.scroll.y)
                                            for x, y in iso_poly]
                                self.highlight_tile(iso_poly, screen, "BLACK")
                            else:
                                building_pos = building.pos
                                temp_iso_poly = self.get_2x2_tiles(building_pos[0], building_pos[1] - 1, camera.scroll)
                                self.highlight_tile(temp_iso_poly, screen, "BLACK")

                # HERE WE DRAW THE UNITS ON THE MAP
                # we extract from the units list the building we want to display
                unit = self.units[x][y]
                if unit is not None and unit.current_health <= 0:
                    self.units[x][y] = None
                    self.map[x][y]["collision"] = False
                    self.examined_tile = None
                    self.hud.examined_tile = None
                if unit is not None:
                    screen.blit(unit.sprite, (
                        render_pos[0] + self.grass_tiles.get_width() / 2 + camera.scroll.x,
                        render_pos[1] - (unit.sprite.get_height() - TILE_SIZE) + camera.scroll.y)
                                )
                    if unit.searching_for_path:
                        # creates a flag to display where the unit is going
                        screen.blit(destination_flag, (
                            unit.dest["render_pos"][0] + self.grass_tiles.get_width() / 2 + camera.scroll.x,
                            unit.dest["render_pos"][1] - (destination_flag.get_height() - TILE_SIZE) + camera.scroll.y)
                                    )

                    # have we clicked on this tile ? if yes we will highlight the tile
                    if self.examined_tile is not None:
                        if (x == self.examined_tile[0]) and (y == self.examined_tile[1]):
                            # outline in white the object selected
                            temp_coor = self.grid_to_map(self.examined_tile[0], self.examined_tile[1])
                            iso_poly = temp_coor["iso_poly"]
                            iso_poly = [(x + self.grass_tiles.get_width() / 2 + camera.scroll.x, y + camera.scroll.y)
                                        for x, y in iso_poly]
                            self.highlight_tile(iso_poly, screen, "WHITE")

        # temp tile is a dictionary containing name + image + render pos + iso_poly + collision
        if self.temp_tile is not None:
            iso_poly = self.temp_tile["iso_poly"]
            iso_poly = [(x + self.grass_tiles.get_width() / 2 + camera.scroll.x, y + camera.scroll.y) for x, y in
                        iso_poly]
            render_pos = self.temp_tile["render_pos"]

            # if we cannot place our building on the tile because there's already smth, we display the tile in red, else, in green
            # For towncenter, we have to display a 2x2 green/Red case, else we only need to highlight a 1x1 case
            if self.temp_tile["name"] == "Town center":
                grid = self.renderpos_to_grid(render_pos[0], render_pos[1])
                temp_iso_poly = self.get_2x2_tiles(grid[0], grid[1] - 1, camera.scroll)
                #collision matrix : 0 if collision, else 1, we check the 4 cases of the town center
                if self.temp_tile["collision"] or self.collision_matrix[grid[1]][grid[0] + 1] == 0 or self.collision_matrix[grid[1] - 1][grid[0] + 1] == 0 or self.collision_matrix[grid[1] - 1][grid[0]] == 0:
                    self.highlight_tile(temp_iso_poly, screen, "RED")
                else:
                    self.highlight_tile(temp_iso_poly, screen, "GREEN")

            #for normal buildings (1x1)
            else:
                if self.temp_tile["collision"]:
                    self.highlight_tile(iso_poly, screen, "RED")
                else:
                    self.highlight_tile(iso_poly, screen, "GREEN")

            # display the potential building on the tile
            screen.blit(self.temp_tile["image"],
                        (  # we obviously have to reapply the offset + camera scroll
                            render_pos[0] + self.grass_tiles.get_width() / 2 + camera.scroll.x,
                            render_pos[1] - (self.temp_tile["image"].get_height() - TILE_SIZE) + camera.scroll.y
                        )
                        )

    def load_images(self):
        block = pygame.image.load(os.path.join(assets_path, "block.png")).convert_alpha()
        tree = pygame.image.load(os.path.join(assets_path, "tree_2_resized_2.png")).convert_alpha()
        rock = pygame.image.load(os.path.join(assets_path, "stone1.png")).convert_alpha()
        grass_tile = pygame.image.load(os.path.join(assets_path, "grass.png")).convert_alpha()
        grass_hd = pygame.image.load(os.path.join(assets_path, "12.png")).convert_alpha()
        gold = pygame.image.load(os.path.join(assets_path, "gold.png")).convert_alpha()
        town_center = pygame.image.load("Resources/assets/town_center.png").convert_alpha()
        house = pygame.image.load("Resources/assets/House_2.png").convert_alpha()
        farm = pygame.image.load("Resources/assets/farm.png").convert_alpha()
        villager = pygame.image.load("resources/assets/Villager.bmp").convert_alpha()
        images = {
            "Town center": town_center,
            "House": house,
            "Farm": farm,
            "tree": tree,
            "rock": rock,
            "block": block,
            "grass": grass_tile,
            "grass_hd": grass_hd,
            "gold": gold,
            "Villager": villager
        }
        return images

    # this function returns the isometric picture coordinates corresponding to a grid_tile
    def grid_to_map(self, grid_x, grid_y):
        rect = [
            (grid_x * TILE_SIZE, grid_y * TILE_SIZE),
            (grid_x * TILE_SIZE + TILE_SIZE, grid_y * TILE_SIZE),
            (grid_x * TILE_SIZE + TILE_SIZE, grid_y * TILE_SIZE + TILE_SIZE),
            (grid_x * TILE_SIZE, grid_y * TILE_SIZE + TILE_SIZE)
        ]
        # polygon
        iso_poly = [decarte_to_iso(x, y) for x, y in rect]
        minx = min([x for x, y in iso_poly])
        miny = min([y for x, y in iso_poly])
        r = random.randint(1, 100)
        perlin = 100 * noise.pnoise2(grid_x / self.perlin_scale, grid_y / self.perlin_scale)
        if (perlin >= 15) or (perlin <= -35):
            tile = "tree"
        else:
            if r <= 1:
                tile = "rock"
            elif r <= 2:
                tile = "tree"
            else:
                tile = ""
        # perlin = noise.
        out = {
            "grid": [grid_x, grid_y],
            "drect": rect,
            "iso_poly": iso_poly,
            "render_pos": [minx, miny],
            "tile": tile,
            "collision": False if tile == "" else True,
            "2x2_collision": False,
            "max_health": 10,
            "health": 10
        }
        return out

    # From the mouse coordinates, we find the corresponding tile of our map (=grid position).
    # Almost does the "opposite" work of grid_to_map
    # x and y : position of mouse
    def mouse_to_grid(self, mouse_x, mouse_y, scroll):
        # 1 : we remove the camera scroll and the offset (for x) to get the corresponding map position
        iso_x = mouse_x - scroll.x - self.grass_tiles.get_width() / 2
        iso_y = mouse_y - scroll.y
        # 2 : we remove the isometric transformation to find cartesian coordinates
        cart_x, cart_y = iso_to_decarte(iso_x, iso_y)
        # 3 : find the grid coordinates (we must get integers to make sense)
        grid_x = int(cart_x // TILE_SIZE)
        grid_y = int(cart_y // TILE_SIZE)
        return grid_x, grid_y

    def renderpos_to_grid(self, x, y):
        # 2 : we remove the isometric transformation to find cartesian coordinates
        cart_x, cart_y = iso_to_decarte(x, y)
        # 3 : find the grid coordinates (we must get integers to make sense)
        grid_x = int(cart_x // TILE_SIZE)
        grid_y = int(cart_y // TILE_SIZE)
        return grid_x + 1, grid_y

    def grid_to_renderpos(self, grid_x, grid_y):
        rect = [
            (grid_x * TILE_SIZE, grid_y * TILE_SIZE),
            (grid_x * TILE_SIZE + TILE_SIZE, grid_y * TILE_SIZE),
            (grid_x * TILE_SIZE + TILE_SIZE, grid_y * TILE_SIZE + TILE_SIZE),
            (grid_x * TILE_SIZE, grid_y * TILE_SIZE + TILE_SIZE)
        ]
        # polygon
        iso_poly = [decarte_to_iso(x, y) for x, y in rect]
        minx = min([x for x, y in iso_poly])
        miny = min([y for x, y in iso_poly])
        render_pos = [minx, miny]
        return render_pos

    # takes tile "matrice" coordinates, returns center of tile
    def get_tile_center(self, tile_x, tile_y, scroll):
        top_left_corner = (tile_x * TILE_SIZE, tile_y * TILE_SIZE)
        bottom_left_corner = (tile_x * TILE_SIZE + TILE_SIZE, tile_y * TILE_SIZE)
        top_right_corner = (tile_x * TILE_SIZE, tile_y * TILE_SIZE + TILE_SIZE)
        bottom_right_corner = (tile_x * TILE_SIZE + TILE_SIZE, tile_y * TILE_SIZE + TILE_SIZE)
        tile_center_x = tile_x + (TILE_SIZE / 2)
        tile_center_y = tile_y + (TILE_SIZE / 2)
        tile_center_x, tile_center_y = decarte_to_iso(tile_center_x, tile_center_y)
        tile_center_x = tile_center_x + scroll.x + (self.grass_tiles.get_width() * 2)
        # tile_center_x = tile_center_x + scroll.x
        tile_center_y = tile_center_y + scroll.y
        return tile_center_x, tile_center_y

    def get_2x2_tiles(self, bottom_left_tile_x, bottom_left_tile_y, scroll):

        top_left_corner = (bottom_left_tile_x * TILE_SIZE, bottom_left_tile_y * TILE_SIZE)
        bottom_left_corner = (bottom_left_tile_x * TILE_SIZE + TILE_SIZE * 2, bottom_left_tile_y * TILE_SIZE)
        bottom_right_corner = (bottom_left_tile_x * TILE_SIZE + TILE_SIZE * 2, bottom_left_tile_y * TILE_SIZE + TILE_SIZE * 2)
        top_right_corner = (bottom_left_tile_x * TILE_SIZE, bottom_left_tile_y * TILE_SIZE + TILE_SIZE * 2)

        rect = [top_left_corner, bottom_left_corner, bottom_right_corner, top_right_corner]

        # polygon
        iso_poly = [decarte_to_iso(x, y) for x, y in rect]
        iso_poly = [(x + self.grass_tiles.get_width() / 2 + scroll.x, y + scroll.y) for x, y in
                    iso_poly]

        return iso_poly

    # to check if we are able to place an object (collision)
    def can_place_tile(self, grid_pos):
        mouse_on_panel = False
        # we check if it is on the hud
        if self.hud.bottom_hud_rect.collidepoint(pygame.mouse.get_pos()):
            mouse_on_panel = True
        # we check it is not outside the map
        map_bounds = (0 <= grid_pos[0] <= self.grid_length_x) and (0 <= grid_pos[1] <= self.grid_length_y)
        # if we are in the map and not on a hud, we can place it
        if map_bounds and not mouse_on_panel:
            return True
        else:
            return False

    # matrix of 1 and 0, will be used for pathfinding
    # 1 : possible tile
    # 0 : there's already something : collision
    # because of the implementation of the pathfinding package, this matrix can't mirror the map grid and needs to be inverted
    def create_collision_matrix(self):
        # at first, we initialise our matrix with 1 : this means you can go everywhere
        collision_matrix = [[1 for x in range(self.grid_length_x)] for y in range(self.grid_length_y)]
        for x in range(self.grid_length_x):
            for y in range(self.grid_length_y):
                # we iterate through our tiles, if there's something, we put a 0 in our collision matrix
                if self.map[x][y]["collision"]:
                    collision_matrix[y][x] = 0
        return collision_matrix

    def highlight_tile(self, iso_poly, screen, color):
        if color == "WHITE":
            pygame.draw.polygon(screen, (255, 255, 255), iso_poly, 3)
        elif color == "BLACK":
            pygame.draw.polygon(screen, (0, 0, 0), iso_poly, 3)
        elif color == "BLUE":
            pygame.draw.polygon(screen, (0, 0, 255), iso_poly, 3)
        elif color == "GREEN":
            pygame.draw.polygon(screen, (0, 255, 0), iso_poly, 3)
        elif color == "RED":
            pygame.draw.polygon(screen, (255, 0, 0), iso_poly, 3)

    # here is the fonction that places the townhall randomly on the map
    def place_townhall(self):
        while not self.townhall_placed:
            place_x = random.randint(0, self.grid_length_x - 2)
            place_y = random.randint(1, self.grid_length_y - 1)

            self.place_x = place_x
            self.place_y = place_y

            new_building = TownCenter((place_x, place_y), self, playerOne)
            self.entities.append(new_building)
            self.buildings[place_x][place_y] = new_building

            self.townhall_placed = True

            self.map[place_x][place_y]["tile"] = "building"
            self.map[place_x][place_y]["collision"] = True
            self.map[place_x + 1][place_y]["tile"] = "building"
            self.map[place_x + 1][place_y]["collision"] = True
            self.map[place_x][place_y - 1]["tile"] = "building"
            self.map[place_x][place_y - 1]["collision"] = True
            self.map[place_x + 1][place_y - 1]["tile"] = "building"
            self.map[place_x + 1][place_y - 1]["collision"] = True
