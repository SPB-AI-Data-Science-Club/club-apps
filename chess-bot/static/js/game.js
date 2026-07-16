/* SPB Chess Bot - Game Logic */
'use strict';

let board = null;
let game  = new Chess();

let state = {
  elo:         1600,
  playerColor: 'white',
  active:      false,
  busy:        false,   // true while engine is computing — blocks all moves
  moveHistory: [],
  hintSquare:  null,
};

// ── DOM refs ──────────────────────────────────────────────────────────
const $status      = $('#statusText');
const $moveList    = $('#moveList');
const $eloDisplay  = $('#eloDisplay');
const $ingame      = $('#ingameControls');
const $setup       = $('#setupSection');
const $modal       = $('#modalOverlay');
const $modalTitle  = $('#modalTitle');
const $modalSub    = $('#modalSub');

// ── Highlight helpers ─────────────────────────────────────────────────
function removeHighlights() {
  $('#chessboard .square-55d63').removeClass('highlight-move hint-square');
}

function highlightMove(from, to) {
  removeHighlights();
  $(`#chessboard .square-${from}`).addClass('highlight-move');
  $(`#chessboard .square-${to}`).addClass('highlight-move');
}

function showHint(square) {
  removeHighlights();
  $(`#chessboard .square-${square}`).addClass('hint-square');
  state.hintSquare = square;
}

// ── Board config ──────────────────────────────────────────────────────
function boardConfig() {
  return {
    draggable:     true,
    position:      'start',
    orientation:   state.playerColor === 'white' ? 'white' : 'black',
    pieceTheme:    'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
    onDragStart:   onDragStart,
    onDrop:        onDrop,
    onSnapEnd:     () => board.position(game.fen()),
  };
}

function onDragStart(source, piece) {
  // Block drag if game not active, engine is thinking, or it's not our turn
  if (!state.active || state.busy) return false;
  if (game.game_over())            return false;
  const myColor = state.playerColor === 'white' ? 'w' : 'b';
  if (game.turn() !== myColor)     return false;
  if (piece.charAt(0) !== myColor) return false;
  removeHighlights();
  return true;
}

function onDrop(source, target) {
  if (!state.active || state.busy) return 'snapback';

  const fenBefore = game.fen();  // FEN before player's move (what server needs)
  const move = game.move({ from: source, to: target, promotion: 'q' });
  if (move) updateCaptures();
  if (move === null) return 'snapback';

  highlightMove(source, target);
  addMoveToHistory(move.san, false);   // false = player's move
  setBusy(true);

  if (game.game_over()) {
    setBusy(false);
    const [winner, reason] = clientOutcome();
    if (winner) updateEvalBar(winner === 'White' ? 10000 : -10000);
    handleGameOver(winner, reason);
    return;
  }

  fetch('/api/move', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fen: fenBefore, move: source + target, elo: state.elo }),
  })
  .then(r => {
    if (!r.ok) throw new Error('Server error ' + r.status);
    return r.json();
  })
  .then(data => {
    if (data.error) throw new Error(data.error);

    game.load(data.fen);
    board.position(data.fen, true);   // animated slide
    updateCaptures();
    updateEvalBar(data.eval_cp);

    if (data.engine_move) {
      const from = data.engine_move.slice(0, 2);
      const to   = data.engine_move.slice(2, 4);
      highlightMove(from, to);
      // Use engine_san returned from server (game.history() is empty after load())
      addMoveToHistory(data.engine_san || data.engine_move, true);   // true = engine's move
    }

    setBusy(false);

    if (data.game_over) {
      handleGameOver(data.winner, data.reason);
    }
  })
  .catch(err => {
    console.error('Engine error:', err);
    setBusy(false);
    updateStatus('error');
  });
}


// ── Captured pieces + material tracker (chess.com style) ─────────────
const PIECE_VALUES = { p: 1, n: 3, b: 3, r: 5, q: 9 };
const INITIAL_COUNTS = { p: 8, n: 2, b: 2, r: 2, q: 1 };
const GLYPHS = {
  w: { p: '\u2659', n: '\u2658', b: '\u2657', r: '\u2656', q: '\u2655' },
  b: { p: '\u265F', n: '\u265E', b: '\u265D', r: '\u265C', q: '\u265B' },
};

function countPieces(fen) {
  const placement = fen.split(' ')[0];
  const counts = { w: { p:0,n:0,b:0,r:0,q:0 }, b: { p:0,n:0,b:0,r:0,q:0 } };
  for (const ch of placement) {
    const lower = ch.toLowerCase();
    if (PIECE_VALUES[lower] !== undefined) {
      counts[ch === lower ? 'b' : 'w'][lower]++;
    }
  }
  return counts;
}

// Pieces of `color` that have left the board (captured by the opponent)
function capturedFrom(counts, color) {
  const out = [];
  let value = 0;
  for (const t of ['p', 'n', 'b', 'r', 'q']) {
    const taken = INITIAL_COUNTS[t] - counts[color][t];
    for (let i = 0; i < taken; i++) out.push(GLYPHS[color][t]);
    if (taken > 0) value += taken * PIECE_VALUES[t];
  }
  return { glyphs: out.join(''), value };
}

function updateCaptures() {
  const counts = countPieces(game.fen());
  const byWhite = capturedFrom(counts, 'b');   // white has taken these black pieces
  const byBlack = capturedFrom(counts, 'w');
  const diff = byWhite.value - byBlack.value;  // >0 means white leads on material

  // Bottom bar is always the player, top bar the engine
  const playerIsWhite = state.playerColor === 'white';
  const bottom = playerIsWhite ? byWhite : byBlack;
  const top    = playerIsWhite ? byBlack : byWhite;
  const bottomLead = playerIsWhite ? diff : -diff;

  $('#capBotName').text('You');
  $('#capTopName').text('Stockfish');
  $('#capBotPieces').html(bottom.glyphs || '<span class="cap-none">no captures</span>');
  $('#capTopPieces').html(top.glyphs || '<span class="cap-none">no captures</span>');
  $('#capBotScore').text(bottomLead > 0 ? '+' + bottomLead : '');
  $('#capTopScore').text(bottomLead < 0 ? '+' + (-bottomLead) : '');
}

// ── Busy state (engine thinking) ──────────────────────────────────────
function setBusy(busy) {
  state.busy = busy;
  if (busy) {
    updateStatus('thinking');
    $('#hintBtn').prop('disabled', true);
  } else {
    updateStatus('your_turn');
    $('#hintBtn').prop('disabled', false);
  }
}


// ── ELO slider ────────────────────────────────────────────────────────
const ELO_TIERS = [
  [400,  'Beginner',       'Most moves are selected randomly at this level.'],
  [800,  'Casual',         'The engine makes frequent inaccuracies and occasional blunders.'],
  [1200, 'Improver',       'Reasonable moves with regular mistakes.'],
  [1600, 'Club Player',    'Calibrated engine strength typical of a club player.'],
  [2000, 'Tournament',     'Strong play that punishes inaccuracies.'],
  [2400, 'Master',         'Very few mistakes at this level.'],
  [3000, 'Grandmaster',    'Close to the engine\'s full playing strength.'],
  [3600, 'Full Strength',  'No strength limit is applied.'],
];

function eloTier(elo) {
  let tier = ELO_TIERS[0];
  for (const t of ELO_TIERS) if (elo >= t[0] - 200) tier = t;
  return tier;
}

function updateEloLabel() {
  const elo  = parseInt($('#eloSlider').val(), 10);
  const tier = eloTier(elo);
  $('#eloValue').text(elo);
  $('#eloName').text(tier[1]);
  $('#eloDesc').text(tier[2]);
}
$('#eloSlider').on('input', updateEloLabel);
updateEloLabel();

// ── Eval bar (white-POV centipawns -> bar share) ──────────────────────
function updateEvalBar(cp) {
  if (typeof cp !== 'number') return;
  // Logistic squash: +-1000cp maps to ~92/8 split
  const share = 100 / (1 + Math.pow(10, -cp / 800));
  const fromBottom = state.playerColor === 'white' ? share : 100 - share;
  $('#evalWhite').css('height', fromBottom.toFixed(1) + '%');
  const pawns = Math.abs(cp) >= 9500 ? 'M' : (cp / 100).toFixed(1).replace('-', '');
  $('#evalLabel').text(pawns).toggleClass('eval-black-lead', cp < 0);
}

// ── Status ────────────────────────────────────────────────────────────
function updateStatus(s) {
  const map = {
    your_turn: 'Your turn',
    thinking:  '<span class="thinking">Engine thinking...</span>',
    error:     '<span class="status-error">Engine error - try again</span>',
    starting:  'Starting...',
  };
  $status.html(map[s] || s);
}

// ── Move history ──────────────────────────────────────────────────────
function addMoveToHistory(san, isEngine) {
  state.moveHistory.push({ san, isEngine });
  renderMoveHistory();
}

function renderMoveHistory() {
  if (state.moveHistory.length === 0) {
    $moveList.html('<div class="no-moves">No moves yet</div>');
    return;
  }

  const moves = state.moveHistory;
  let html = '';

  for (let i = 0; i < moves.length; i += 2) {
    const num  = Math.floor(i / 2) + 1;
    const a    = moves[i];
    const b    = moves[i + 1];
    // White column = first of pair, Black column = second
    const wSan = a ? `<span class="move-white">${a.san}</span>` : '';
    const bSan = b ? `<span class="move-black">${b.san}</span>` : '';
    html += `<div class="move-pair"><span class="move-num">${num}.</span>${wSan}${bSan}</div>`;
  }

  $moveList.html(html);
  $moveList[0].scrollTop = $moveList[0].scrollHeight;
}


// Outcome of the current chess.js position. After a game-ending move the
// side to move is the one with no escape, so on checkmate the OTHER side won.
function clientOutcome() {
  if (game.in_checkmate()) {
    return [game.turn() === 'w' ? 'Black' : 'White', 'checkmate'];
  }
  if (game.in_stalemate())              return [null, 'stalemate'];
  if (game.insufficient_material())     return [null, 'insufficient material'];
  if (game.in_threefold_repetition())   return [null, 'threefold repetition'];
  return [null, 'the fifty-move rule'];
}

// ── Game Over ─────────────────────────────────────────────────────────
function handleGameOver(winner, reason) {
  state.active = false;
  state.busy   = false;

  let title, sub;
  if (winner === 'White' || winner === 'Black') {
    const youWon = (winner.toLowerCase() === state.playerColor);
    title = youWon ? 'You Win!' : 'Stockfish Wins';
    sub   = `${youWon ? 'You win' : 'Stockfish wins'} by ${reason || 'resignation'}.`;
  } else {
    title = 'Draw';
    sub   = `Draw by ${reason || 'agreement'}.`;
  }

  $modalTitle.text(title);
  $modalSub.text(sub);
  $status.html(`<span>${title === 'Draw' ? 'Draw' : title} - ${reason || ''}</span>`);
  $modal.removeClass('hidden');
}

// ── Show setup screen ─────────────────────────────────────────────────
function showSetup() {
  state.active = false;
  state.busy   = false;
  state.moveHistory = [];

  $modal.addClass('hidden');
  $ingame.addClass('hidden');
  $setup.removeClass('hidden');

  renderMoveHistory();
  game = new Chess();
  board = Chessboard('chessboard', {
    position:   'start',
    pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
    orientation: 'white',
  });
}

// ── Start Game ────────────────────────────────────────────────────────
function startGame() {
  state.elo         = parseInt($('#eloSlider').val(), 10) || 1600;
  state.playerColor = $('.color-btn.active').data('color') || 'white';
  state.moveHistory = [];
  state.active      = false;
  state.busy        = false;

  renderMoveHistory();
  $modal.addClass('hidden');
  $setup.addClass('hidden');            // Hide difficulty/color/start during game
  $ingame.removeClass('hidden');        // Show status/hint/new-game during game
  $eloDisplay.text(`Stockfish ${state.elo} - you play ${state.playerColor}`);
  updateStatus('starting');

  board = Chessboard('chessboard', boardConfig());
  game  = new Chess();

  fetch('/api/new_game', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ elo: state.elo, color: state.playerColor }),
  })
  .then(r => {
    if (!r.ok) throw new Error('Server error ' + r.status);
    return r.json();
  })
  .then(data => {
    if (data.error) throw new Error(data.error);

    game.load(data.fen);
    updateCaptures();
    updateEvalBar(data.eval_cp);
    board.position(data.fen);
    state.active = true;

    if (data.engine_move) {
      // Engine moved first (player plays black)
      const from = data.engine_move.slice(0, 2);
      const to   = data.engine_move.slice(2, 4);
      highlightMove(from, to);
      // Use engine_san from server — game.history() is empty after load()
      addMoveToHistory(data.engine_san || data.engine_move, true);
    }

    updateStatus('your_turn');
  })
  .catch(err => {
    console.error('Start game error:', err);
    updateStatus('error');
  });
}

// ── Hint ──────────────────────────────────────────────────────────────
$('#hintBtn').on('click', () => {
  if (!state.active || state.busy) return;
  $('#hintBtn').prop('disabled', true);
  fetch('/api/hint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fen: game.fen() }),
  })
  .then(r => r.json())
  .then(data => {
    if (data.hint) showHint(data.hint.slice(0, 2));
    $('#hintBtn').prop('disabled', false);
  })
  .catch(() => { $('#hintBtn').prop('disabled', false); });
});

// ── Event Listeners ───────────────────────────────────────────────────
$('#eloGrid').on('click', '.elo-btn', function() {
  $('.elo-btn').removeClass('active');
  $(this).addClass('active');
});

$('.color-toggle').on('click', '.color-btn', function() {
  $('.color-btn').removeClass('active');
  $(this).addClass('active');
});

$('#startBtn').on('click', startGame);
$('#newGameBtn').on('click', showSetup);    // "New Game" during game -> back to setup
$('#modalNewGame').on('click', startGame);  // "Play Again" modal -> restart same settings
$('#modalSetup').on('click', showSetup);    // "Change Settings" modal -> back to setup

// ── Init ──────────────────────────────────────────────────────────────
$(function() {
  board = Chessboard('chessboard', {
    position:   'start',
    pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
    orientation: 'white',
  });
});
/* init captures on load */
updateCaptures();

// Mobile: while a game is active, touches that start on the board must
// drag pieces, never scroll the page (covers older browsers where
// touch-action alone is not enough).
document.addEventListener('touchmove', function(e) {
  if (state.active && e.target.closest && e.target.closest('#chessboard')) {
    e.preventDefault();
  }
}, { passive: false });
