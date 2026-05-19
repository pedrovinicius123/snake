from collections import deque
import pygame

class Directions:
    UP=pygame.K_UP
    DOWN=pygame.K_DOWN
    LEFT=pygame.K_LEFT
    RIGHT=pygame.K_RIGHT

rev_directions = {
    Directions.UP: Directions.DOWN,
    Directions.DOWN: Directions.UP,
    Directions.LEFT: Directions.RIGHT,
    Directions.RIGHT: Directions.LEFT
}

class Snake:
    def __init__(self):
        self.pos = deque()
        self.current_action = Directions.UP
        self.reversed_position = rev_directions[Directions.UP]
        self.head = [0, 0]

    def move(self, positions, grow=False):
        match self.current_action:
            case Directions.DOWN:
                self.head[1] -= 1

            case Directions.UP:
                self.head[1] += 1

            case Directions.RIGHT:
                self.head[0] += 1

            case Directions.LEFT:
                self.head[0] -= 1

        self.pos.appendleft((*self.head,))
        positions.remove((*self.head,))

        if not grow:
            old_p = self.pos.pop()
            positions.add(old_p)

    def get_best_direction(self, exc, fruit):
        fx, fy = fruit
        dx_plus = fx - (self.head[0]+1)
        dx_minus = fx - (self.head[0]-1)

        dy_plus = fy - (self.head[1]+1)
        dy_minus = fy - (self.head[1]-1)

        dx = min(dx_minus, dx_plus)
        dy = min(dy_minus, dy_plus)

        if dx <= dy:
            if dx == dx_minus and rev_directions[self.current_action] != Directions.LEFT and Directions.LEFT not in exc:
                self.current_action = Directions.LEFT
                return True
                    
            elif dx == dx_plus and rev_directions[self.current_action] != Directions.RIGHT and Directions.RIGHT not in exc:
                self.current_action = Directions.RIGHT
                return True
            
        else:
            if dy == dy_minus and rev_directions[self.current_action] != Directions.DOWN and Directions.DOWN not in exc:
                self.current_action = Directions.DOWN
                return True
                    
            elif dy == dy_plus and rev_directions[self.current_action] != Directions.UP and Directions.UP not in exc:
                self.current_action = Directions.UP
                return True
            
        return False
    
    def change_direction(self, positions, fruit):
        have_obstacles, pos_wrap_exc = self.check_obstacles(positions)
        if have_obstacles:
            ddir = Directions.__dict__()
            for d in pos_wrap_exc:
                if d not in ddir and self.get_best_direction(pos_wrap_exc, fruit):
                    return True
        
        return self.get_best_direction(pos_wrap_exc, fruit)

    def check_obstacles(self, positions):
        head = self.pos[0]
        positions_up = [(x, y) for (x, y) in positions if y > head[1] and (x, y) not in self.pos]
        positions_left = [(x, y) for (x, y) in positions if x < head[0] and (x, y) not in self.pos]
        positions_right = [(x, y) for (x, y) in positions if x > head[0] and (x, y) not in self.pos]
        positions_down = [(x, y) for (x, y) in positions if y < head[1] and (x, y) not in self.pos]

        tot_positions_wrap_exc = []
        result = False 

        match self.current_action:
            case Directions.UP:
                if not positions_up:
                    tot_positions_wrap_exc.append(Directions.UP)
                    result = True
                
            case Directions.DOWN:
                if not positions_down:
                    tot_positions_wrap_exc.append(Directions.DOWN)
                    result = True
                
            case Directions.LEFT:
                if not positions_left:
                    tot_positions_wrap_exc.append(Directions.LEFT)
                    result = True
            
            case Directions.RIGHT:
                if not positions_right:
                    tot_positions_wrap_exc.append(Directions.RIGHT)
                    result = True
                
        return result, tot_positions_wrap_exc
    