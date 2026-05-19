from snake import Snake
import pygame
import random

MTRX_SIZE = 20
SQUARE_SIZE = 20
GREEN = (0, 255, 0)
RED = (255, 0, 0)

def generate_random_fruit_coords(snake:Snake, all_pos):
    valid_pos = [pos for pos in all_pos if pos not in snake.pos]
    return random.choice(valid_pos)

def init_valid_pos():
    return {(x, y) for x in range(MTRX_SIZE) for y in range(MTRX_SIZE)}

def game():
    pygame.init()
    display = pygame.display.set_mode((MTRX_SIZE*SQUARE_SIZE, MTRX_SIZE*SQUARE_SIZE))
    valid_pos = init_valid_pos()

    snake = Snake()
    fruit = generate_random_fruit_coords(snake, valid_pos)
    snake.pos.append(random.choice([*valid_pos]))
    clock = pygame.time.Clock()
    
    running = True
    while running:
        display.fill((0,0,0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        grow = False
        if snake.head == fruit:
            fruit = generate_random_fruit_coords(snake, all_pos=valid_pos)
            grow = True
        
        pygame.draw.rect(display, RED, pygame.Rect(fruit[0]*SQUARE_SIZE, fruit[1]*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
        snake.move(valid_pos, grow=grow)
        snake.change_direction(valid_pos, fruit)
        for pos in snake.pos:
            pygame.draw.rect(display, GREEN, pygame.Rect(pos[0]*SQUARE_SIZE, pos[1]*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

        
        pygame.display.flip()
        clock.tick(10)

    pygame.quit()


if __name__ == '__main__':
    game()        
