// Simple in-browser explorer that calls the Python backend for move stats.
(function () {
  const boardEl = document.getElementById('board');
  const boardPanel = document.querySelector('.board-panel');
  const statusEl = document.getElementById('statusText');
  const pathEl = document.getElementById('pathTrail');
  const statsEl = document.getElementById('stats');
  const nextMovesEl = document.getElementById('nextMoves');
  const sidePanel = document.querySelector('.side');
  const applyBtn = document.getElementById('applyFilters');
  const toStartBtn = document.getElementById('toStartBtn');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const toEndBtn = document.getElementById('toEndBtn');
  const importBtn = document.getElementById('importBtn');
  const importStatusEl = document.getElementById('importStatus');
  const importUsernameEl = document.getElementById('importUsername');
  const importToggle = document.getElementById('importToggle');
  const filterToggle = document.getElementById('filterToggle');
  const importPanel = document.getElementById('importPanel');
  const filterPanel = document.getElementById('filterPanel');

  const colorSel = document.getElementById('color');
  const resultSel = document.getElementById('result');
  const timeSel = document.getElementById('timeControl');
  const dateFromEl = document.getElementById('dateFrom');
  const dateToEl = document.getElementById('dateTo');
  const minOppRatingEl = document.getElementById('minOppRating');
  const maxOppRatingEl = document.getElementById('maxOppRating');
  const playerSelect = document.getElementById('playerSelect');
  const playerInput = document.getElementById('playerInput');
  const refreshPlayersBtn = document.getElementById('refreshPlayers');

  if (typeof window.Chess === 'undefined') {
    statusEl.textContent = 'Chess.js failed to load (check network/CDN).';
    console.error('Chess.js missing: verify CDN accessibility.');
    return;
  }

  const chess = new window.Chess();
  let pathSAN = [];
  let cursor = 0; // index of next move to play in pathSAN
  let lastPayload = null;
  let loadedPlayers = [];

  const board = Chessboard(boardEl, {
    draggable: true,
    position: 'start',
    pieceTheme: 'https://cdn.jsdelivr.net/npm/chessboardjs/www/img/chesspieces/wikipedia/{piece}.png',
    onDrop: handleDrop,
    onSnapEnd: () => board.position(chess.fen(), false),
  });

  // Keep sidebar height aligned to board panel on desktop sizes.
  function syncPanelHeight() {
    if (!sidePanel || !boardPanel) return;
    if (window.innerWidth <= 900) {
      sidePanel.style.height = 'auto';
      return;
    }
    sidePanel.style.height = `${boardPanel.offsetHeight}px`;
  }

  syncPanelHeight();
  window.addEventListener('resize', syncPanelHeight);

  function currentPath() {
    return pathSAN.slice(0, cursor);
  }

  function rebuildPosition() {
    chess.reset();
    const seq = currentPath();
    seq.forEach((san) => chess.move(san));
    board.position(chess.fen(), false);
    pathEl.textContent = seq.join(' ');
  }

  function selectedPlayer() {
    const custom = playerInput.value.trim();
    if (custom) return custom;
    return playerSelect.value || null;
  }

  function gatherFilters() {
    const payload = {
      player: selectedPlayer(),
      color: colorSel.value || 'white',
      result: resultSel.value || null,
      time_control: timeSel.value || null,
      date_from: dateFromEl.value || null,
      date_to: dateToEl.value || null,
      min_opponent_rating: minOppRatingEl.value ? Number(minOppRatingEl.value) : null,
      max_opponent_rating: maxOppRatingEl.value ? Number(maxOppRatingEl.value) : null,
      path: currentPath(),
    };
    lastPayload = payload;
    return payload;
  }

  async function fetchPlayers() {
    try {
      const res = await fetch('/api/players');
      if (!res.ok) throw new Error(`Failed to load players (${res.status})`);
      const data = await res.json();
      loadedPlayers = data.players || [];
      const previous = playerSelect.value;
      playerSelect.innerHTML = '';
      const placeholder = document.createElement('option');
      placeholder.value = '';
      placeholder.textContent = loadedPlayers.length ? 'Select player' : 'No players yet';
      playerSelect.appendChild(placeholder);
      loadedPlayers.forEach((p) => {
        const opt = document.createElement('option');
        opt.value = p;
        opt.textContent = p;
        playerSelect.appendChild(opt);
      });
      if (playerInput.value.trim()) return;
      if (loadedPlayers.includes(previous)) {
        playerSelect.value = previous;
      } else if (loadedPlayers.length) {
        playerSelect.value = loadedPlayers[0];
      }
    } catch (err) {
      console.error(err);
      statusEl.textContent = 'Could not load players — check server.';
    }
  }

  async function fetchNextMoves() {
    const payload = lastPayload || gatherFilters();
    payload.path = currentPath();
    statusEl.textContent = 'Loading…';
    try {
      const res = await fetch('/api/next-moves', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`Request failed: ${res.status}`);
      const data = await res.json();
      updateUI(data);
    } catch (err) {
      console.error(err);
      statusEl.textContent = 'Backend unavailable — ensure serve_frontend.py is running.';
    }
  }

  function handleDrop(source, target) {
    const move = chess.move({ from: source, to: target, promotion: 'q' });
    if (move === null) return 'snapback';
    if (cursor < pathSAN.length) {
      pathSAN = pathSAN.slice(0, cursor);
    }
    pathSAN.push(move.san);
    cursor = pathSAN.length;
    pathEl.textContent = currentPath().join(' ');
    fetchNextMoves();
  }

  function updateStats(stats, totalGames) {
    if (!stats || !totalGames) {
      statsEl.innerHTML = '<strong>0 games</strong> match these filters.';
      return;
    }
    const { wins = 0, draws = 0, losses = 0, total = 0, winRate = 0, drawRate = 0, lossRate = 0 } = stats;
    statsEl.innerHTML = `
      <div><strong>${totalGames}</strong> games after filtering</div>
      <div>Current node: <strong>${total}</strong> games</div>
      <div>W ${wins} (${(winRate * 100).toFixed(1)}%) · D ${draws} (${(drawRate * 100).toFixed(1)}%) · L ${losses} (${(lossRate * 100).toFixed(1)}%)</div>
    `;
  }

  function applyMoveFromCard(moveSAN) {
    if (cursor < pathSAN.length) {
      pathSAN = pathSAN.slice(0, cursor);
    }
    const applied = chess.move(moveSAN);
    if (!applied) {
      statusEl.textContent = 'Move could not be applied here.';
      return;
    }
    pathSAN.push(moveSAN);
    cursor = pathSAN.length;
    board.position(chess.fen(), false);
    pathEl.textContent = currentPath().join(' ');
    fetchNextMoves();
  }

  function updateNextMoves(list) {
    nextMovesEl.innerHTML = '';
    if (!list || list.length === 0) {
      nextMovesEl.innerHTML = '<div class="move-card">No continuations here.</div>';
      return;
    }
    list.forEach((item) => {
      const total = item.stats?.total || 0;
      const wins = item.stats?.wins || 0;
      const draws = item.stats?.draws || 0;
      const losses = item.stats?.losses || 0;
      const card = document.createElement('div');
      card.className = 'move-card';
      const winRate = total ? (wins / total) * 100 : 0;
      const drawRate = total ? (draws / total) * 100 : 0;
      const lossRate = total ? (losses / total) * 100 : 0;
      const segments = [];
      if (winRate > 0) segments.push(`<div class="result-segment result-win" style="width:${winRate}%;" title="${winRate.toFixed(0)}% wins">${winRate >= 10 ? winRate.toFixed(0) + '%' : ''}</div>`);
      if (drawRate > 0) segments.push(`<div class="result-segment result-draw" style="width:${drawRate}%;" title="${drawRate.toFixed(0)}% draws">${drawRate >= 10 ? drawRate.toFixed(0) + '%' : ''}</div>`);
      if (lossRate > 0) segments.push(`<div class="result-segment result-loss" style="width:${lossRate}%;" title="${lossRate.toFixed(0)}% losses">${lossRate >= 10 ? lossRate.toFixed(0) + '%' : ''}</div>`);
      card.innerHTML = `
        <div class="move-row">
          <div class="move">${item.move}</div>
          <div class="result-bar">${segments.join('')}</div>
        </div>
      `;
      card.addEventListener('click', () => applyMoveFromCard(item.move));
      nextMovesEl.appendChild(card);
    });
  }

  function updateUI(data) {
    if (!data) return;
    pathEl.textContent = currentPath().join(' ');
    statusEl.textContent = data.games ? `${data.games} games match filters` : 'No games for these filters';
    updateStats(data.stats, data.games);
    updateNextMoves(data.next);
  }

  function undoMove() {
    if (cursor === 0) return;
    cursor -= 1;
    rebuildPosition();
    fetchNextMoves();
  }

  function resetBoard() {
    chess.reset();
    pathSAN = [];
    cursor = 0;
    board.start();
    pathEl.textContent = '';
    fetchNextMoves();
  }

  function redoMove() {
    if (cursor >= pathSAN.length) return;
    cursor += 1;
    rebuildPosition();
    fetchNextMoves();
  }

  function jumpToStart() {
    cursor = 0;
    rebuildPosition();
    fetchNextMoves();
  }

  function jumpToEnd() {
    cursor = pathSAN.length;
    rebuildPosition();
    fetchNextMoves();
  }

  function togglePanel(panel) {
    panel.classList.toggle('hidden');
  }

  async function importGames() {
    const username = importUsernameEl.value.trim();
    const customPlayer = playerInput.value.trim();
    const selected = playerSelect.value;
    let player = null;
    if (customPlayer) {
      player = customPlayer;
    } else if (selected && selected === username) {
      player = selected;
    } else if (!selected) {
      player = username; // no selection, default to username
    } else {
      // selected player differs from typed username; default to username to avoid mixing
      player = username;
    }
    if (!username) {
      importStatusEl.textContent = 'Enter a username.';
      return;
    }
    importStatusEl.textContent = 'Importing…';
    try {
      const res = await fetch('/api/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, player }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        importStatusEl.textContent = data.error || `Failed (${res.status})`;
        return;
      }
      importStatusEl.textContent = `Imported ${data.imported} new (total ${data.total}).`;
      // Refresh filters/trie after import
      pathSAN = [];
      cursor = 0;
      chess.reset();
      board.start();
      pathEl.textContent = '';
      playerInput.value = '';
      await fetchPlayers();
      if (playerSelect && player) {
        playerSelect.value = player;
      }
      fetchNextMoves();
    } catch (err) {
      importStatusEl.textContent = 'Import failed (network).';
      console.error(err);
    }
  }

  applyBtn.addEventListener('click', () => {
    pathSAN = [];
    cursor = 0;
    chess.reset();
    board.start();
    pathEl.textContent = '';
    gatherFilters();
    fetchNextMoves();
  });

  refreshPlayersBtn?.addEventListener('click', async () => {
    await fetchPlayers();
    pathSAN = [];
    cursor = 0;
    chess.reset();
    board.start();
    pathEl.textContent = '';
    lastPayload = null;
    fetchNextMoves();
  });

  playerSelect?.addEventListener('change', () => {
    playerInput.value = '';
    pathSAN = [];
    cursor = 0;
    chess.reset();
    board.start();
    pathEl.textContent = '';
    lastPayload = null;
    fetchNextMoves();
  });

  toStartBtn?.addEventListener('click', jumpToStart);
  prevBtn?.addEventListener('click', undoMove);
  nextBtn?.addEventListener('click', redoMove);
  toEndBtn?.addEventListener('click', jumpToEnd);
  importBtn?.addEventListener('click', importGames);
  importToggle?.addEventListener('click', () => togglePanel(importPanel));
  filterToggle?.addEventListener('click', () => togglePanel(filterPanel));

  // Arrow key navigation for chess moves
  document.addEventListener('keydown', (e) => {
    // Ignore if user is typing in an input field
    if (e.target.matches('input, textarea, select')) return;
    
    switch (e.key) {
      case 'ArrowLeft':
        e.preventDefault();
        undoMove();
        break;
      case 'ArrowRight':
        e.preventDefault();
        redoMove();
        break;
      case 'ArrowUp':
        e.preventDefault();
        jumpToStart();
        break;
      case 'ArrowDown':
        e.preventDefault();
        jumpToEnd();
        break;
    }
  });

  // Kick things off
  fetchPlayers().then(() => {
    gatherFilters();
    fetchNextMoves();
  });
})();
