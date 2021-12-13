import random
import noise
import pygame.mouse
from settings import *
from builds import Farm, Town_center, House
from player import playerOne
from New_ressources import *


class Map:
    def __init__(self, hud, entities, grid_length_x, grid_length_y, width, height):
        self.hud = hud
        self.entities = entities
        self.grid_length_x = grid_length_x
        self.grid_length_y = grid_length_y
        self.width = width
        self.height = height

        self.town_hall_placed = False

        # anything >1 or <-1, otherwise pnoise will return 0
        self.perlin_scale = grid_length_x / 2

        self.grass_tiles = pygame.Surface(
            (grid_length_x * TILE_SIZE * 2, grid_length_y * TILE_SIZE + 2 * TILE_SIZE)).convert_alpha()
        self.tiles = self.load_images()

        # lists of lists
        self.buildings = [[None for x in range(self.grid_length_x)] for y in range(self.grid_length_y)]

        self.map = self.create_map()

        # used when selecting a tile to build
        self.temp_tile = None

        # used when examinating elements of the map
        self.examined_tile = None

    def create_map(self):
        map = []

        for grid_x in range(self.grid_length_x):
            map.append([])
            for grid_y in range(self.grid_length_y):
                map_tile = self.grid_to_map(grid_x, grid_y)
                map[grid_x].append(map_tile)

                #here we define the collisions for the townhall that we placed randomly on the map
                #and we delete things on the tiles of the building
                if map[grid_x - 1][grid_y]["tile"] == "building":
                    map[grid_x][grid_y]["collision"] = True
                    map[grid_x][grid_y]["tile"] = ""
                    map[grid_x - 1][grid_y - 1]["collision"] = True
                    map[grid_x - 1][grid_y - 1]["tile"] = ""
                    map[grid_x][grid_y - 1]["collision"] = True
                    map[grid_x][grid_y - 1]["tile"] = ""

                render_pos = map_tile["render_pos"]

                # self.grass_tiles.getwidth()/2 : offset
                self.grass_tiles.blit(self.tiles["block"],
                                      (render_pos[0] + self.grass_tiles.get_width() / 2, render_pos[1]))

        return map

    def update(self, camera, screen):
        mouse_pos = pygame.mouse.get_pos()
        mouse_action = pygame.mouse.get_pressed()

        # we deselect the object examined when right-clicking
        if mouse_action[2]:
            self.examined_tile = None
            self.hud.examined_tile = None

        self.temp_tile = None
        # meaning : the player selected a building in the hud
        if self.hud.selected_tile is not None:
            grid_pos = self.mouse_to_grid(mouse_pos[0], mouse_pos[1], camera.scroll)

            # if we can't place the building on the tile, there's no need to do the following
            if self.can_place_tile(grid_pos):
                image = self.hud.selected_tile["image"].copy()
                # setting transparency to make sure player understands it's not built
                image.set_alpha(100)

                if grid_pos[0] < self.grid_length_x and grid_pos[1] < self.grid_length_y:
                    render_pos = self.map[grid_pos[0]][grid_pos[1]]["render_pos"]
                    iso_poly = self.map[grid_pos[0]][grid_pos[1]]["iso_poly"]
                    collision = self.map[grid_pos[0]][grid_pos[1]]["collision"]
                                  
                    self.temp_tile = {
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
                        new_building = Farm(render_pos, playerOne)
                        # to add it to the entities list on our map
                        self.entities.append(new_building)
                        # grid_pos 0 and grid_pos 1 means : grid_pos_x and grid_pos_y, not the specific tile near the origin
                        self.buildings[grid_pos[0]][grid_pos[1]] = new_building

                    elif self.hud.selected_tile["name"] == "Town center":
                        new_building = Town_center(render_pos, playerOne)
                        self.entities.append(new_building)
                        self.buildings[grid_pos[0]][grid_pos[1]] = new_building
                        # additional collision bc town center is 2x2 tile, not 1x1
                        self.map[grid_pos[0] + 1][grid_pos[1]]["collision"] = True
                        self.map[grid_pos[0]][grid_pos[1] - 1]["collision"] = True
                        self.map[grid_pos[0] + 1][grid_pos[1] - 1]["collision"] = True
                        self.map[grid_pos[0]][grid_pos[1]]["2x2_collision"] = True


                    elif self.hud.selected_tile["name"] == "House":
                        new_building = House(render_pos, playerOne)
                        self.entities.append(new_building)
                        self.buildings[grid_pos[0]][grid_pos[1]] = new_building

                    self.map[grid_pos[0]][grid_pos[1]]["collision"] = True

                    self.hud.selected_tile = None

        # the player hasn't selected something to build, he will interact with what's on the map
        else:
            grid_pos = self.mouse_to_grid(mouse_pos[0], mouse_pos[1], camera.scroll)

            # if on the map and left click and the tile isn't empty
            if self.can_place_tile(grid_pos):
                if grid_pos[0] < self.grid_length_x and grid_pos[1] < self.grid_length_y:
                    building = self.buildings[grid_pos[0]][grid_pos[1]]

                    if mouse_action[0]:
                        self.examined_tile = grid_pos
                        if building is not None:
                            self.hud.examined_tile = building
                else:
                    pass

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

                # here we delete the ressource we left click on
                if (self.examined_tile is not None) and (tile == "tree" or tile == "rock"):
                    if x == self.examined_tile[0] and y == self.examined_tile[1]:
                        self.map[x][y]["health"] -= 0.2
                        if self.map[x][y]["health"] <= 0:
                            self.map[x][y]["tile"] = ""  # the tile becomes empty since we destroy  the tree/rock
                            self.map[x][y]["collision"] = False
                            if tile == "tree":
                                playerOne.update_resource(0, 10)  # the player gains +10 wood if the tile was a tree
                            elif tile == "rock":
                                playerOne.update_resource(3, 10)  # the player gains +10 stone if the tile was a rock
                        self.examined_tile = None

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

                            # display examined tile in white
                            # temp_coor = self.grid_to_map(self.examined_tile[0], self.examined_tile[1])
                            # iso_poly = temp_coor["iso_poly"]
                            # iso_poly = [(x + self.grass_tiles.get_width() / 2 + camera.scroll.x, y + camera.scroll.y) for x, y in iso_poly]
                            # pygame.draw.polygon(screen, (255, 255, 255), iso_poly, 3)


        # display the potential building on the tile
        if self.temp_tile is not None:
            iso_poly = self.temp_tile["iso_poly"]
            iso_poly = [(x + self.grass_tiles.get_width() / 2 + camera.scroll.x, y + camera.scroll.y) for x, y in
                        iso_poly]

            # if we cannot place our building on the tile because there's already smth, we display the tile in red, else, in green
            if self.temp_tile["collision"]:
                pygame.draw.polygon(screen, (255, 0, 0), iso_poly, 3)
            else:
                pygame.draw.polygon(screen, (0, 255, 0), iso_poly, 3)

            render_pos = self.temp_tile["render_pos"]
            screen.blit(self.temp_tile["image"],
                        (  # we obviously have to reapply the offset + camera scroll
                            render_pos[0] + self.grass_tiles.get_width() / 2 + camera.scroll.x,
                            render_pos[1] - (self.temp_tile["image"].get_height() - TILE_SIZE) + camera.scroll.y
                        )
                        )

    def load_images(self):

        block = pygame.image.load(os.path.join(assets_path, "block.png")).convert_alpha()
        tree = pygame.image.load(os.path.join(assets_path, "tree_2_resized_2.png")).convert_alpha()
        rock = pygame.image.load(os.path.join(assets_path, "rock.png")).convert_alpha()
        grass_tile = pygame.image.load(os.path.join(assets_path, "20001_02.png")).convert_alpha()

        town_center = pygame.image.load("Resources/assets/town_center.png").convert_alpha()
        house = pygame.image.load("Resources/assets/House_2.png").convert_alpha()
        farm = pygame.image.load("Resources/assets/farm.png").convert_alpha()

        images = {
            "Town center": town_center,
            "House": house,
            "Farm": farm,
            "tree": tree,
            "rock": rock,
            "block": block,
            "grass_tile": grass_tile
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
        iso_poly = [self.decarte_to_iso(x, y) for x, y in rect]

        minx = min([x for x, y in iso_poly])
        miny = min([y for x, y in iso_poly])

        r = random.randint(1, 100)
        perlin = 100 * noise.pnoise2(grid_x / self.perlin_scale, grid_y / self.perlin_scale)

        place_town_hall = random.random()

        if (perlin >= 15) or (perlin <= -35):
            tile = "tree"

        else:
            if r <= 1:
                tile = "rock"
            elif r <= 2:
                tile = "tree"

            #here we place randomly the townhall on the map
            elif place_town_hall <= 0.003 and not self.town_hall_placed:
                new_building = Town_center((minx, miny), playerOne)
                self.entities.append(new_building)
                self.buildings[grid_x][grid_y] = new_building

                self.town_hall_placed = True

                tile = "building"
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

    def decarte_to_iso(self, x, y):
        iso_x = x - y
        iso_y = (x + y) / 2
        return iso_x, iso_y

    # From the mouse coordinates, we find the corresponding tile of our map (=grid position).
    # Almost does the "opposite" work of grid_to_map
    # x and y : position of mouse
    def mouse_to_grid(self, mouse_x, mouse_y, scroll):

        # 1 : we remove the camera scroll and the offset (for x) to get the corresponding map position
        map_x = mouse_x - scroll.x - self.grass_tiles.get_width() / 2
        map_y = mouse_y - scroll.y

        # 2 : we remove the isometric transformation to find cartesian coordinates
        # opposite of decarte_to_iso function
        cart_y = (2 * map_y - map_x) / 2
        cart_x = cart_y + map_x

        # 3 : find the grid coordinates (we must get integers to make sense)
        grid_x = int(cart_x // TILE_SIZE)
        grid_y = int(cart_y // TILE_SIZE)

        return grid_x, grid_y

    # to check if we are able to place an object (collision)
    def can_place_tile(self, grid_pos):
        mouse_on_panel = False

        # we check if it is on the hud
        for rect in [self.hud.build_rect, self.hud.select_rect]:
            if rect.collidepoint(pygame.mouse.get_pos()):
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