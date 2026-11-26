(() => {
const get = id => document.getElementById(id);
const endpoint = document.querySelector('.xo-page').dataset.state;
const dialog = get('entry');
const marks = ['X', 'O'];
const directory = JSON.parse(get('player-directory')?.textContent || '[]');
const translate = window.tr || ((text, ...args) => text.replace(/\{(\d+)\}/g, (match, index) => args[index] ?? match));
const isArabic = window.arabic === true;
const playerInput = get('player');
const suggestions = get('suggestions');
const displayName = clue => isArabic ? clue.ar : clue.name;
const displayPlayer = player => isArabic ? (directory.find(([name]) => name === player)?.[1] || player) : player;
const normalizeName = text => text.toLowerCase().normalize('NFKD').replace(/\p{M}/gu, '').replace(/[^\p{L}\p{N}]/gu, '');
const searchable = directory.map(([name, translated]) => ({
  name, translated,
  keys: [name, translated].flatMap(label => [normalizeName(label), ...label.split(/\s+/).map(normalizeName)])
}));
let picked = '';

function distance(left, right) {
  let previous = Array.from({length: right.length + 1}, (_, i) => i);
  for (let i = 0; i < left.length; i++) {
    const current = [i + 1];
    for (let j = 0; j < right.length; j++) {
      current.push(Math.min(previous[j + 1] + 1, current[j] + 1, previous[j] + Number(left[i] !== right[j])));
    }
    previous = current;
  }
  return previous[right.length];
}

function suggest() {
  const input = normalizeName(playerInput.value);
  const matches = input.length < 2 ? [] : searchable.map(player => {
    const score = Math.min(...player.keys.map(key =>
      key === input ? 0 : key.startsWith(input) ? 1 : key.includes(input) ? 2 :
      input.length < 4 ? Infinity : distance(input, key) + 2.5
    ));
    return {...player, score};
  }).filter(player => player.score <= (input.length >= 6 ? 4.5 : 3.5)).sort((a,b) => a.score - b.score);
  suggestions.replaceChildren(...matches.slice(0, 6).map(player => {
    const button = element('button', isArabic ? player.translated : player.name);
    button.type = 'button';
    button.addEventListener('click', () => {
      picked = player.name;
      playerInput.value = isArabic ? player.translated : player.name;
      suggestions.replaceChildren();
      playerInput.focus();
    });
    return button;
  }));
}

function picture(clue) {
  if (!clue.image) return document.createDocumentFragment();
  const image = document.createElement('img');
  image.src = clue.image;
  image.alt = '';
  image.className = 'clue-photo ' + clue.kind;
  image.onerror = () => image.remove();
  return image;
}

function rule(clue) {
  const message = {
    club: 'Played for {0}.',
    national: 'Was in the senior squad for {0}.',
    coach: 'Was coached by {0}.',
    player: 'Was a teammate of {0} at club or senior international level.'
  };
  return translate(message[clue.kind], displayName(clue));
}
let state, selected, busy = false, polling = false, rendered = '';

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function openSquare(index) {
  selected = index;
  const row = state.rows[Math.floor(index / state.size)];
  const column = state.columns[index % state.size];
  get('clues').textContent = displayName(row) + ' × ' + displayName(column);
  get('rule').textContent = rule(row) + ' ' + rule(column);
  get('guess').reset();
  picked = '';
  suggestions.replaceChildren();
  get('entry-note').textContent = '';
  dialog.showModal();
}

function isPictureBoard(board) {
  return [3, 4, 5].includes(board?.size) && [board.rows, board.columns].every(clues =>
    Array.isArray(clues) && clues.length === board.size &&
    clues.every(clue => clue && typeof clue.name === 'string' && (clue.image === null || typeof clue.image === 'string'))
  );
}

let clockEnds = null, roundEnds = null;

function formatTime(end) {
  const seconds = Math.max(0, Math.ceil((end - performance.now()) / 1000));
  return Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0');
}

function updateClock() {
  get('round-clock').textContent = roundEnds === null ? '' : (isArabic ? 'وقت الجولة ' : 'Round time ') + formatTime(roundEnds);
  if (clockEnds === null) return;
  const seconds = Math.max(0, Math.ceil((clockEnds - performance.now()) / 1000));
  get('turn-clock').textContent = translate('{0}s', seconds);
}

function takeState(board) {
  if (dialog.open && state && board.revision !== state.revision &&
      (board.finished || board.turn !== board.team || board.cells[selected])) dialog.close();
  state = board;
  clockEnds = state.remaining === null ? null : performance.now() + state.remaining * 1000;
  roundEnds = state.round_remaining == null ? null : performance.now() + state.round_remaining * 1000;
  render();
  updateClock();
}

function render() {
  get('score').textContent = state.solo ? '' : state.scores.join(':');
  get('series-info').textContent = state.solo ? '' : (isArabic ? 'الجولة ' : 'Round ') + state.round_number + ' · ' + (isArabic ? 'الأفضل من ' : 'Best of ') + state.best_of;
  get('next').hidden = state.solo || !state.finished || state.series_over || state.team !== 0;
  const status = state.series_over ? translate('{0} wins the series!', state.names[state.winner]) : state.winner !== null ? translate('{0} wins!', state.names[state.winner])
    : state.lost ? translate('Game over. No lives left.')
    : state.revealed ? translate('Example answers') : state.finished ? translate(state.solo ? 'Board complete!' : 'Draw')
    : state.solo ? translate('{0} of {1} solved', state.cells.filter(Boolean).length, state.cells.length)
    : state.turn === state.team ? translate('Your turn') : translate('{0} to play', state.names[state.turn]);
  if (get('status').textContent !== status) get('status').textContent = status;
  get('lives').hidden = !state.solo;
  if (state.solo) get('lives').textContent = translate('Lives: {0}', state.lives);
  get('turn-controls').hidden = state.solo || state.finished;
  const canAct = !state.solo && !state.finished && state.turn === state.team;
  get('pass').disabled = get('end').disabled = !canAct;
  const canSeeVote = state.end_vote !== null && !state.finished;
  get('end-vote').hidden = !canSeeVote;
  if (canSeeVote) {
    get('end-vote').textContent = translate(state.end_vote === state.team
      ? 'You voted for a new board.' : '{0} voted for a new board. Press End to agree.', state.names[state.end_vote]);
  }
  get('reveal').hidden = state.revealed || (!state.solo && !state.finished);
  get('restart').hidden = !state.solo;
  const key = JSON.stringify([state.rows, state.columns, state.cells, state.turn, state.finished, state.revealed]);
  if (key === rendered) return;
  rendered = key;
  get('seats').replaceChildren(...(state.solo ? [] : state.names.map((name, i) =>
    element('span', marks[i] + ' · ' + name, i === state.turn && !state.finished ? 'is-turn' : ''))));
  const board = get('board');
  board.closest('.xo-pitch').dataset.size = state.size;
  board.replaceChildren();
  const head = board.createTHead().insertRow();
  head.append(element('td', 'X/O', 'xo-corner'));
  for (const column of state.columns) {
    const th = element('th');
    th.append(picture(column), element('span', displayName(column), 'xo-clue-label'));
    th.scope = 'col';
    head.append(th);
  }
  const body = board.createTBody();
  state.rows.forEach((row, r) => {
    const tr = body.insertRow();
    const th = element('th');
    th.append(picture(row), element('span', displayName(row), 'xo-clue-label'));
    th.scope = 'row';
    tr.append(th);
    state.columns.forEach((column, c) => {
      const i = r * state.size + c;
      const cell = state.cells[i];
      const button = element('button', '', 'xo-square');
      button.type = 'button';
      if (cell) {
        button.classList.add('claimed', 'team-' + cell.team);
        if (!state.solo) button.append(element('strong', marks[cell.team]));
        button.append(element('span', displayPlayer(cell.player)));
      } else {
        button.append(element(state.revealed ? 'span' : 'strong', state.revealed ? displayPlayer(state.examples[i]) : '+'));
      }
      button.classList.toggle('winning', state.line.includes(i));
      button.disabled = Boolean(cell || state.finished || state.turn !== state.team);
      button.setAttribute('aria-label', displayName(row) + ' × ' + displayName(column) + (cell ? ', ' + displayPlayer(cell.player) : state.revealed ? ', ' + displayPlayer(state.examples[i]) : ''));
      button.addEventListener('click', () => openSquare(i));
      tr.insertCell().append(button);
    });
  });
}

async function update(action, fields = {}) {
  if (busy || (!action && polling)) return;
  if (action) busy = true;
  else polling = true;
  try {
    const response = await fetch(endpoint, action ? {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({action, revision: state.revision, ...fields})
    } : {cache: 'no-store'});
    if (!response.ok) throw new Error('Board unavailable');
    const next = await response.json();
    if (!isPictureBoard(next)) {
      get('status').textContent = translate('Reopen the game using the launcher in the new folder.');
      return;
    }
    if (!action && busy) return;
    if (!action && state && next.revision < state.revision) return;
    const changed = !state || next.revision !== state.revision;
    takeState(next);
    if (changed && !action) get('feedback').textContent = translate(next.notice);
    if (action === 'play' && !state.finished && dialog.open &&
        (next.message === 'Several players share that name. Pick a full name.' ||
         (state.solo && next.message !== 'Square claimed.'))) {
      get('entry-note').textContent = translate(next.message);
      get('player').select();
    } else if (action) {
      if (dialog.open) dialog.close();
      get('feedback').textContent = translate(next.message);
    } else if (dialog.open && (state.finished || state.turn !== state.team || state.cells[selected])) {
      dialog.close();
    }
  } catch {
    (dialog.open ? get('entry-note') : get('feedback')).textContent = translate('Connection interrupted. Try again.');
  } finally {
    if (action) busy = false;
    else polling = false;
  }
}

get('guess').addEventListener('submit', event => {
  event.preventDefault();
  const guess = picked || playerInput.value.trim();
  if (guess) update('play', {cell: selected, guess});
});
playerInput.addEventListener('input', () => { picked = ''; suggest(); });
get('cancel').addEventListener('click', () => dialog.close());
get('reveal').addEventListener('click', () => update('reveal'));
get('restart').addEventListener('click', () => update('restart'));
get('next').addEventListener('click', () => update('next'));
get('pass').addEventListener('click', () => update('pass'));
get('end').addEventListener('click', () => update('end'));
try {
  const initial = get('initial-board');
  if (initial) {
    const board = JSON.parse(initial.textContent);
    if (isPictureBoard(board)) {
      takeState(board);
    } else {
      update();
    }
  } else {
    update();
  }
} catch (error) {
  console.error('Could not start X/O', error);
  get('feedback').textContent = translate('Connection interrupted. Try again.');
}
setInterval(() => { if (!state || !state.solo) update(); }, 850);
setInterval(updateClock, 200);

})();
