// Simple in-browser explorer that calls the Python backend for move stats.
(function () {
  const boardEl = document.getElementById('board');
  const boardPanel = document.querySelector('.board-panel');
  const statusEl = document.getElementById('statusText');
  const pathEl = document.getElementById('pathTrail');
  const openingEl = document.getElementById('openingDisplay');
  const statsEl = document.getElementById('stats');
  const nextMovesEl = document.getElementById('nextMoves');
  const sidePanel = document.querySelector('.side');
  const applyBtn = document.getElementById('applyFilters');
  const toStartBtn = document.getElementById('toStartBtn');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const toEndBtn = document.getElementById('toEndBtn');
  const flipBtn = document.getElementById('flipBtn');
  // const importBtn = document.getElementById('importBtn');
  // const importStatusEl = document.getElementById('importStatus');
  // const importUsernameEl = document.getElementById('importUsername');
  // const importToggle = document.getElementById('importToggle');
  const filterToggle = document.getElementById('filterToggle');
  // const importPanel = document.getElementById('importPanel');
  const filterOverlay = document.getElementById('filterOverlay');
  const closeFilterOverlay = document.getElementById('closeFilterOverlay');
  const importOverlay = document.getElementById('importOverlay');
  const closeImportOverlay = document.getElementById('closeImportOverlay');
  const importSource = document.getElementById('importSource');
  const importUsername = document.getElementById('importUsername');
  const startImportBtn = document.getElementById('startImport');

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
  const importPlayerBtn = document.getElementById('importPlayerBtn');

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
  let fetchDebounceTimer = null;
  let currentFetchController = null;
  let openingsDatabase = [];
  let openingsDatabaseLoaded = false;

  // Fetch comprehensive opening database from Lichess
  async function loadOpeningsDatabase() {
    try {
      statusEl.textContent = 'Loading openings database…';
      statusEl.className = 'status loading';
      
      const files = ['a', 'b', 'c', 'd', 'e'];
      const fetchPromises = files.map(letter => 
        fetch(`https://raw.githubusercontent.com/lichess-org/chess-openings/master/${letter}.tsv`)
          .then(res => res.text())
      );
      
      const allTexts = await Promise.all(fetchPromises);
      
      openingsDatabase = [];
      for (const text of allTexts) {
        const lines = text.split('\n');
        
        for (let i = 1; i < lines.length; i++) { // Skip header
          const line = lines[i].trim();
          if (!line) continue;
          
          const [eco, name, pgn] = line.split('\t');
          if (!eco || !name || !pgn) continue;
          
          // Convert PGN to SAN array
          const moves = pgn
            .replace(/\d+\.\s*/g, '') // Remove move numbers
            .split(/\s+/)
            .filter(m => m && !m.includes('*'));
          
          openingsDatabase.push({ eco, name, moves });
        }
      }
      
      // Sort by move count (longest first) for better matching
      openingsDatabase.sort((a, b) => b.moves.length - a.moves.length);
      openingsDatabaseLoaded = true;
      console.log(`Loaded ${openingsDatabase.length} openings from database`);
    } catch (err) {
      console.error('Failed to load openings database:', err);
      openingsDatabaseLoaded = false;
    }
  }

  function detectOpening(moves) {
    if (!moves || moves.length === 0 || !openingsDatabaseLoaded) return null;
    
    // Find the longest matching opening
    for (const opening of openingsDatabase) {
      if (opening.moves.length > moves.length) continue;
      
      let matches = true;
      for (let i = 0; i < opening.moves.length; i++) {
        if (moves[i] !== opening.moves[i]) {
          matches = false;
          break;
        }
      }
      
      if (matches) {
        return opening;
      }
    }
    
    return null;
  }

  function updateOpeningDisplay() {
    const currentMoves = currentPath();
    const opening = detectOpening(currentMoves);
    
    if (opening) {
      openingEl.innerHTML = `${opening.name} <span class="eco-code">${opening.eco}</span>`;
      openingEl.classList.add('visible');
    } else if (currentMoves.length > 0) {
      openingEl.innerHTML = 'Starting Position';
      openingEl.classList.add('visible');
    } else {
      openingEl.innerHTML = 'Starting Position';
      openingEl.classList.add('visible');
    }
  }

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
      pathEl.innerHTML = '<span style="color: var(--sub); font-style: italic;">No Moves Have Been Made</span>';
      updateOpeningDisplay();
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
    updateOpeningDisplay();
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
      
      loadedPlayers.forEach((playerInfo) => {
        const p = typeof playerInfo === 'string' ? playerInfo : playerInfo.name;
        const source = typeof playerInfo === 'object' ? playerInfo.source : 'legacy';
        
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
        
        // Add source icon
        const iconSpan = document.createElement('span');
        iconSpan.className = 'player-source-icon';
        if (source === 'chess.com') {
          // Chess.com official logo style
          iconSpan.innerHTML = '<svg width="16" height="16" viewBox="0 0 64 64" fill="none"><rect width="64" height="64" rx="12" fill="#7fa650"/><rect x="8" y="8" width="48" height="48" rx="4" fill="#fff"/><rect x="12" y="12" width="8" height="8" fill="#7fa650"/><rect x="28" y="12" width="8" height="8" fill="#7fa650"/><rect x="44" y="12" width="8" height="8" fill="#7fa650"/><rect x="20" y="20" width="8" height="8" fill="#7fa650"/><rect x="36" y="20" width="8" height="8" fill="#7fa650"/><rect x="12" y="28" width="8" height="8" fill="#7fa650"/><rect x="28" y="28" width="8" height="8" fill="#7fa650"/><rect x="44" y="28" width="8" height="8" fill="#7fa650"/><rect x="20" y="36" width="8" height="8" fill="#7fa650"/><rect x="36" y="36" width="8" height="8" fill="#7fa650"/><rect x="12" y="44" width="8" height="8" fill="#7fa650"/><rect x="28" y="44" width="8" height="8" fill="#7fa650"/><rect x="44" y="44" width="8" height="8" fill="#7fa650"/></svg>';
          iconSpan.title = 'Chess.com';
        } else if (source === 'lichess') {
          // Lichess official logo - horse knight
          iconSpan.innerHTML = '<svg width="16" height="16" viewBox="0 0 64 64" fill="none"><rect width="64" height="64" rx="12" fill="#000"/><path d="M38 8c-5.5 0-10 4.5-10 10 0 2.2.7 4.25 1.95 5.95-3.2 1.8-5.45 5-5.45 8.8 0 5.05 3.75 9.2 8.5 9.95v4.05c-6.5 1.2-11.5 6.8-11.5 13.5 0 1.7.3 3.3.85 4.8H51.5c.55-1.5.85-3.1.85-4.8 0-6.7-5-12.3-11.5-13.5V42.7c4.75-.75 8.5-4.9 8.5-9.95 0-3.8-2.25-7-5.45-8.8A9.96 9.96 0 0 0 45.5 18c0-5.5-4.5-10-10-10-2.5 0-4.75.9-6.5 2.4zm-6.5 4.5 2.5 3.5L32 18.5l2-2.5z" fill="#fff"/></svg>';
          iconSpan.title = 'Lichess';
        }
        
        label.appendChild(checkbox);
        label.appendChild(span);
        if (source === 'chess.com' || source === 'lichess') {
          label.appendChild(iconSpan);
        }
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
    // Cancel any pending fetch
    if (currentFetchController) {
      currentFetchController.abort();
    }
    
    currentFetchController = new AbortController();
    const signal = currentFetchController.signal;
    
    const payload = lastPayload || gatherFilters();
    payload.path = currentPath();
    statusEl.textContent = 'Loading…';
    statusEl.className = 'status loading';
    try {
      const res = await fetch('/api/next-moves', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: signal,
      });
      if (!res.ok) throw new Error(`Request failed: ${res.status}`);
      const data = await res.json();
      updateUI(data);
    } catch (err) {
      if (err.name === 'AbortError') {
        // Request was cancelled, ignore
        return;
      }
      console.error(err);
      statusEl.textContent = 'Backend unavailable — ensure serve_frontend.py is running.';
      statusEl.className = 'status';
    } finally {
      currentFetchController = null;
    }
  }

  function debouncedFetchNextMoves(immediate = false) {
    // Clear any pending debounced call
    if (fetchDebounceTimer) {
      clearTimeout(fetchDebounceTimer);
      fetchDebounceTimer = null;
    }
    
    if (immediate) {
      fetchNextMoves();
    } else {
      // Set status immediately to show we're loading
      statusEl.textContent = 'Loading…';
      statusEl.className = 'status loading';
      
      // Debounce the actual fetch
      fetchDebounceTimer = setTimeout(() => {
        fetchDebounceTimer = null;
        fetchNextMoves();
      }, 150);
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
    debouncedFetchNextMoves();
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
    debouncedFetchNextMoves();
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
    debouncedFetchNextMoves();
  }

  function resetBoard() {
    chess.reset();
    pathSAN = [];
    cursor = 0;
    board.start();
    updatePathDisplay();
    debouncedFetchNextMoves();
  }

  function redoMove() {
    if (cursor >= pathSAN.length) return;
    cursor += 1;
    rebuildPosition();
    debouncedFetchNextMoves();
  }

  function jumpToStart() {
    cursor = 0;
    rebuildPosition();
    debouncedFetchNextMoves();
  }

  function jumpToEnd() {
    cursor = pathSAN.length;
    rebuildPosition();
    debouncedFetchNextMoves();
  }

  // function togglePanel(panel) {
  //   panel.classList.toggle('hidden');
  // }

  /* async function importGames() {
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
      debouncedFetchNextMoves(true);
    } catch (err) {
      importStatusEl.textContent = 'Import failed (network).';
      importStatusEl.className = 'status';
      console.error(err);
    }
  } */

  async function importNewPlayer() {
    const username = importUsername?.value?.trim();
    const source = importSource?.value || 'chess.com';
    
    if (!username) {
      alert('Please enter a username');
      return;
    }
    
    statusEl.textContent = `Importing ${username} from ${source}...`;
    statusEl.className = 'status loading';
    
    // Close the overlays
    importOverlay?.classList.add('hidden');
    playerDropdown?.classList.add('hidden');
    playerSelectBtn?.classList.remove('open');
    
    try {
      const res = await fetch('/api/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, player: username, source }),
      });
      const data = await res.json();
      
      if (!res.ok || data.error) {
        statusEl.textContent = data.error || `Import failed (${res.status})`;
        statusEl.className = 'status';
        alert(`Import failed: ${data.error || 'Unknown error'}`);
        return;
      }
      
      const sourceLabel = source === 'lichess' ? 'Lichess' : 'Chess.com';
      statusEl.textContent = `Imported ${data.imported} new games (total ${data.total}) for ${username} from ${sourceLabel}`;
      statusEl.className = 'status';
      
      // Clear the username field
      if (importUsername) importUsername.value = '';
      
      // Refresh player list and reset view
      await fetchPlayers();
      pathSAN = [];
      cursor = 0;
      chess.reset();
      board.start();
      updatePathDisplay();
      lastPayload = null;
      debouncedFetchNextMoves(true);
      
      // Auto-select the newly imported player
      setTimeout(() => {
        const newPlayerCheckbox = Array.from(playerCheckboxList?.querySelectorAll('input[type="checkbox"]') || [])
          .find(cb => cb.value === username);
        if (newPlayerCheckbox) {
          allPlayersCheckbox.checked = false;
          playerCheckboxList?.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
          });
          newPlayerCheckbox.checked = true;
          updatePlayerLabel();
          handlePlayerCheckboxChange({ target: newPlayerCheckbox });
        }
      }, 500);
    } catch (err) {
      statusEl.textContent = 'Import failed (network error)';
      statusEl.className = 'status';
      alert('Import failed: Network error');
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
    debouncedFetchNextMoves(true);
  }

  applyBtn.addEventListener('click', () => {
    gatherFilters();
    debouncedFetchNextMoves(true);
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
    debouncedFetchNextMoves(true);
  });

  importPlayerBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    // Close player dropdown and open import overlay
    playerDropdown?.classList.add('hidden');
    playerSelectBtn?.classList.remove('open');
    importOverlay?.classList.remove('hidden');
  });

  startImportBtn?.addEventListener('click', () => {
    importNewPlayer();
  });

  closeImportOverlay?.addEventListener('click', () => {
    importOverlay?.classList.add('hidden');
  });

  // Allow Enter key in username field to trigger import
  importUsername?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      importNewPlayer();
    }
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

  // Prevent import overlay from closing when clicking inside it
  importOverlay?.addEventListener('click', (e) => {
    e.stopPropagation();
  });

  // Close dropdown when clicking outside
  document.addEventListener('click', (e) => {
    if (!playerDropdown?.contains(e.target) && 
        e.target !== playerSelectBtn && 
        !playerSelectBtn?.contains(e.target) &&
        e.target !== refreshPlayersBtn &&
        !refreshPlayersBtn?.contains(e.target)) {
      playerDropdown?.classList.add('hidden');
      playerSelectBtn?.classList.remove('open');
    }
  });

  toStartBtn?.addEventListener('click', jumpToStart);
  prevBtn?.addEventListener('click', undoMove);
  nextBtn?.addEventListener('click', redoMove);
  toEndBtn?.addEventListener('click', jumpToEnd);
  flipBtn?.addEventListener('click', () => board.flip());
  // importBtn?.addEventListener('click', importGames);
  // importToggle?.addEventListener('click', () => togglePanel(importPanel));
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
    
    // Close import overlay when clicking outside
    if (!importOverlay?.classList.contains('hidden') && 
        !importOverlay.contains(e.target)) {
      importOverlay.classList.add('hidden');
    }
  });

  // Arrow key navigation for chess moves
  document.addEventListener('keydown', (e) => {
    // Close overlays on Escape
    if (e.key === 'Escape') {
      if (!filterOverlay.classList.contains('hidden')) {
        filterOverlay.classList.add('hidden');
        return;
      }
      if (!importOverlay?.classList.contains('hidden')) {
        importOverlay.classList.add('hidden');
        return;
      }
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
      case 'f':
      case 'F':
        e.preventDefault();
        board.flip();
        break;
    }
  });

  // Kick things off
  Promise.all([
    loadOpeningsDatabase(),
    fetchPlayers()
  ]).then(() => {
    gatherFilters();
    debouncedFetchNextMoves(true);
  });
})();
