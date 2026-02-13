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
  const filterOverlay = document.getElementById('filterOverlay');
  const closeFilterOverlay = document.getElementById('closeFilterOverlay');

  const colorSel = document.getElementById('color');
  const resultSel = document.getElementById('result');
  const timeSel = document.getElementById('timeControl');
  const dateFromEl = document.getElementById('dateFrom');
  const dateToEl = document.getElementById('dateTo');
  const minOppRatingEl = document.getElementById('minOppRating');
  const maxOppRatingEl = document.getElementById('maxOppRating');
  const playerSelectBtn = document.getElementById('playerSelectBtn');
  const playerSelectLabel = document.getElementById('playerSelectLabel');
  const playerDropdown = document.getElementById('playerDropdown');
  const playerCheckboxList = document.getElementById('playerCheckboxList');
  const allPlayersCheckbox = document.getElementById('allPlayersCheckbox');
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

  function updatePathDisplay() {
    if (pathSAN.length === 0) {
      pathEl.innerHTML = '';
      return;
    }
    const parts = [];
    for (let i = 0; i < pathSAN.length; i++) {
      const move = pathSAN[i];
      const isCurrent = i === cursor - 1;
      const style = isCurrent ? 'font-weight: 700; color: var(--accent);' : '';
      
      if (i % 2 === 0) {
        // White move - add move number
        const moveNum = Math.floor(i / 2) + 1;
        parts.push(`<span style="${style}">${moveNum}. ${move}</span>`);
      } else {
        // Black move - no number, just the move
        parts.push(`<span style="${style}">${move}</span>`);
      }
    }
    pathEl.innerHTML = parts.join(' ');
  }

  function rebuildPosition() {
    chess.reset();
    const seq = currentPath();
    seq.forEach((san) => chess.move(san));
    board.position(chess.fen(), false);
    updatePathDisplay();
  }

  function selectedPlayer() {
    if (allPlayersCheckbox?.checked) return null;
    
    const selected = Array.from(playerCheckboxList?.querySelectorAll('input[type="checkbox"]:checked') || [])
      .map(cb => cb.value);
    
    return selected.length > 0 ? selected : null;
  }

  function gatherFilters() {
    const payload = {
      players: selectedPlayer(),
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
      
      const currentSelected = Array.from(playerCheckboxList?.querySelectorAll('input[type="checkbox"]:checked') || [])
        .map(cb => cb.value);
      
      playerCheckboxList.innerHTML = '';
      
      loadedPlayers.forEach((p) => {
        const div = document.createElement('div');
        div.className = 'player-option';
        const label = document.createElement('label');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = p;
        checkbox.checked = currentSelected.includes(p);
        checkbox.addEventListener('change', handlePlayerCheckboxChange);
        const span = document.createElement('span');
        span.textContent = p;
        label.appendChild(checkbox);
        label.appendChild(span);
        div.appendChild(label);
        playerCheckboxList.appendChild(div);
      });
      
      if (currentSelected.length === 0 && loadedPlayers.length > 0) {
        const firstCheckbox = playerCheckboxList.querySelector('input[type="checkbox"]');
        if (firstCheckbox) {
          firstCheckbox.checked = true;
          updatePlayerLabel();
        }
      } else {
        updatePlayerLabel();
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
    statusEl.className = 'status loading';
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
      statusEl.className = 'status';
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
    updatePathDisplay();
    fetchNextMoves();
  }

  function updateStats(stats, totalGames) {
    // Stats display removed - path is shown in pathTrail div
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
    updatePathDisplay();
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
      if (winRate > 0) segments.push(`<div class="result-segment result-win" style="width:${winRate}%;" title="${wins} white">${winRate >= 8 ? winRate.toFixed(0) + '%' : ''}</div>`);
      if (drawRate > 0) segments.push(`<div class="result-segment result-draw" style="width:${drawRate}%;" title="${draws} draw">${drawRate >= 8 ? drawRate.toFixed(0) + '%' : ''}</div>`);
      if (lossRate > 0) segments.push(`<div class="result-segment result-loss" style="width:${lossRate}%;" title="${losses} black">${lossRate >= 8 ? lossRate.toFixed(0) + '%' : ''}</div>`);
      card.innerHTML = `
        <div class="move-row">
          <div class="move">${item.move}</div>
          <div class="move-count">${total}</div>
          <div class="result-bar">${segments.join('')}</div>
        </div>
      `;
      card.addEventListener('click', () => applyMoveFromCard(item.move));
      nextMovesEl.appendChild(card);
    });
  }

  function updateUI(data) {
    if (!data) return;
    updatePathDisplay();
    statusEl.textContent = data.games ? `${data.games} games match filters` : 'No games for these filters';
    statusEl.className = 'status';
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
    updatePathDisplay();
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
    if (!username) {
      importStatusEl.textContent = 'Enter a username.';
      return;
    }
    importStatusEl.textContent = 'Importing…';
    importStatusEl.className = 'status loading';
    try {
      const res = await fetch('/api/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, player: username }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        importStatusEl.textContent = data.error || `Failed (${res.status})`;
        importStatusEl.className = 'status';
        return;
      }
      importStatusEl.textContent = `Imported ${data.imported} new (total ${data.total}).`;
      importStatusEl.className = 'status';
      // Refresh filters/trie after import
      pathSAN = [];
      cursor = 0;
      chess.reset();
      board.start();
      updatePathDisplay();
      await fetchPlayers();
      fetchNextMoves();
    } catch (err) {
      importStatusEl.textContent = 'Import failed (network).';
      importStatusEl.className = 'status';
      console.error(err);
    }
  }

  function updatePlayerLabel() {
    if (!playerSelectLabel) return;
    
    if (allPlayersCheckbox?.checked) {
      playerSelectLabel.textContent = 'All players';
      return;
    }
    
    const selected = Array.from(playerCheckboxList?.querySelectorAll('input[type="checkbox"]:checked') || []);
    
    if (selected.length === 0) {
      playerSelectLabel.textContent = 'Select players';
    } else if (selected.length === 1) {
      playerSelectLabel.textContent = selected[0].value;
    } else {
      playerSelectLabel.textContent = `${selected.length} players selected`;
    }
  }

  function handlePlayerCheckboxChange(e) {
    const checkbox = e.target;
    
    if (checkbox === allPlayersCheckbox) {
      if (allPlayersCheckbox.checked) {
        // Uncheck all individual players
        playerCheckboxList?.querySelectorAll('input[type="checkbox"]').forEach(cb => {
          cb.checked = false;
        });
      }
    } else {
      // If any individual player is checked, uncheck "All players"
      if (checkbox.checked && allPlayersCheckbox) {
        allPlayersCheckbox.checked = false;
      }
    }
    
    updatePlayerLabel();
    
    pathSAN = [];
    cursor = 0;
    chess.reset();
    board.start();
    updatePathDisplay();
    lastPayload = null;
    fetchNextMoves();
  }

  applyBtn.addEventListener('click', () => {
    gatherFilters();
    fetchNextMoves();
    filterOverlay.classList.add('hidden');
  });

  refreshPlayersBtn?.addEventListener('click', async () => {
    await fetchPlayers();
    pathSAN = [];
    cursor = 0;
    chess.reset();
    board.start();
    updatePathDisplay();
    lastPayload = null;
    fetchNextMoves();
  });

  // Player dropdown button toggle
  playerSelectBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    playerDropdown?.classList.toggle('hidden');
    playerSelectBtn?.classList.toggle('open');
  });

  // All players checkbox
  allPlayersCheckbox?.addEventListener('change', handlePlayerCheckboxChange);

  // Prevent dropdown from closing when clicking inside it
  playerDropdown?.addEventListener('click', (e) => {
    e.stopPropagation();
  });

  // Close dropdown when clicking outside
  document.addEventListener('click', (e) => {
    if (!playerDropdown?.contains(e.target) && 
        e.target !== playerSelectBtn && 
        !playerSelectBtn?.contains(e.target)) {
      playerDropdown?.classList.add('hidden');
      playerSelectBtn?.classList.remove('open');
    }
  });

  toStartBtn?.addEventListener('click', jumpToStart);
  prevBtn?.addEventListener('click', undoMove);
  nextBtn?.addEventListener('click', redoMove);
  toEndBtn?.addEventListener('click', jumpToEnd);
  importBtn?.addEventListener('click', importGames);
  importToggle?.addEventListener('click', () => togglePanel(importPanel));
  filterToggle?.addEventListener('click', () => filterOverlay.classList.toggle('hidden'));
  closeFilterOverlay?.addEventListener('click', () => filterOverlay.classList.add('hidden'));
  
  // Close filter overlay when clicking outside
  document.addEventListener('click', (e) => {
    if (!filterOverlay.classList.contains('hidden') && 
        !filterOverlay.contains(e.target) && 
        e.target !== filterToggle && 
        !filterToggle.contains(e.target)) {
      filterOverlay.classList.add('hidden');
    }
  });

  // Arrow key navigation for chess moves
  document.addEventListener('keydown', (e) => {
    // Close filter overlay on Escape
    if (e.key === 'Escape' && !filterOverlay.classList.contains('hidden')) {
      filterOverlay.classList.add('hidden');
      return;
    }
    
    // Ignore if user is typing in an input field
    const tagName = e.target.tagName.toLowerCase();
    if (tagName === 'input' || tagName === 'textarea' || tagName === 'select') return;
    
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
