from collections import deque
from pygame import K_LEFT, K_RIGHT, K_UP, K_DOWN
import math
import time


def void_pos(size: tuple, snake) -> list:
    sx, sy = size
    valid_pos = [(x, y) for x in range(sx) for y in range(sy) if (x, y) not in snake.pos]
    return valid_pos


def check_out_of_bounds(size: int, head: tuple):
    return not (0 <= head[0] < size and 0 <= head[1] < size)


def check_hit_self_pos(pos:list, head: tuple):
    p = pos[1:]
    return head in p


class Direction:
    left = K_LEFT
    right = K_RIGHT
    up = K_UP
    down = K_DOWN

    @classmethod
    def movement(cls, direct):
        match direct:
            case cls.down: return (0, 1)
            case cls.up: return (0, -1)
            case cls.left: return (-1, 0)
            case cls.right: return (1, 0)
        raise TypeError(f"Key '{direct}' is not valid")


reversed_dirs = {
    Direction.up: Direction.down,
    Direction.down: Direction.up,
    Direction.left: Direction.right,
    Direction.right: Direction.left,
}


def valid_d(current_dir):
    valid = [k for k in reversed_dirs]
    valid.remove(reversed_dirs[current_dir])
    return valid


def adj(head: tuple, pos, size: int):
    """Conta vizinhos livres de `head`. Usa `next_head` (corrigido)."""
    f = 0
    for d in reversed_dirs:
        dx, dy = Direction.movement(d)
        next_head = (head[0] + dx, head[1] + dy)
        if not (check_hit_self_pos(pos, next_head) or check_out_of_bounds(size, next_head)):
            f += 1
    return f if f > 0 else False


def valid_next_heads(current_dir, pos, size: int, head: tuple, target:tuple, ftail:bool=False):
    """
    Apenas enumera direções válidas (sem reversão).
    O filtro de colisão é feito no `_bfs_target`, que monta `new_state`
    e sabe se a cauda avança (movimento normal) ou não (comeu).
    Filtrar aqui bloquearia perseguição à própria cauda.
    """
    for d in valid_d(current_dir):
        dx, dy = Direction.movement(d)
        next_head = (head[0] + dx, head[1] + dy)
        next_pos = []

        if next_head == target and not ftail:
            next_pos = [next_head]+pos
        else:
            next_pos = [next_head]+pos[:-1]

        if not (check_hit_self_pos(next_pos, next_head) or check_out_of_bounds(size, next_head)):
            yield next_head, d


class Snake:
    def __init__(self, pos: list, size: int):
        self.score = 0
        self.size = size
        self.head = pos[0]
        self.pos = deque(pos)
        self.direction = Direction.up
        self.automated = False
        self.__path = deque([])

    # ---- FIX PRINCIPAL: cabeça é sempre derivada de pos[0] ----

    def _bfs_target(self, initial_state, head, target, size,
                    initial_dir=None, ftail=False):
        visited = set()
        tails = set()
        start_dir = self.direction if initial_dir is None else initial_dir
        queue = deque([(list(initial_state), head, [], start_dir)])
        count = 0
        tot = 2*size*(size-1)

        paths = []

        while queue:
            state, nh, dirs, last_dir = queue.popleft()

            if nh == target:
                # Só faz a checagem de cauda se ainda houver espaço e não
                # for a própria verificação. `size*size > len(state)`
                # é False quando comer acabou de encher o tabuleiro

                result = []
                # (vitória) — nesse caso não precisa de checagem.
                if not ftail and size * size > len(state) > 0:
                    eat_dir = dirs[-1] if dirs else start_dir
                    result = self._bfs_target(
                        state, nh, state[-1], size,
                        ftail=True, initial_dir=eat_dir,
                    )
                    if not result:
                        continue
                return deque(dirs)

            if nh in tails and size*size > len(state) > 0 and not ftail:
                if not check_hit_self_pos(state, nh) and not check_out_of_bounds(size, nh):
                    result = self._bfs_target(
                        state, nh, state[-1], size, ftail=True, initial_dir=dirs[-1]
                    )
                    if result:
                        paths.append(dirs)

            elif len(dirs) >= tot and not ftail:
                result = self._bfs_target(
                    state, nh, state[-1], size, ftail=True, initial_dir=dirs[-1]
                )
                if result:
                    paths.append(dirs)

            for h, d in valid_next_heads(last_dir, state, size, nh, target, ftail=ftail):
                # Cresce só quando realmente come (não no ftail).
                if h == target and not ftail:
                    new_state = [h] + state
                else:
                    new_state = [h] + state[:-1]

                key = (nh, h, new_state[-1])
                if key in visited:
                    continue

                visited.add(key)
                tails.add(new_state[-1])
                queue.append((new_state, h, dirs + [d], d))
    
        
        return False if not paths else deque(max(paths, key=lambda x:len(x)))
        

    def approx_tail(self, tail:tuple):
        min_d = None
        min_dist = float("inf")

        for h, d in valid_next_heads(self.direction, list(self.pos), self.size, self.head, tail, ftail=True):
            if math.dist(h,tail) < min_dist:
                min_dist = math.dist(h, tail)
                min_d = d
        if min_d == None:
            return self.direction

        return min_d

    def move(self, fruit: tuple = None, grow=False):
        #print(self.pos)
        tail = list(self.pos)[-1]
        
        if self.automated and fruit:
            # 1. Tenta achar o caminho até a comida com validação de sobrevivência
            if not self.__path:
                self.__path = self._bfs_target(self.pos, self.head, fruit, self.size)
            
            # 2. Se não achou até a comida, tenta ir de forma segura em direção à cauda direta
            if not self.__path:
                self.__path = self._bfs_target(self.pos, self.head, tail, self.size, ftail=True)

            # 3. Executa o próximo movimento gerado ou usa a aproximação de emergência
            if self.__path:
                self.direction = self.__path.popleft()
            else:
                self.direction = self.approx_tail(tail)

        dx, dy = Direction.movement(self.direction)
        hx, hy = self.head

        self.head = (dx + hx, dy + hy)
        self.pos.appendleft(self.head)        

        if self.head == fruit:
            self.score += 1
            return True, tail
        else:
            return False, self.pos.pop()
