"""Cobrinha automática — servidor entrega lotes de frames pré-calculados."""

import random
import uuid

from flask import Flask, jsonify, render_template, request, session

from player import Snake, check_hit_self_pos, check_out_of_bounds, void_pos

app = Flask(__name__)
app.secret_key = "snake-auto-dev-key"  # troque em produção
GAMES = {}

MIN_SIZE, MAX_SIZE, DEFAULT_SIZE = 5, 50, 15
BATCH_DEFAULT = 500
BATCH_MAX = 2000
# Teto de bytes por resposta (evita payloads gigantes em grades grandes)
BATCH_BYTE_CAP = 2_000_000


def init_snake_pos(size):
    sx, sy = size
    return random.randint(0, sx - 1), random.randint(0, sy - 1)


class Game:
    def __init__(self, size: int):
        self.size = size
        self.snake = Snake([init_snake_pos((size, size))], size=size)
        self.snake.automated = True  # jogo não jogável
        self.fruit = random.choice(void_pos((size, size), self.snake))
        self.gameover = False
        self.win = False

    def state(self):
        return {
            "size": self.size,
            "snake": [[x, y] for x, y in self.snake.pos],
            "fruit": list(self.fruit),
            "score": self.snake.score,
            "gameover": self.gameover,
            "win": self.win,
        }

    def advance(self):
        if self.gameover:
            return

        snake = self.snake
        grow, _tail = snake.move(self.fruit)

        # 1) Vitória
        if snake.score == self.size * self.size - 1:
            self.win = True
            self.gameover = True
            return

        # 2) Comeu: fruta nova, sem checagem de colisão
        if grow:
            self.fruit = random.choice(void_pos((self.size, self.size), snake))
            return

        # 3) Colisão — usa pos[0] como cabeça autoritativa, não snake.head
        pos_list = list(snake.pos)
        if not pos_list:
            print("[DEATH] pos vazio")
            self.gameover = True
            return

        head = tuple(pos_list[0])

        # Diagnóstico: se snake.head não bate com pos[0], move() está
        # deixando o atributo defasado — causa clássica de falso positivo
        if tuple(snake.head) != head:
            print(
                f"[WARN] snake.head={tuple(snake.head)} != pos[0]={head} "
                f"(len={len(pos_list)}, score={snake.score})"
            )

        body = [tuple(p) for p in pos_list[1:]]
        self_hit = head in body
        oob = not (0 <= head[0] < self.size and 0 <= head[1] < self.size)

        if self_hit or oob:
            print(
                f"[DEATH] head={head} self_hit={self_hit} oob={oob} "
                f"len={len(pos_list)} score={snake.score} "
                f"snake.head={tuple(snake.head)} fruit={tuple(self.fruit)}"
            )
            self.gameover = True

def _gid():
    if "gid" not in session:
        session["gid"] = uuid.uuid4().hex
    return session["gid"]


@app.get("/")
def index():
    return render_template(
        "index.html",
        min_size=MIN_SIZE, max_size=MAX_SIZE, default_size=DEFAULT_SIZE,
    )


@app.post("/api/new")
def api_new():
    data = request.get_json(silent=True) or {}
    try:
        size = int(data.get("size", DEFAULT_SIZE))
    except (TypeError, ValueError):
        size = DEFAULT_SIZE
    size = max(MIN_SIZE, min(MAX_SIZE, size))

    game = Game(size)
    GAMES[_gid()] = game

    # Primeira leva já volta junto: elimina um round-trip inicial.
    initial = game.state()
    priming = []
    for _ in range(min(100, BATCH_DEFAULT)):
        if game.gameover:
            break
        game.advance()
        priming.append(game.state())

    return jsonify({
        "initial": initial,
        "priming": priming,
        "batch_size": BATCH_DEFAULT,
    })


@app.post("/api/batch")
def api_batch():
    game = GAMES.get(_gid())
    if game is None:
        return jsonify({"error": "sem jogo ativo"}), 400

    data = request.get_json(silent=True) or {}
    try:
        n = int(data.get("n", BATCH_DEFAULT))
    except (TypeError, ValueError):
        n = BATCH_DEFAULT

    n = max(1, min(BATCH_MAX, n))
    # Reduz o lote quando a grade é grande para segurar o payload.
    size_cap = max(50, BATCH_BYTE_CAP // (game.size * game.size))
    n = min(n, size_cap)

    frames = []
    for _ in range(n):
        if game.gameover:
            break
        game.advance()
        frames.append(game.state())

    return jsonify({
        "frames": frames,
        "gameover": game.gameover,
        "win": game.win,
    })


if __name__ == "__main__":
    app.run(debug=False)
