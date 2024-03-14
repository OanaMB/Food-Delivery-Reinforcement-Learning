import random
import gym
import sys
from gym import spaces
import numpy as np
import pygame
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
    ' ': pygame.image.load('images/road.png'),
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
    'P': pygame.image.load('images/car_2.png'),
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
    'P': tile_images['P'],
    'F': tile_images['F'],
}

class DoubleDeliveryEnv(gym.Env):
    
    """
     Delivery locations:
    - 0: R(estaurant)
    - 1: A(block 1)
    - 2: B(block 2)
    - 3: C(block 3)
    - 4: in the delivey car1/bike/motorbike
    - 5: in the delivery car2

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
     -2 pentru fiecare pas dacă nu este declanșată o altă recompensă.
    +100 pentru livrarea comenzii.
    -10 pentru efectuarea acțiunilor "pickup" și "drop-off" în mod ilegal (fără a avea mancare la bord).
    -5 daca intra in santier
    -10 daca depaseste timpul (timer-ul expira)
    -15 coliziune

    state space is represented by:
        (taxi_row, taxi_col, passenger_location, destination)
        
    """
    metadata = {"render_modes": ["human"], "render_fps": 3}
    
    def __init__(self, w = 1000, h = 790):
        super(DoubleDeliveryEnv, self).__init__()
        
        # initialize the map 
        self.desc, self.grid_size = generate_random_map(MAP)

        self.max_row = self.grid_size - 1
        self.max_column = self.grid_size - 1
        
        #initialize the game
        self.action_space = spaces.Discrete(36)
        self.observation_space = spaces.Discrete(self.grid_size * self.grid_size * self.grid_size * self.grid_size * 6 * 3)
        
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
        self.current_row1, self.current_col1 = coordinates[0]
        self.current_row2, self.current_col2 = coordinates[1]
        
        #initialize number of deliveries and delivery position
        self.no_delivery = 0
        self.delivery_idx = 0
        
        # AICI TREBUIE MODIFICATA FORMAREA ARRAY-ului
        self.restaurant_pos = self.search_for_coordinates_blocks(self.desc,b'R')
        coord_A = self.search_for_coordinates_blocks(self.desc,b'A')
        coord_B = self.search_for_coordinates_blocks(self.desc,b'B')
        coord_C = self.search_for_coordinates_blocks(self.desc,b'C')
        self.locs = [coord_A, coord_B, coord_C]

        # un array de index-uri ca sa fie random
        self.destination = random.randint(0, 2)
        
        # the starting state should be random
        self.initial_state = self.encode(self.current_row1, self.current_col1, self.current_row2, self.current_col2, self.delivery_idx, self.destination)
                                                    
        return self.initial_state
        
   
    def apply_action_one(self, row, col, deliv_idx: int, dest_idx: int, action, taxi_id: int):
        
        new_row, new_col, new_deliv_idx = row, col, deliv_idx
        reward = -2  # default reward when there is no pickup/dropoff
        done = False    
        delivery_loc = (row, col)
       
        if (deliv_idx >= 4) and ((4 + taxi_id) != deliv_idx):
            # passenger already onboarded in someone else's car
            # so the overall reward should be less -ve
            reward = -1
            return new_row, new_col, new_deliv_idx, done, reward
            
        
        if action == 0: 
            if  (self.desc[row + 2, 2 * col + 1] != b"-" and 
                self.desc[row + 2, 2 * col + 1] != b"|"):
                if self.desc[row + 1 + 1, 2 * col + 1] != b"X":
                    new_row = min(row + 1, self.max_row)
                elif self.desc[row + 1 + 1, 2 * col + 1] == b"X":
                    new_row = min(row + 1, self.max_row)
                    reward = -10

        
        if action == 1:
            if  (self.desc[row, 2 * col + 1] != b"-" and 
                 self.desc[row, 2 * col + 1] != b"|"):
                if self.desc[row + 1 - 1, 2 * col + 1] != b"X":
                    new_row = max(row - 1, 0)
                elif self.desc[row + 1 - 1, 2 * col + 1] == b"X":
                    new_row = max(row - 1, 0)
                    reward = -10
        
        if action == 2:
            if self.desc[row + 1, 2 * col + 2] == b":":
                if self.desc[row + 1, 2 * (col + 1) + 1] != b"X":
                    new_col = min(col + 1, self.max_column)
                elif self.desc[row + 1, 2 * (col + 1)] == b"X":
                    new_col = min(col + 1, self.max_column)
                    reward = -10
            elif self.desc[row + 1, 2 * col + 2] == b"|": 
                new_col = col
                
                
        if action == 3:
            if self.desc[row + 1, 2 * col] == b":":
                if self.desc[row + 1, 2 * col - 1] != b"X":
                    new_col = max(col - 1, 0)
                elif self.desc[row + 1, 2 * col - 1] == b"X":
                    new_col = max(col - 1, 0)
                    reward = -10  
            elif self.desc[row + 1, 2 * col] == b"|": 
                new_col = col
                    
        if action == 4:  # pickup
            if (self.delivery_idx == 0 and delivery_loc == self.restaurant_pos):
                new_deliv_idx = 4 + taxi_id   
                self.delivery_idx = 4 + taxi_id   
                
            else:  # delivery not at location
                reward = -10    
                
                
        if action == 5:  # dropoff
            if (delivery_loc == self.locs[self.destination]) and deliv_idx == 4 + taxi_id:
                new_deliv_idx = dest_idx + 1
                self.delivery_idx = dest_idx + 1
                reward = 100
                done = True
                           
            else:  # dropoff at wrong location
                reward = -10   
        
        return new_row, new_col, new_deliv_idx, done, reward
    
    
    def step(self,actions):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
        
        action_1, action_2 = self.decode_action(actions)
        loc_1 = (self.current_row1,self.current_col1)
        loc_2 = (self.current_row2,self.current_col2)
        
        current_row1, current_col1, new_delivery_idx1, done_1, reward_1 = self.apply_action_one(
                                self.current_row1, self.current_col1, self.delivery_idx, self.destination, action_1, taxi_id=0)

        current_row2, current_col2, new_delivery_idx2, done_2, reward_2 = self.apply_action_one(
                                self.current_row2, self.current_col2, self.delivery_idx, self.destination, action_2, taxi_id=1)
        new_loc_1 = (current_row1,current_col1)
        new_loc_2 = (current_row2,current_col2)
        
        if (new_loc_1 == new_loc_2):
            # collision!
            reward_1 = reward_2 = -15
            new_loc_1, new_loc_2 = loc_1, loc_2
            new_deliv_idx = self.delivery_idx
            self.delivery_idx = new_deliv_idx
        elif (loc_1 == loc_2):
            # spawned at collision
            # Technically this should not encountered. So if you detect -0.5 rewards, something's off
            done_1 = True
            reward_1 = -0.5
            reward_2 = 0
            new_deliv_idx = self.delivery_idx
            self.delivery_idx = new_deliv_idx
        else:
            # Resolving pass_idx
            new_deliv_idx = None
            # after both the actions, the passenger location is unchanged
            if new_delivery_idx1 == new_delivery_idx2 == self.delivery_idx:
                new_deliv_idx = new_delivery_idx1
                self.delivery_idx = new_deliv_idx  
            # Taxi 1 pickup and passenger onboarded
            elif (action_1 == 4) and (new_delivery_idx1 == 4):
                new_deliv_idx= new_delivery_idx1
                self.delivery_idx = new_deliv_idx         
            # Taxi 2 pickup and passenger onboarded
            elif (action_2 == 4) and (new_delivery_idx2 == 5):
                new_deliv_idx = new_delivery_idx2
                self.delivery_idx = new_deliv_idx         
            # Taxi 1 finished
            elif done_1:
                new_deliv_idx = new_delivery_idx1
                self.delivery_idx = new_deliv_idx         
            # Taxi 2 finished
            elif done_2:
                new_deliv_idx = new_delivery_idx2
                self.delivery_idx = new_deliv_idx        
            # passenger was onboarded in taxi 1 and it took dropoff action
            elif (self.delivery_idx == 4) and (action_1 == 5):
                new_deliv_idx = new_delivery_idx1
                self.delivery_idx = new_deliv_idx         
            # passenger was onboarded in taxi 2 and it took dropoff action
            elif  (self.delivery_idx == 5) and (action_2 == 5):
                new_deliv_idx = new_delivery_idx2
                self.delivery_idx = new_deliv_idx         
            else:
                raise Exception(f"unksnown state with pass_idx {loc_1} {loc_2} {self.delivery_idx} {done_1} {done_2} {action_1}:{new_delivery_idx1}, {action_2}:{new_delivery_idx2}")
        
        
        next_state = self.encode(current_row1, current_col1, current_row2, current_col2, new_deliv_idx, self.destination)     
        reward = reward_1 + reward_2
        done = done_1 or done_2
        self.current_row1 = current_row1
        self.current_col1 = current_col1
        self.current_row2 = current_row2
        self.current_col2 = current_col2
        info = {}
        return next_state, reward, done, info 
          

    # the encoding of the new state
    # the numbers will be replaced with the variable number of rows ad columns
    def encode(self, taxi1_row, taxi1_col,taxi2_row, taxi2_col, del_loc, dest_idx):
        return ((((taxi1_row * self.grid_size + taxi1_col) * self.grid_size + taxi2_row) * self.grid_size + taxi2_col) * 6 + del_loc) * 3 + dest_idx
   
    
    def encode_action(self, action_1, action_2):
        return action_1 * 6 + action_2
    
    
    def decode_action(self, action):
        action_2 = action % 6
        action = action // 6
        action_1 = action % 6
        assert 0 <= action_1 < 6
        return (action_1, action_2)
        
    def place_agent_starting_point(self,map):
    # Find a valid location for the starting point (" ")
        valid_coordinates = []
        for row_idx in range(1,len(map) - 1,1):
            for col_idx in range(1,len(map[row_idx]) - 1,1):
                if map[row_idx][col_idx] == b' ':
                    valid_coordinates.append((row_idx - 1, col_idx // 2))
        return random.sample(valid_coordinates,2)
    
    
    def search_for_coordinates_blocks(self,map,character):
        for row_idx in range(1,len(map) - 1,1):
            for col_idx in range(1,len(map[row_idx]) - 1,1):
                if map[row_idx][col_idx] == character:
                    return (row_idx - 1,col_idx // 2)


    def render_mode(self,actions,episode,total_rewards):
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()  
                
        action_1, action_2 = self.decode_action(actions)
                    
        self.display.fill((132, 126, 135))  # Clear the display
        # Display loading screen
        self.loading_screen_image = pygame.image.load('images/fundal.png')  # Replace with your image path
        self.loading_screen_image = pygame.transform.scale(self.loading_screen_image, (self.w, self.h))

        self.display.blit(self.loading_screen_image, (0, 0))

        # Display text
        rect_width, rect_height = 250, 100
        rect_x = (self.w - rect_width) // 2  # Center horizontally
        rect_y = self.h - rect_height - 20      # Bottom of the screen
        rect = pygame.Rect(rect_x, rect_y, rect_width, rect_height)
        pygame.draw.rect(self.display, (132, 126, 135), rect)
        pygame.draw.rect(self.display, (0,0,0), rect, 3)
        
        text1 = self.font.render(f"Destination: {self.destination}", True, (0, 0, 0))
        text2 = self.font.render(f"Position_car_1: {(self.current_row1, self.current_col1)}", True, (0, 0, 0))
        text5 = self.font.render(f"Position_car_2: {(self.current_row2, self.current_col2)}", True, (0, 0, 0))

        text_rect1 = text1.get_rect(center=(rect.centerx, rect.centery - 30))
        text_rect2 = text2.get_rect(center=(rect.centerx, rect.centery))
        text_rect5 = text5.get_rect(center=(rect.centerx, rect.centery + 30))
        

        # Blit the text onto the screen
        self.display.blit(text1, text_rect1)
        self.display.blit(text2, text_rect2)
        self.display.blit(text5, text_rect5)
        
        
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
        x_s_pos = (self.w - len(self.desc[self.current_row1]) * TILE_SIZE) // 2 + (2 * self.current_col1 + 1) * TILE_SIZE
        y_s_pos = (self.h - len(self.desc) * TILE_SIZE) // 2 + (self.current_row1 + 1) * TILE_SIZE  
        
        # Calculate the position to center the 'P' image on its corresponding tile
        x_p_pos = (self.w - len(self.desc[self.current_row2]) * TILE_SIZE) // 2 + (2 * self.current_col2 + 1) * TILE_SIZE
        y_p_pos = (self.h - len(self.desc) * TILE_SIZE) // 2 + (self.current_row2 + 1) * TILE_SIZE  
        
        tile_image1 = image_map['S']
        if(self.delivery_idx == 4):
            tile_image1 = image_map['F']   
            
        tile_image2 = image_map['P']
        if(self.delivery_idx == 5):
            tile_image2 = image_map['F']
                
        if(action_1 == 0 or action_1 == 1):
            tile_image1 = pygame.transform.rotate(tile_image1, 90)
            self.display.blit(tile_image1, (x_s_pos, y_s_pos))
        else:          
            self.display.blit(tile_image1, (x_s_pos, y_s_pos))            
        
        if(action_2 == 0 or action_2 == 1):
            tile_image2 = pygame.transform.rotate(tile_image2, 90)
            self.display.blit(tile_image2, (x_p_pos, y_p_pos))
        else:          
            self.display.blit(tile_image2, (x_p_pos, y_p_pos))
        pygame.display.update()
        self.clock.tick(3)
                
     
    def close(self):
            pygame.display.quit()
            pygame.quit()
            exit()
    
 