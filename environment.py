import random
import gym
import sys
from gym import spaces
import numpy as np
import pygame
import time
from sys import exit
from random_map import generate_random_map

pygame.init()
pygame.font.init()

MAP = {
    "5x5":["+---------+",
    "| : : : : |",
    "| : : : : |",
    "| : : : : |",
    "| : : : : |",
    "| : : : : |",
    "+---------+"],
    "6x6":
   ["+-----------+",
    "| : : : : : |",
    "| : : : : : |",
    "| : : : : : |",
    "| : : : : : |",
    "| : : : : : |",
    "| : : : : : |",
    "+-----------+"],
    "7x7":
   ["+-------------+",
    "| : : : : : : |",
    "| : : : : : : |",
    "| : : : : : : |",
    "| : : : : : : |",
    "| : : : : : : |",
    "| : : : : : : |",
    "| : : : : : : |",
    "+-------------+"]
    
}

TILE_SIZE = 60
tile_images = {
    ' ': pygame.image.load("images/road.png"),
    '+': pygame.image.load('images/colt.png'),
    '-': pygame.image.load('images/wall.png'),
    '|': pygame.image.load('images/wall.png'),   
    'R': pygame.image.load('images/restaurant.png'),
    'A': pygame.image.load('images/cartier_A.png'),
    'B': pygame.image.load('images/cartier_B.png'),
    'C': pygame.image.load('images/cartier_C.png'),
    'X': pygame.image.load('images/stop.png'),
    ':': pygame.image.load('images/wall_passing.png'), 
    'S': pygame.image.load('images/car_1.png'),
    'F': pygame.image.load('images/car_loaded.png')
}

# Map characters to images
image_map = {
    ' ': tile_images[' '],
    '+': tile_images['+'],
    '-': tile_images['-'],
    '|': tile_images['|'],   
    'R': tile_images['R'],
    'A': tile_images['A'],
    'B': tile_images['B'],
    'C': tile_images['C'],
    'X': tile_images['X'],
    ':': tile_images[':'], 
    'S': tile_images['S'],
    'F': tile_images['F'],
}

class DeliveryEnv(gym.Env):
    
    """
     Delivery locations:
    - 0: R(estaurant)
    - 1: A(block 1)
    - 2: B(block 2)
    - 3: C(block 3)
    - 4: in the delivey car/bike/motorbike

    Destinations:
    - 0: A(block 1)
    - 1: B(block 2)
    - 2: C(block 3)

    Actions:
    There are 6 discrete deterministic actions:
    - 0: move south/down
    - 1: move north/up
    - 2: move east/right
    - 3: move west/left
    - 4: pickup delivey
    - 5: drop off delivery
    
    
    Rewards:
     -1 pentru fiecare pas dacă nu este declanșată o altă recompensă.
    +20 pentru livrarea comenzii.
    -10 pentru efectuarea acțiunilor "pickup" și "drop-off" în mod ilegal (fără a avea mancare la bord).
    -5 daca intra in santier
    -10 daca depaseste timpul (timer-ul expira)

    state space is represented by:
        (taxi_row, taxi_col, passenger_location, destination)
       
    """
    metadata = {"render_modes": ["human"], "render_fps": 3}
    
    def __init__(self, w = 1000, h = 790):
        super(DeliveryEnv, self).__init__()
        
        # initialize the map 
        self.desc, self.grid_size = generate_random_map(MAP)

        self.max_row = self.grid_size - 1
        self.max_column = self.grid_size - 1
        
        #initialize the game
        self.action_space = spaces.Discrete(6)
        self.observation_space = spaces.Discrete(self.grid_size * self.grid_size * 5 * 3)
        
        self.w = w
        self.h = h
        # init display
        self.display = pygame.display.set_mode((self.w, self.h))
        pygame.display.set_caption('Pizzeria Food Delivery')
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        
            
        loading_font = pygame.font.Font(None, 40)
        loading_text = loading_font.render("Loading...", True, (0, 0, 0))
        text_rect = loading_text.get_rect(center=(self.w // 2, self.h // 2))
        
        self.loading_screen_image = pygame.image.load('images/fundal.png')  # Replace with your image path
        self.loading_screen_image = pygame.transform.scale(self.loading_screen_image, (self.w, self.h))

        # Display loading screen
        self.display.blit(self.loading_screen_image, (0, 0))
        self.display.blit(loading_text, text_rect)
        pygame.display.flip()
        
        self.reset()
        
        
    def reset(self):
        # initialize the map with a valid random starting point
        
        coordinates = self.place_agent_starting_point(self.desc)
        self.current_row, self.current_col = coordinates
        
        #initialize number of deliveries and delivery position
        self.no_delivery = 0
        self.delivery_idx = 0
        
        # AICI TREBUIE MODIFICATA FORMAREA ARRAY-ului
        self.restaurant_pos = self.search_for_coordinates_blocks(self.desc,b'R')
        coord_A = self.search_for_coordinates_blocks(self.desc,b'A')
        coord_B = self.search_for_coordinates_blocks(self.desc,b'B')
        coord_C = self.search_for_coordinates_blocks(self.desc,b'C')
        self.locs = [coord_A, coord_B, coord_C]
       
        self.destination = random.randint(0, 2)
        
        self.time_limit_seconds = 15
        self.start_time = pygame.time.get_ticks()  # Record the start time
        self.remaining_time = 15
        
        # the starting state should be random
        self.initial_state = self.encode(self.current_row, self.current_col, self.delivery_idx, self.destination)
                                                    
        return self.initial_state
        
   
    def step(self, action):
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
        
        new_row, new_col, new_deliv_idx = self.current_row, self.current_col, self.delivery_idx
        reward = -1  # default reward when there is no pickup/dropoff
        done = False    
        delivery_loc = (self.current_row, self.current_col)
        destination = self.destination
        
        if action == 0: 
            if  (self.desc[self.current_row + 2, 2 * self.current_col + 1] != b"-" and 
                self.desc[self.current_row + 2, 2 * self.current_col + 1] != b"|"):
                if self.desc[self.current_row + 1 + 1, 2 * self.current_col + 1] != b"X":
                    new_row = min(self.current_row + 1, self.max_row)
                elif self.desc[self.current_row + 1 + 1, 2 * self.current_col + 1] == b"X":
                    new_row = min(self.current_row + 1, self.max_row)
                    reward = -5
                    
        if action == 1:
            if  (self.desc[self.current_row, 2 * self.current_col + 1] != b"-" and 
                 self.desc[self.current_row, 2 * self.current_col + 1] != b"|"):
                if self.desc[self.current_row + 1 - 1, 2 * self.current_col + 1] != b"X":
                    new_row = max(self.current_row - 1, 0)
                elif self.desc[self.current_row + 1 - 1, 2 * self.current_col + 1] == b"X":
                    new_row = max(self.current_row - 1, 0)
                    reward = -5
                   
        if action == 2:
            if self.desc[self.current_row + 1, 2 * self.current_col + 2] == b":":
                if self.desc[self.current_row + 1, 2 * (self.current_col + 1) + 1] != b"X":
                    new_col = min(self.current_col + 1, self.max_column)
                elif self.desc[self.current_row + 1, 2 * (self.current_col + 1)] == b"X":
                    new_col = min(self.current_col + 1, self.max_column)
                    reward = -5
            elif self.desc[self.current_row + 1, 2 * self.current_col + 2] == b"|": 
                new_col = self.current_col
                
                
        if action == 3:
            if self.desc[self.current_row + 1, 2 * self.current_col] == b":":
                if self.desc[self.current_row + 1, 2 * self.current_col - 1] != b"X":
                    new_col = max(self.current_col - 1, 0)
                elif self.desc[self.current_row + 1, 2 * self.current_col - 1] == b"X":
                    new_col = max(self.current_col - 1, 0)
                    reward = -5 
            elif self.desc[self.current_row + 1, 2 * self.current_col] == b"|": 
                new_col = self.current_col
                    
        if action == 4:  # pickup
            if (self.delivery_idx == 0 and delivery_loc == self.restaurant_pos):
                new_deliv_idx = 4
                self.delivery_idx = 4   
            else:  # delivery not at location
                reward = -10    
                
                
        if action == 5:  # dropoff
            if (delivery_loc == self.locs[self.destination]) and self.delivery_idx == 4:
                new_deliv_idx = self.destination + 1
                self.no_delivery += 1
                reward = 20
            
                if (self.no_delivery == 3):
                    done = True
                else:
                    self.destination = random.randint(0, 2)
                    self.delivery_idx = 0
                           
            else:  # dropoff at wrong location
                reward = -10   
        
        # Calculate elapsed time
        elapsed_time = (pygame.time.get_ticks() - self.start_time) / 1000
        self.remaining_time = self.time_limit_seconds - elapsed_time

        if self.remaining_time <= 0:
            reward -= 10  # Deduct points when timer runs out
            
        next_state = self.encode(new_row, new_col, new_deliv_idx, destination)     
        self.current_row = new_row
        self.current_col = new_col
        info = {}
        return next_state, reward, done, info       
          

    # the encoding of the new state
    # the numbers will be replaced with the variable number of rows ad columns
    def encode(self, taxi_row, taxi_col, del_loc, dest_idx):
        return ((taxi_row * self.grid_size + taxi_col) * 5 + del_loc) * 3 + dest_idx
   
        
        
    def place_agent_starting_point(self,map):
    # Find a valid location for the starting point (" ")
        valid_coordinates = []
        for row_idx in range(1,len(map) - 1,1):
            for col_idx in range(1,len(map[row_idx]) - 1,1):
                if map[row_idx][col_idx] == b' ':
                    valid_coordinates.append((row_idx - 1, col_idx // 2))
        return random.choice(valid_coordinates)
    
    
    def search_for_coordinates_blocks(self,map,character):
        for row_idx in range(1,len(map) - 1,1):
            for col_idx in range(1,len(map[row_idx]) - 1,1):
                if map[row_idx][col_idx] == character:
                    return (row_idx - 1,col_idx // 2)
    
    def render_mode(self,action,episode,total_rewards):
          
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()  
                    
        self.display.fill((132, 126, 135))  # Clear the display
        # Display loading screen
        self.loading_screen_image = pygame.image.load('images/fundal.png')  # Replace with your image path
        self.loading_screen_image = pygame.transform.scale(self.loading_screen_image, (self.w, self.h))

        self.display.blit(self.loading_screen_image, (0, 0))

        # Display text
        rect_width, rect_height = 200, 100
        rect_x = (self.w - rect_width) // 2  # Center horizontally
        rect_y = self.h - rect_height - 20      # Bottom of the screen
        rect = pygame.Rect(rect_x, rect_y, rect_width, rect_height)
        pygame.draw.rect(self.display, (132, 126, 135), rect)
        pygame.draw.rect(self.display, (0,0,0), rect, 3)
        
        text1 = self.font.render(f"Destination: {self.destination}", True, (0, 0, 0))
        text2 = self.font.render(f"Position: {(self.current_row, self.current_col)}", True, (0, 0, 0))

        text_rect1 = text1.get_rect(center=(rect.centerx, rect.centery - 30))
        text_rect2 = text2.get_rect(center=(rect.centerx, rect.centery + 30))

        # Blit the text onto the screen
        self.display.blit(text1, text_rect1)
        self.display.blit(text2, text_rect2)
        
        
        # Display text
        rect_width_2, rect_height_2 = 200, 70
        rect_x_2 = (self.w - rect_width_2) // 2  # Center horizontally
        rect_y_2 = 10      # Top of the screen
        rect_2 = pygame.Rect(rect_x_2, rect_y_2, rect_width_2, rect_height_2)
        pygame.draw.rect(self.display, (132, 126, 135), rect_2)
        pygame.draw.rect(self.display, (0,0,0), rect_2, 3)
        
        text3 = self.font.render(f"Episode: {episode}", True, (0, 0, 0))
        text4 = self.font.render(f"Score: {total_rewards}", True, (0, 0, 0))

        text_rect3 = text3.get_rect(center=(rect.centerx, rect_2.top + 20))
        text_rect4 = text4.get_rect(center=(rect.centerx, rect_2.top + 50))

        # Blit the text onto the screen
        self.display.blit(text3, text_rect3)
        self.display.blit(text4, text_rect4)
        
        rect_width_3, rect_height_3 = 200, 70
        rect_x_3 = 20   # Center horizontally
        rect_y_3 = 10      # Top of the screen
        rect_3 = pygame.Rect(rect_x_3, rect_y_3, rect_width_3, rect_height_3)
        pygame.draw.rect(self.display, (132, 126, 135), rect_3)
        pygame.draw.rect(self.display, (0,0,0), rect_3, 3)
        
        timer_text = f"Time left: {self.remaining_time:.1f}"
        if (self.remaining_time > 0):
            timer_surface = self.font.render(timer_text, True, (0, 255, 0))
        else:
            timer_surface = self.font.render(timer_text, True, (255, 0, 0))
            
                 
        timer_rect = timer_surface.get_rect()
        timer_rect.topleft = (30, 30)  # Adjust position
        self.display.blit(timer_surface, timer_rect)
        
                
        # Display tiles 
        for row in range(0,len(self.desc),1):
            for col in range(0,len(self.desc[row]),1):
                tile_char = self.desc[row, col]
                tile_char = tile_char.decode('utf-8')
                tile_image = image_map[tile_char]
                
                #calculate positions so that it is centered
                x_pos = (self.w - len(self.desc[row]) * TILE_SIZE) // 2 + col * TILE_SIZE
                y_pos = (self.h - len(self.desc) * TILE_SIZE) // 2 + row * TILE_SIZE
                
                if self.desc[row, col] == b'|':  # Rotate vertical walls
                    tile_image = pygame.transform.rotate(tile_image, 90)
                                
                self.display.blit(tile_image, (x_pos, y_pos)) 
                
        # Calculate the position to center the 'S' image on its corresponding tile
        x_s_pos = (self.w - len(self.desc[self.current_row]) * TILE_SIZE) // 2 + (2 * self.current_col + 1) * TILE_SIZE
        y_s_pos = (self.h - len(self.desc) * TILE_SIZE) // 2 + (self.current_row + 1) * TILE_SIZE
        
        tile_image = image_map['S']
        if(self.delivery_idx == 4):
            tile_image = image_map['F']
        
        
        if(action == 0 or action == 1):
            tile_image = pygame.transform.rotate(tile_image, 90)
            self.display.blit(tile_image, (x_s_pos, y_s_pos))
        else:          
            self.display.blit(tile_image, (x_s_pos, y_s_pos))    
        
        pygame.display.flip()
        self.clock.tick(3)
                           
    
    def close(self):
            pygame.display.quit()
            pygame.quit()
            exit()
    
 