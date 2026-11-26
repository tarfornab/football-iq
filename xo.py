import json
import unicodedata
from pathlib import Path

from itertools import combinations
from functools import lru_cache
from random import choice, sample, shuffle
from time import monotonic
from statistics import median

from collections import defaultdict

from imposter import ROSTER
from xo_careers import CAREERS
from xo_data import CLUES, EXPANSION, POOLS, clue_image

TURN_SECONDS = 30
SIZES = (3, 4, 5)


NAME_CHARACTERS = str.maketrans({"ø": "o", "ł": "l", "đ": "d", "ð": "d", "ı": "i",
                                 "ى": "ي", "ی": "ي", "ک": "ك", "ـ": None})
DISPLAY_ALIASES = {"Heung-min Son": "Son Heung-min", "Min-jae Kim": "Kim Min-jae",
                   "Andrew Cole": "Andy Cole", "Neymar Jr.": "Neymar"}


def normalize(name):
    folded = unicodedata.normalize("NFKD", name.casefold()).translate(NAME_CHARACTERS)
    return "".join(c for c in folded if c.isalnum())


# Each clue has its own evidence set: club appearance, senior teammate,
# or coached player. Existing curated answers establish both relationships.
names_by_key = {}
players_by_clue = defaultdict(set)


def add_fact(clue, name):
    name = DISPLAY_ALIASES.get(name, name)
    identity = normalize(name)
    names_by_key.setdefault(identity, name)
    if CLUES[clue][2] != "player" or identity != normalize(CLUES[clue][0]):
        players_by_clue[clue].add(identity)


# Players who shared the pitch with Mbappé against Manchester City in 2017.
# https://www.uefa.com/newsfiles/UCL/2017/2019623_LU.pdf
for name in ("Tiémoué Bakayoko", "Djibril Sidibé", "Andrea Raggi", "Jemerson", "Danijel Subašić", "Valère Germain"):
    add_fact("mbappe", name)
    add_fact("monaco", name)

# Modrić played for Mourinho at Madrid and later shared the pitch with Mbappé.
for clue in ("real", "mourinho", "mbappe", "ancelotti"):
    add_fact(clue, "Luka Modrić")

# Senior appearances for Lyon and City, and a shared France starting XI.
# https://www.mancity.com/news/mens/rayan-cherki-announcement-63885169
# https://www.uefa.com/news-media/mediaservices/informationkits/competitions/european-qualifiers/2026/match/2044310/
for clue in ("lyon", "city", "pep", "erling-haaland", "mbappe", "deschamps", "ousmane-dembele", "zidane"):
    add_fact(clue, "Rayan Cherki")

# Manchester City's senior XI against Liverpool on 9 November 2025.
# https://www.mancity.com/news/mens/manchester-city-liverpool-202526-team-news-announced-63898295
for name in ("Gianluigi Donnarumma", "Matheus Nunes", "Rúben Dias", "Joško Gvardiol",
             "Nico O’Reilly", "Nico González", "Bernardo Silva", "Phil Foden", "Jérémy Doku"):
    for clue in ("city", "pep", "erling-haaland"):
        add_fact(clue, name)

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

# A dated senior squad adds team membership, its head coach and teammates.
# Historical relationships remain available for the existing X/O clues.
current_squads = json.loads(Path(__file__).with_name("xo-current-squads.json").read_text(encoding="utf-8"))
player_clue_keys = {normalize(name): key for key, (name, _, kind) in CLUES.items() if kind == "player"}
def add_team_group(team, coach, players):
    teammates = {player_clue_keys[normalize(name)] for name in players if normalize(name) in player_clue_keys}
    for name in players:
        add_fact(team, name)
        if coach:
            add_fact(coach, name)
        for player_clue in teammates:
            add_fact(player_clue, name)


for team, squad in current_squads.items():
    coach = squad["coach"]
    CLUES.setdefault(team, (squad["name"], squad["ar"], squad["kind"]))
    CLUES.setdefault(coach["key"], (coach["name"], coach["ar"], "coach"))
    add_team_group(team, coach["key"], squad["players"])

# Match groups establish historical teammates without linking players from different eras.
# Brazil v Argentina, Copa América 2019: https://www.youtube.com/watch?v=3sl2t4vnLMk
add_team_group("brazil", None, (
    "Alisson", "Dani Alves", "Marquinhos", "Thiago Silva", "Alex Sandro",
    "Casemiro", "Arthur Melo", "Philippe Coutinho", "Everton Cebolinha", "Gabriel Jesus", "Roberto Firmino",
))
# Real Madrid v Manchester City, 2022: https://www.uefa.com/news-media/mediaservices/informationkits/competitions/uefachampionsleague/2022/match/2034663/
add_team_group("real", "ancelotti", (
    "Thibaut Courtois", "Dani Carvajal", "Éder Militão", "Nacho Fernández", "Toni Kroos",
    "Karim Benzema", "Luka Modrić", "Casemiro", "Federico Valverde", "Vinícius Júnior", "Ferland Mendy",
))
# Barcelona's starting XI on 20 March 2022.
# https://www.rtve.es/deportes/20220320/real-madrid-barcelona-clasico-liga-cronica-4/2318260.shtml
add_team_group("barcelona", None, (
    "Marc-André ter Stegen", "Ronald Araújo", "Gerard Piqué", "Eric García", "Jordi Alba",
    "Sergio Busquets", "Frenkie de Jong", "Pedri", "Ousmane Dembélé", "Pierre-Emerick Aubameyang", "Ferran Torres",
))
# https://www.uefa.com/MultimediaFiles/Download/TechnicalReport/competitions/EURO/01/86/72/05/1867205_DOWNLOAD.pdf
add_fact("pirlo", "Mario Balotelli")
for name in ("Mario Balotelli", "Eric García", "Ferran Torres"):
    add_fact("city", name)
# https://www.fcbarcelona.com/en/football/first-team/noticias/748188/ousmane-dembele-nuevo-jugador-del-fc-barcelona
add_fact("dortmund", "Ousmane Dembélé")

# Bulk appearance records include historical club, coach and same-match teammate links.
bulk = json.loads(Path(__file__).with_name("xo-bulk-connections.json").read_text(encoding="utf-8"))
for key, clue in bulk["clues"].items():
    CLUES.setdefault(key, tuple(clue))
for key, players in bulk["members"].items():
    for name in players:
        add_fact(key, name)

# Tournament call-ups establish membership. Actual appearances establish
# teammates and coaching links in the same match.
national_history = json.loads(Path(__file__).with_name("xo-national-history.json").read_text(encoding="utf-8"))
country_keys = {normalize(name): key for key, (name, _, kind) in CLUES.items() if kind == "national"}
coach_keys = {normalize(name): key for key, (name, _, kind) in CLUES.items() if kind == "coach"}

def national_clue(country):
    identity = normalize(country)
    key = country_keys.setdefault(identity, "national-" + identity)
    CLUES.setdefault(key, (country, country, "national"))
    return key


# A single senior call-up list establishes overlap. Keep each camp separate
# from previous call-ups and never infer a coach from a shared season.
regional_squads = json.loads(Path(__file__).with_name("xo-national-squads.json").read_text(encoding="utf-8"))
for squad in regional_squads:
    manager = coach_keys.get(normalize(squad["coach"] or ""))
    add_team_group(national_clue(squad["team"]), manager, squad["names"])

for _, country, squad in national_history["tournament_squads"]:
    key = national_clue(country)
    for player in squad:
        add_fact(key, player)

for _, _, country, manager, lineup in national_history["matches"]:
    add_team_group(national_clue(country), coach_keys.get(normalize(manager)), lineup)

# Positive senior appearances from 11v11 season tables, published club-season
# statistics and player career records. Coach and teammate additions use lineups
# from European Cup, UEFA Cup, EURO and Gold Cup finals or audited match sheets.
verified = json.loads(Path(__file__).with_name("xo-verified-links.json").read_text(encoding="utf-8"))
for key, names in verified.items():
    for name in names:
        add_fact(key, name)

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
HEADER_CLUBS = {
    "roma", "inter", "milan", "napoli", "juventus", "lazio",
    "barcelona", "real", "atletico", "betis", "sociedad", "sevilla", "villarreal", "bilbao",
    "arsenal", "city", "united", "liverpool", "brighton", "chelsea", "tottenham", "newcastle", "villa",
    "psg", "marseille", "lyon", "monaco", "lille",
    "porto", "benfica", "sporting-cp",
}
ALL_ROWS = tuple(key for key, (_, _, kind) in CLUES.items() if key in HEADER_CLUBS or kind == "coach")
ALL_COLUMNS = tuple(key for key, (_, _, kind) in CLUES.items() if key in HEADER_CLUBS or kind == "player")


NEIGHBOURS = {
    row: {col for col in ALL_COLUMNS if frozenset((row, col)) in CONNECTIONS}
    for row in ALL_ROWS
}
PLAYER_KEYS = {key for key in ALL_COLUMNS if CLUES[key][2] == "player"}
COACH_KEYS = {key for key in ALL_ROWS if CLUES[key][2] == "coach"}


def candidate_layout(size, coach_count, player_count):
    rows = []
    columns = set(ALL_COLUMNS)
    for row_kind in (COACH_KEYS,) * coach_count + (HEADER_CLUBS,) * (size - coach_count):
        choices = []
        for row in sorted(row_kind - set(rows)):
            compatible = (columns & NEIGHBOURS[row]) - {row}
            if (len(compatible & HEADER_CLUBS) >= size - player_count
                    and len(compatible & PLAYER_KEYS) >= player_count):
                choices.append((row, compatible))
        if not choices:
            return None
        row, columns = choice(choices)
        rows.append(row)
    clubs = sample(sorted(columns & HEADER_CLUBS), size - player_count)
    players = sample(sorted(columns & PLAYER_KEYS), player_count)
    return tuple(rows), tuple(clubs + players)


@lru_cache(maxsize=len(SIZES))
def layouts(size):
    boards = {}
    mixes = [(coaches, players) for coaches in range(size) for players in range(size - coaches)]
    shuffle(mixes)
    for attempt in range(40000):
        coaches, players = mixes[attempt % len(mixes)]
        board = candidate_layout(size, coaches, players)
        if board:
            rows, cols = board
            boards.setdefault(frozenset((*rows, *cols)), board)
            if len(boards) >= 1200:
                break
    return tuple(boards.values())


DECKS = {}
LAST_BOARDS = {}


@lru_cache(maxsize=9)
def difficulty_boards(size, difficulty):
    familiar = {normalize(p["name"]) for p in ROSTER}
    ease = {}
    def score(board):
        counts = []
        familiar_squares = 0
        for row in board[0]:
            for column in board[1]:
                pair = frozenset((row, column))
                if pair not in ease:
                    names = CONNECTIONS[pair]
                    ease[pair] = len(names), any(normalize(n) in familiar for n in names)
                count, recognizable = ease[pair]
                counts.append(count)
                familiar_squares += recognizable
        return median(counts), familiar_squares, sum(min(n, 20) for n in counts)
    ranked = sorted(layouts(size), key=score)
    level = ("Hard", "Medium", "Easy").index(difficulty)
    return ranked[len(ranked)*level//3:len(ranked)*(level+1)//3]


TOP_CLUBS = {"arsenal", "chelsea", "city", "united", "liverpool", "tottenham",
             "barcelona", "real", "atletico", "juventus", "milan", "inter", "psg"}
FAMOUS_PLAYERS = {"messi", "ronaldo", "neymar", "mbappe", "salah", "zlatan", "henry",
                  "ronaldinho", "beckham", "pirlo", "lamine-yamal", "erling-haaland"}
FAMOUS_COACHES = {"pep", "ancelotti", "mourinho", "klopp", "zidane", "alex-ferguson",
                  "arsene-wenger", "luis-enrique", "diego-simeone"}
with Path(__file__).with_name("xo-layouts.json").open(encoding="utf-8") as layout_file:
    RULED_BOARDS = json.load(layout_file)


def draw_board(size, difficulty="Medium"):
    key = (size, difficulty)
    deck = DECKS.setdefault(key, [])
    if not deck:
        deck.extend(RULED_BOARDS[str(size)][difficulty] if size in (3, 4) else difficulty_boards(size, difficulty))
        shuffle(deck)
        recent = LAST_BOARDS.get(key, ())
        for i in range(min(2, len(deck))):
            target = len(deck) - 1 - i
            if deck[target] in recent:
                replacement = next(j for j in range(target) if deck[j] not in recent)
                deck[target], deck[replacement] = deck[replacement], deck[target]
    board = deck.pop()
    LAST_BOARDS[key] = (board, *LAST_BOARDS.get(key, ())[:1])
    return board


@lru_cache(maxsize=len(SIZES))
def winning_lines(size):
    rows = [tuple(r * size + c for c in range(size)) for r in range(size)]
    columns = list(zip(*rows))
    diagonals = [tuple(r * size + c for r, c in enumerate(diagonal))
                 for diagonal in (range(size), range(size - 1, -1, -1))]
    return (*rows, *columns, *diagonals)


ALIASES = {"messi": "Lionel Messi", "zlatan": "Zlatan Ibrahimović",
           "cesc": "Cesc Fàbregas", "fabregas": "Cesc Fàbregas", "reyes": "José Antonio Reyes",
           "vin": "Vinícius Júnior", "vini": "Vinícius Júnior", "vinijr": "Vinícius Júnior",
           "vinicius": "Vinícius Júnior", "viniciusjr": "Vinícius Júnior",
           "fabrigas": "Cesc Fàbregas"}
PLAYER_TRANSLATIONS = json.loads(Path(__file__).with_name("quiz-ar.json").read_text(encoding="utf-8"))
ROSTER_TRANSLATIONS = {normalize(player["name"]): player["ar"] for player in ROSTER}
PLAYER_DIRECTORY = [(name, ROSTER_TRANSLATIONS.get(normalize(name), PLAYER_TRANSLATIONS.get(name, name)))
                    for name in PLAYERS]
FULL_NAMES = defaultdict(set)
SHORT_NAMES = defaultdict(set)
for name, translated in PLAYER_DIRECTORY:
    for label in {name, translated, PLAYER_TRANSLATIONS.get(name, name)}:
        FULL_NAMES[normalize(label)].add(name)
        SHORT_NAMES[normalize(label.split()[-1])].add(name)
for alias, name in {**DISPLAY_ALIASES, **ALIASES}.items():
    if name in PLAYERS:
        FULL_NAMES[normalize(alias)].add(name)


class Match:
    def __init__(self, names, solo=False, size=3, revision=0, now=None, difficulty="Medium",
                 best_of=1, turn_seconds=30, round_minutes=0, round_index=0, scores=None):
        self.size = size
        self.difficulty = difficulty
        self.best_of = best_of
        self.turn_seconds = turn_seconds
        self.round_minutes = round_minutes
        self.round_index = round_index
        self.scores = list(scores or [0, 0])
        self.expired = False
        self.continue_at = None
        rows, columns = draw_board(size, difficulty)
        self.rows = sample(rows, size)
        self.columns = sample(columns, size)
        self.answers = [sorted(CONNECTIONS[frozenset((r, c))]) for r in self.rows for c in self.columns]
        self.names = names
        self.solo = solo
        self.cells = [None] * (size * size)
        self.turn = round_index % 2
        self.revision = revision
        self.winner = None
        self.line = ()
        self.revealed = False
        self.lives = 3 if solo else None
        self.end_vote = None
        self.notice = ""
        started = monotonic() if now is None else now
        self.deadline = None if solo else started + turn_seconds
        self.round_end = started + round_minutes * 60 if round_minutes and not solo else None

    @property
    def lost(self):
        return self.solo and self.lives == 0

    @property
    def finished(self):
        return self.expired or self.winner is not None or all(self.cells) or self.revealed or self.lost

    def tick(self, now):
        if self.finished or self.solo:
            return
        if self.round_end is not None and now >= self.round_end:
            counts = [sum(bool(cell and cell["team"] == team) for cell in self.cells) for team in (0, 1)]
            self.expired = True
            if counts[0] != counts[1]:
                self.winner = counts.index(max(counts))
                self.scores[self.winner] += 1
            self.revision += 1
        elif now >= self.deadline:
            elapsed_turns = 1 + int((now - self.deadline) // self.turn_seconds)
            self.turn = (self.turn + elapsed_turns) % 2
            self.deadline += elapsed_turns * self.turn_seconds
            self.revision += elapsed_turns
            self.end_vote = None
            self.notice = "Time ran out. Turn passed."

    def advance(self, now, notice="", keep_vote=False):
        self.turn = 1 - self.turn
        self.deadline = now + self.turn_seconds
        self.revision += 1
        self.notice = notice
        if not keep_vote:
            self.end_vote = None

    @property
    def series_over(self):
        return max(self.scores) >= self.best_of // 2 + 1

    def next_round(self, now):
        return Match(self.names, solo=self.solo, size=self.size, revision=self.revision + 1,
                     now=now, difficulty=self.difficulty, best_of=self.best_of,
                     turn_seconds=self.turn_seconds, round_minutes=self.round_minutes,
                     round_index=0 if self.solo else self.round_index + 1, scores=self.scores)

    def vote_to_end(self, team, now):
        if self.end_vote is not None and self.end_vote != team:
            return self.next_round(now)
        self.end_vote = team
        self.advance(now, keep_vote=True)
        return self

    def play(self, team, cell, guess, now):
        if self.finished or team != self.turn or self.cells[cell]:
            return "That square is unavailable."
        key = normalize(guess)
        full_matches = FULL_NAMES.get(key)
        candidates = full_matches or SHORT_NAMES.get(key, set())
        matches = candidates.intersection(self.answers[cell])
        if len(matches) > 1:
            return "Several players share that name. Pick a full name."
        if len(matches) != 1:
            if self.solo:
                self.lives -= 1
                self.revision += 1
                return "Wrong guess. No lives left." if self.lost else "Wrong guess. You lost a life."
            self.advance(now, "That name wasn’t accepted. Turn passed.")
            return self.notice
        self.cells[cell] = {"team": team, "player": next(iter(matches))}
        if self.solo:
            self.revision += 1
        else:
            self.line = next((line for line in winning_lines(self.size)
                              if all(self.cells[i] and self.cells[i]["team"] == team for i in line)), ())
            if self.line or all(self.cells):
                self.winner = team if self.line else None
                if self.line:
                    self.scores[team] += 1
                self.end_vote = None
                self.notice = ""
                self.revision += 1
            else:
                self.advance(now)
        return "Square claimed."

    def view(self, team, now=None):
        def clues(keys):
            return [dict(name=CLUES[key][0], ar=CLUES[key][1], kind=CLUES[key][2],
                         image=(f"/static/{clue_image(key)}" if Path(__file__).with_name("static").joinpath(clue_image(key)).is_file() else None))
                    for key in keys]
        return dict(rows=clues(self.rows), columns=clues(self.columns), names=self.names, solo=self.solo, team=team,
                    best_of=self.best_of, scores=self.scores, series_over=self.series_over, round_number=self.round_index + 1,
                    round_remaining=max(0, self.round_end - (monotonic() if now is None else now))
                    if self.round_end is not None and not self.finished else None,
                    size=self.size, lives=self.lives, lost=self.lost, end_vote=self.end_vote, notice=self.notice,
                    remaining=max(0, self.deadline - (monotonic() if now is None else now))
                    if not self.solo and not self.finished else None,
                    cells=self.cells, turn=self.turn, revision=self.revision, winner=self.winner,
                    line=self.line, finished=self.finished, revealed=self.revealed,
                    examples=[names[0] for names in self.answers] if self.revealed else None)
