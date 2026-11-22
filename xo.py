import unicodedata

from itertools import combinations
from functools import lru_cache
from random import choice, sample, shuffle
from time import monotonic

from collections import defaultdict

from xo_careers import CAREERS
from xo_data import CLUES, EXPANSION, POOLS, clue_image

TURN_SECONDS = 30
SIZES = (3, 4, 5)


def normalize(name):
    return "".join(c for c in unicodedata.normalize("NFKD", name.casefold()) if c.isalnum())


# Each clue has its own evidence set: club appearance, senior teammate,
# or coached player. Existing curated answers establish both relationships.
names_by_key = {}
players_by_clue = defaultdict(set)


def add_fact(clue, name):
    identity = normalize(name)
    names_by_key.setdefault(identity, name)
    if CLUES[clue][2] != "player" or identity != normalize(CLUES[clue][0]):
        players_by_clue[clue].add(identity)


for clue, names in CAREERS.items():
    for name in names.split("|"):
        add_fact(clue, name)

for columns, rows in POOLS:
    for row, answers in rows.items():
        for column, names in zip(columns, answers, strict=True):
            for name in filter(None, names.split("|")):
                add_fact(row, name)
                add_fact(column, name)

for clue, record in EXPANSION.items():
    for name in record["members"]:
        add_fact(clue, name)

# Being teammates is reciprocal. Add the reverse fact when the answer also
# appears as a player clue. Sharing an opponent never creates a link.
player_clues = {normalize(name): key for key, (name, _, kind) in CLUES.items() if kind == "player"}
for identity, clue in player_clues.items():
    for teammate in list(players_by_clue[clue]):
        if teammate in player_clues:
            add_fact(player_clues[teammate], CLUES[clue][0])

CONNECTIONS = {}
for left, right in combinations(CLUES, 2):
    matches = players_by_clue[left] & players_by_clue[right]
    if matches:
        CONNECTIONS[frozenset((left, right))] = {names_by_key[key] for key in matches}

PLAYERS = sorted(names_by_key.values())
ALL_ROWS = tuple(key for key, (_, _, kind) in CLUES.items() if kind != "player")
ALL_COLUMNS = tuple(key for key, (_, _, kind) in CLUES.items() if kind != "coach")


NEIGHBOURS = {
    row: {col for col in ALL_COLUMNS if frozenset((row, col)) in CONNECTIONS}
    for row in ALL_ROWS
}
PICTURE_PLAYERS = tuple(key for key in ALL_COLUMNS if CLUES[key][2] == "player")
COACH_KEYS = {key for key in ALL_ROWS if CLUES[key][2] == "coach"}


def candidate_layout(size, player, fixed_row=None):
    eligible = [row for row in ALL_ROWS if player in NEIGHBOURS[row] and len(NEIGHBOURS[row]) >= size]
    rows = [fixed_row] if fixed_row is not None else []
    columns = NEIGHBOURS[fixed_row].copy() if fixed_row is not None else set(ALL_COLUMNS)
    while len(rows) < size:
        choices = [row for row in eligible if row not in rows and
                   (COACH_KEYS.intersection(rows) or row in COACH_KEYS) and
                   len((columns & NEIGHBOURS[row]) - set((*rows, row))) >= size]
        if not choices:
            return None
        selected = choice(choices)
        rows.append(selected)
        columns.intersection_update(NEIGHBOURS[selected])
        columns.discard(selected)
    extras = sample(tuple(columns - {player}), size - 1)
    return tuple(rows), (player, *extras)


@lru_cache(maxsize=len(SIZES))
def layouts(size):
    boards = {}
    covered = set()
    for attempt in range(40000):
        player = PICTURE_PLAYERS[attempt % len(PICTURE_PLAYERS)]
        uncovered_rows = [row for row in ALL_ROWS if row not in covered and player in NEIGHBOURS[row]]
        fixed = choice(uncovered_rows) if uncovered_rows and attempt % 2 == 0 else None
        board = candidate_layout(size, player, fixed)
        if board:
            rows, cols = board
            clue_set = frozenset((*rows, *cols))
            boards.setdefault(clue_set, board)
            covered.update(clue_set)
            if len(boards) >= 5000:
                break
    return tuple(boards.values())


DECKS = {}
LAST_BOARDS = {}


def draw_board(size):
    deck = DECKS.setdefault(size, [])
    if not deck:
        deck.extend(layouts(size))
        shuffle(deck)
        recent = LAST_BOARDS.get(size, ())
        for i in range(min(2, len(deck))):
            target = len(deck) - 1 - i
            if deck[target] in recent:
                replacement = next(j for j in range(target) if deck[j] not in recent)
                deck[target], deck[replacement] = deck[replacement], deck[target]
    board = deck.pop()
    LAST_BOARDS[size] = (board, *LAST_BOARDS.get(size, ())[:1])
    return board


@lru_cache(maxsize=len(SIZES))
def winning_lines(size):
    rows = [tuple(r * size + c for c in range(size)) for r in range(size)]
    columns = list(zip(*rows))
    diagonals = [tuple(r * size + c for r, c in enumerate(diagonal))
                 for diagonal in (range(size), range(size - 1, -1, -1))]
    return (*rows, *columns, *diagonals)


ALIASES = {"messi":"Lionel Messi", "zlatan":"Zlatan Ibrahimović", "ibrahimovic":"Zlatan Ibrahimović",
           "cesc":"Cesc Fàbregas", "fabregas":"Cesc Fàbregas", "reyes":"José Antonio Reyes", "vin":"Vinícius Júnior",
           "vini":"Vinícius Júnior", "vinijr":"Vinícius Júnior", "vinicius":"Vinícius Júnior"}


class Match:
    def __init__(self, names, solo=False, size=3, revision=0, now=None):
        self.size = size
        rows, columns = draw_board(size)
        self.rows = sample(rows, size)
        self.columns = sample(columns, size)
        self.answers = [sorted(CONNECTIONS[frozenset((r, c))]) for r in self.rows for c in self.columns]
        self.names = names
        self.solo = solo
        self.cells = [None] * (size * size)
        self.turn = 0
        self.revision = revision
        self.winner = None
        self.line = ()
        self.revealed = False
        self.lives = 3 if solo else None
        self.end_vote = None
        self.notice = ""
        self.deadline = None if solo else (monotonic() if now is None else now) + TURN_SECONDS

    @property
    def lost(self):
        return self.solo and self.lives == 0

    @property
    def finished(self):
        return self.winner is not None or all(self.cells) or self.revealed or self.lost

    def tick(self, now):
        if not self.solo and not self.finished and now >= self.deadline:
            self.advance(now, "Time ran out. Turn passed.")

    def advance(self, now, notice="", keep_vote=False):
        self.turn = 1 - self.turn
        self.deadline = now + TURN_SECONDS
        self.revision += 1
        self.notice = notice
        if not keep_vote:
            self.end_vote = None

    def vote_to_end(self, team, now):
        if self.end_vote is not None and self.end_vote != team:
            return Match(self.names, size=self.size, revision=self.revision + 1, now=now)
        self.end_vote = team
        self.advance(now, keep_vote=True)
        return self

    def play(self, team, cell, guess, now):
        if self.finished or team != self.turn or self.cells[cell]:
            return "That square is unavailable."
        key = normalize(guess)
        key = normalize(ALIASES.get(key, key))
        players = self.answers[cell]
        exact = next((name for name in PLAYERS if normalize(name) == key), None)
        if exact:
            matches = [exact] if exact in players else []
        else:
            candidates = [name for name in PLAYERS if key and normalize(name.split()[-1]) == key]
            if len(candidates) > 1:
                return "Several players share that name. Pick a full name."
            matches = [name for name in candidates if name in players]
        if len(matches) != 1:
            if self.solo:
                self.lives -= 1
                self.revision += 1
                return "Wrong guess. No lives left." if self.lost else "Wrong guess. You lost a life."
            self.advance(now, "That name wasn’t accepted. Turn passed.")
            return self.notice
        self.cells[cell] = {"team": team, "player": matches[0]}
        if self.solo:
            self.revision += 1
        else:
            self.line = next((line for line in winning_lines(self.size)
                              if all(self.cells[i] and self.cells[i]["team"] == team for i in line)), ())
            if self.line or all(self.cells):
                self.winner = team if self.line else None
                self.end_vote = None
                self.notice = ""
                self.revision += 1
            else:
                self.advance(now)
        return "Square claimed."

    def view(self, team, now=None):
        def clues(keys):
            return [dict(name=CLUES[key][0], ar=CLUES[key][1], kind=CLUES[key][2],
                         image=f"/static/{clue_image(key)}")
                    for key in keys]
        return dict(rows=clues(self.rows), columns=clues(self.columns), names=self.names, solo=self.solo, team=team,
                    size=self.size, lives=self.lives, lost=self.lost, end_vote=self.end_vote, notice=self.notice,
                    remaining=max(0, self.deadline - (monotonic() if now is None else now))
                    if not self.solo and not self.finished else None,
                    cells=self.cells, turn=self.turn, revision=self.revision, winner=self.winner,
                    line=self.line, finished=self.finished, revealed=self.revealed,
                    examples=[names[0] for names in self.answers] if self.revealed else None)
