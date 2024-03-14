import numpy as np
import random
import pygame
from sys import exit

from environment import DeliveryEnv
from multi_environment import DoubleDeliveryEnv


# Initialize pygame
pygame.init()

width, height = 800, 800
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption('Game Mode Selection')



class Button:
    def __init__(self, x, y, width, height, color, text, text_color, action):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        self.text = text
        self.text_color = text_color
        self.action = action
    
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        pygame.draw.rect(screen, (0,0,0), self.rect, 3)
        font = pygame.font.Font("slkscr.ttf", 32)
        text_surface = font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
    
    def check_collision(self, point):
        return self.rect.collidepoint(point)


# Create buttons
button1 = Button(250, 300, 250, 50, (132, 126, 135), "Simple Mode", (0,0,0), 0)
button2 = Button(250, 400, 250, 50, (132, 126, 135), "Double Mode", (0,0,0), 1)
buttons = [button1, button2]

# Main loop
def select_game_mode():
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False 
                pygame.display.quit()
                pygame.quit()
                exit()  
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                for button in buttons:
                    if button.check_collision(mouse_pos):
                        return button.action


        # Clear the screen
        screen.fill((255,255,255))
        
        
        # Draw loading screen
        loading_screen_image = pygame.image.load('images/fundal_2.png')  # Replace with your image path
        loading_screen_image = pygame.transform.scale(loading_screen_image, (width, height))

        screen.blit(loading_screen_image, (0, 0))
        
        font = pygame.font.Font("slkscr.ttf", 100)
        text1 = font.render("Pizzeria Bot", True, (180, 196, 36))
        text_rect = text1.get_rect(centerx=width // 2, top=30)
        screen.blit(text1, text_rect)

        # Draw buttons
        for button in buttons:
            button.draw(screen)
            

        # Update the display
        pygame.display.flip()
        
env_id = select_game_mode()


if env_id == 0:
    env = DeliveryEnv()
elif env_id == 1:
    env = DoubleDeliveryEnv()
env.reset()

# CREATE THE Q TABLE

action_size = env.action_space.n
state_size = env.observation_space.n
qtable = np.zeros((state_size, action_size))

# CREATE THE HYPERPARAMETERS

total_episodes = 70000

# Total episodes
total_test_episodes = 15     # Total test episodes
max_steps = 50               # Max steps per episode

learning_rate = 0.9           # Learning rate
gamma = 0.95                 # Discounting rate

# Exploration parameters
epsilon = 1.0                 # Exploration rate
max_epsilon = 1.0             # Exploration probability at start
min_epsilon = 0.05            # Minimum exploration probability 
decay_rate = 0.005             # Exponential decay rate for exploration prob

#CREATE THE Q LEARNING ALGORITHM

rewards = []

for episode in range(total_episodes):
    # Reset the environment
    state = env.reset()
    step = 0
    done = False
    total_rewards = 0
    
    
    for step in range(max_steps):
        #  Choose an action a in the current world state (s)
        ## First we randomize a number
        exp_exp_tradeoff = random.uniform(0,1)
        
        ## If this number > greater than epsilon --> exploitation (taking the biggest Q value for this state)
        if exp_exp_tradeoff > epsilon:
            action = np.argmax(qtable[state,:])
        
        # Else doing a random choice --> exploration
        else:
            action = env.action_space.sample()
        
        # Take the action (a) and observe the outcome state(s') and reward (r)
        new_state, reward, done, info = env.step(action)

        # Update Q(s,a):= Q(s,a) + lr [R(s,a) + gamma * max Q(s',a') - Q(s,a)]
        qtable[state, action] = qtable[state, action] + learning_rate * (reward + gamma * np.max(qtable[new_state, :]) - qtable[state, action])
        
        total_rewards += reward
                
        # Our new state is state
        state = new_state
        
        # If done : finish episode
        if done == True: 
            break
        
    
    # Reduce epsilon (because we need less and less exploration)
    epsilon = min_epsilon + (max_epsilon - min_epsilon)*np.exp(-decay_rate*episode) 
    rewards.append(total_rewards)
    
print("Score over time: " + str(sum(rewards)/total_episodes))
print(qtable)

# TEST THE ALGORITHM

env.reset()
rewards = []


for episode in range(total_test_episodes):
    state = env.reset()

    step = 0
    done = False
    total_rewards = 0
    print("****************************************************")
    print("EPISODE ", episode)

    for step in range(max_steps):
        
        # Take the action (index) that have the maximum expected future reward given that state
        action = np.argmax(qtable[state,:])
        new_state, reward, done, info = env.step(action)
        
        env.render_mode(action,episode,total_rewards)
        
        total_rewards += reward
        
        if done:
            rewards.append(total_rewards)
            break
        state = new_state

    print ("Score over time: " +  str(sum(rewards)/total_test_episodes))
    
env.close()