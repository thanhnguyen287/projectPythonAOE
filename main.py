import pygame
import os
from game.game import Game as g
#from game.settings import path
#from .settings import WIDTH
#from .settings import HEIGHT


def main():
#path
    current_path = os.path.dirname(__file__) #current path of main.py
    resource_path = os.path.join(current_path, 'resources') #the resource folder
    common_path = os.path.join(resource_path, 'common')
    assets_path = os.path.join(resource_path, 'assets')

#intialize pygame
    pygame.init()
    pygame.mixer.init()
    clock = pygame.time.Clock()

#create the screen
#screen = pygame.display.set_mode((1920,1080))
  #  screen = pygame.display.set_mode((WIDTH,HEIGHT))
    screen = pygame.display.set_mode((1920,1070))




#title and Icon
    pygame.display.set_caption("Age of Empire: Homemade Edition")
    icon = pygame.image.load(os.path.join(common_path,'icon.png'))
    pygame.display.set_icon(icon)
    game = g(screen, clock)

#Exit game
    running = True
    playing = True
    while running:

        # Add start menu here

        while playing:



            # Start game loop
            game.run()



if __name__ == "__main__":
    main()

