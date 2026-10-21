(() => {
  const $ = (id) => document.getElementById(id);

  const canvas  = $('board');
  const ctx     = canvas.getContext('2d');
  const wrap    = $('wrap');
  const area    = document.querySelector('.board-area');
  const sizeIn  = $('size');
  const speedIn = $('speed');
  const tpsLbl  = $('tpsLabel');
  const scoreEl = $('score');
  const gridEl  = $('grid');
  const grid2El = $('grid2');
  const bufEl   = $('buf');
  const overlay = $('overlay');
  const restart = $('restart');

  // Estado do jogo / buffer local
  let state      = null;
  let buffer     = [];
  let block      = 1;
  let tps        = 30;
  let running    = false;
  let fetching   = false;
  let gen        = 0;
  let overlayUp  = false;
  let lastTime   = 0;
  let accumulator = 0;   // em "ticks"

  const LOW_WATER = 200;          // pede mais quando buffer < isto
  const MAX_REQUEST = 2000;       // limite por lote

  // ------------------------------------------------------------- utilidades
  function sliderToTps(v) {
    // 0..100 → 1..2000 tps (escala exponencial)
    const t = Math.pow(10, 0.03301 * v);
    return Math.max(1, Math.round(t));
  }

  function requestedBatch() {
    return Math.max(500, Math.min(MAX_REQUEST, Math.round(tps * 1.5)));
  }

  // ------------------------------------------------------------- dimensiona
  function fitCanvas() {
    if (!state) return;
    const rect = area.getBoundingClientRect();
    const avail = Math.max(40, Math.min(rect.width, rect.height) - 4);
    block = Math.max(2, Math.floor(avail / state.size));

    const W = block * state.size;
    canvas.style.width  = W + 'px';
    canvas.style.height = W + 'px';
    canvas.width  = W;
    canvas.height = W;
    wrap.style.width  = W + 'px';
    wrap.style.height = W + 'px';
    render();
  }

  // ----------------------------------------------------------------- render
  function render() {
    if (!state) return;
    const size = state.size;
    const W    = canvas.width;

    ctx.fillStyle = '#0b1020';
    ctx.fillRect(0, 0, W, W);

    if (block >= 6) {
      ctx.strokeStyle = 'rgba(255,255,255,0.05)';
      ctx.lineWidth = 1;
      for (let i = 1; i < size; i++) {
        const p = i * block + 0.5;
        ctx.beginPath(); ctx.moveTo(p, 0); ctx.lineTo(p, W); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(0, p); ctx.lineTo(W, p); ctx.stroke();
      }
    }

    const n = state.snake.length;
    for (let i = 0; i < n; i++) {
      const [x, y] = state.snake[i];
      const t = n > 1 ? i / (n - 1) : 0;
      const r = Math.round(100 - 60 * t);
      const g = Math.round(255 - 120 * t);
      const b = Math.round(100 - 60 * t);
      ctx.fillStyle = `rgb(${r},${g},${b})`;
      ctx.fillRect(x * block, y * block, block, block);
    }

    const [fx, fy] = state.fruit;
    const pad = Math.max(1, Math.round(block * 0.15));
    ctx.fillStyle = '#ff6b6b';
    ctx.fillRect(fx * block + pad, fy * block + pad,
                 block - 2 * pad, block - 2 * pad);

    scoreEl.textContent = state.score;
    gridEl.textContent  = size;
    grid2El.textContent = size;
  }

  // ---------------------------------------------------------------- overlay
  function showOverlay() {
    if (overlayUp) return;
    overlayUp = true;
    overlay.textContent = state && state.win
      ? '🎉 Vitória!'
      : `💀 Fim de jogo — ${state ? state.score : 0} ponto${state && state.score === 1 ? '' : 's'}`;
    overlay.classList.remove('hidden');

    const myGen = gen;
    setTimeout(() => {
      if (myGen === gen) newGame(state ? state.size : parseInt(sizeIn.value, 10) || 15);
    }, 1500);
  }

  function showMessage(msg) {
    overlayUp = true;
    overlay.textContent = msg;
    overlay.classList.remove('hidden');
  }

  // ------------------------------------------------------------------ HTTP
  async function fetchBatch() {
    if (fetching || !running) return;
    fetching = true;
    const myGen = gen;
    try {
      const res = await fetch('/api/batch', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({n: requestedBatch()}),
      });
      const data = await res.json();
      if (myGen !== gen) return;

      if (data.frames.length === 0) {
        if (data.gameover) {
          running = false;
          if (state) {
            state.gameover = true;
            state.win = data.win;
            render();
          }
          showOverlay();
        }
        return;
      }
      buffer.push(...data.frames);
    } catch (e) {
      console.error('fetchBatch:', e);
    } finally {
      if (myGen === gen) fetching = false;
    }
  }

  // ------------------------------------------------------------ novo jogo
  async function newGame(size) {
    gen++;
    const myGen = gen;
    running = false;
    fetching = false;
    buffer = [];
    accumulator = 0;
    lastTime = 0;
    state = null;
    overlayUp = false;
    overlay.classList.add('hidden');
    scoreEl.textContent = '0';
    bufEl.textContent = '0';

    try {
      const res = await fetch('/api/new', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({size}),
      });
      const data = await res.json();
      if (myGen !== gen) return;

      state = data.initial;
      buffer = data.priming.slice();
      running = true;
      fitCanvas();
      render();
      bufEl.textContent = buffer.length;
    } catch (e) {
      if (myGen !== gen) return;
      showMessage('Erro ao conectar.');
    }
  }

  // -------------------------------------------------------- loop de render
  function animate(now) {
    requestAnimationFrame(animate);
    if (!running) { lastTime = 0; return; }
    if (!lastTime) { lastTime = now; return; }

    const dt = Math.min(0.2, (now - lastTime) / 1000);
    lastTime = now;
    accumulator += dt * tps;

    // Segurança: nunca deixa acumular eternamente (ex.: rede lenta)
    if (accumulator > 1e6) accumulator = 1e6;

    let advanced = false;
    while (accumulator >= 1 && buffer.length > 0) {
      state = buffer.shift();
      accumulator -= 1;
      advanced = true;
      if (state.gameover) { running = false; break; }
    }

    if (advanced) {
      render();
      bufEl.textContent = buffer.length;
    }

    if (!running) { showOverlay(); return; }

    if (!fetching && buffer.length < LOW_WATER) fetchBatch();
  }

  // ------------------------------------------------------------- eventos
  restart.addEventListener('click', () => {
    const n = parseInt(sizeIn.value, 10) || 15;
    newGame(Math.max(5, Math.min(50, n)));
  });

  speedIn.addEventListener('input', () => {
    tps = sliderToTps(parseInt(speedIn.value, 10));
    tpsLbl.textContent = tps;
  });

  window.addEventListener('resize', fitCanvas);
  if (window.ResizeObserver) new ResizeObserver(fitCanvas).observe(area);

  // inicialização
  tps = sliderToTps(parseInt(speedIn.value, 10));
  tpsLbl.textContent = tps;
  requestAnimationFrame(animate);
  newGame(parseInt(sizeIn.value, 10) || 15);
})();
