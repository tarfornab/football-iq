import json
from math import ceil
from pathlib import Path
from random import choice, sample, shuffle

CLUBS = json.loads(Path(__file__).with_name("guess-clubs.json").read_text(encoding="utf-8"))
OPENERS = list(CLUBS)[:13]
FAMILIAR = ["Napoli", "Roma", "Lazio", "Atalanta", "Newcastle United", "Aston Villa",
            "Everton", "Valencia", "Sevilla", "Villarreal", "Athletic Club", "Real Betis"]


class GuessRound:
    def __init__(self, names):
        self.names = dict(sorted(names.items()))
        self.scores = dict.fromkeys(names, 0)
        first = sample(OPENERS, 3)
        next_clubs = sample(FAMILIAR, 4)
        rest = [club for club in CLUBS if club not in OPENERS and club not in next_clubs]
        shuffle(rest)
        self.deck = [(club, choice(CLUBS[club])) for club in first + next_clubs + rest]
        self.deadline = None

    def start(self, now):
        if self.deadline is None:
            self.deadline = now + 120

    def answer(self, team, data, now):
        index = self.scores[team]
        if self.deadline is None or now >= self.deadline or index >= len(self.deck):
            return None
        if data.get("index") != index:
            return None
        if self.deck[index][0] == data.get("club"):
            self.scores[team] += 1
            return "correct"
        return "wrong"

    def view(self, team, now):
        seconds = 120 if self.deadline is None else max(0, ceil(self.deadline - now))
        index = self.scores[team]
        phase = "waiting" if self.deadline is None else "playing"
        if seconds == 0 or min(self.scores.values()) == len(self.deck):
            phase = "finished"
        elif index == len(self.deck):
            phase = "complete"
        return dict(phase=phase, seconds=seconds, index=index,
                    rows=self.deck[index][1]["rows"] if phase == "playing" else [],
                    scores=[{"name": name, "score": self.scores[n]} for n, name in self.names.items()])
