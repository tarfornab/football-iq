import json
import sqlite3
from collections import Counter
from pathlib import Path
from random import choice, shuffle

BANK = json.loads(Path(__file__).with_name("questions.json").read_text(encoding="utf-8"))
ARABIC = json.loads(Path(__file__).with_name("quiz-ar.json").read_text(encoding="utf-8"))
HISTORY = Path(__file__).with_name("question_history.sqlite3")
REVEAL_SECONDS = 4
KICKOFF_SECONDS = 3
DIFFICULTIES = ("Easy", "Medium", "Medium", "Hard", "Medium", "Easy", "Medium")


def draw_question(used, topics):
    with sqlite3.connect(HISTORY) as db:
        db.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY)")
        db.execute("BEGIN IMMEDIATE")
        seen = {row[0] for row in db.execute("SELECT id FROM seen")}
        available = [q for q in BANK if q["id"] not in seen and q["id"] not in used]
        if not available and all(q["id"] in seen for q in BANK):
            db.execute("DELETE FROM seen")
            available = [q for q in BANK if q["id"] not in used]
        if not available:
            return None
        preferences = (
            ("difficulty", DIFFICULTIES[len(used) % len(DIFFICULTIES)]),
            ("era", (2, 0, 2, 1)[len(used) % 4]),
            ("kind", ("careers", "competitions", "scorers", "competitions", "awards", "honours")[len(used) % 6]),
        )

        def balance(question):
            values = {
                "difficulty": question["difficulty"],
                "era": min(2, (question["year"] - 1990) // 13),
                "kind": question["kind"],
            }
            # Favor question variety while still rotating through competitions.
            score = sum(weight for (field, target), weight in zip(preferences, (9, 4, 3))
                        if values[field] == target)
            recent = question["year"] >= 2023 and len(used) % 4 == 0
            return score + 4 * recent - min(5, topics[question["topic"]])

        best = max(map(balance, available))
        question = choice([q for q in available if balance(q) == best])
        db.execute("INSERT INTO seen VALUES (?)", (question["id"],))
    used.add(question["id"])
    topics[question["topic"]] += 1
    options = [question["answer"], *question["distractors"]]
    shuffle(options)
    return question["text"], options, options.index(question["answer"]), question["topic"]


ROUND_NAMES = ("Multiple Choice", "The Boom", "90-Second Quiz")
DURATIONS = (20, 120, 90)


class Quiz:
    def __init__(self, names, solo=False):
        self.names, self.solo = names, solo
        self.round = 2 if solo else 0
        self.question = self.turn = self.version = 0
        self.phase = "waiting"
        self.ends = self.turn_ends = 0
        self.scores = [0] * len(names)
        self.awards = [0] * len(names)
        self.answers = {}
        self.cup = []
        self.results = []
        self.used = set()
        self.topics = Counter()
        self.active = [None] * len(names)
        self.positions = [0] * len(names)
        self.exploded = None
        self.feedback = [None] * len(names)
        self.penalty = 0

    def deal(self, team=0):
        self.active[team] = draw_question(self.used, self.topics)
        return self.active[team] is not None

    def current(self, team):
        return self.active[team if self.round == 2 else 0]

    def revision(self, team):
        return f"{self.version}:{self.positions[team]}"

    def finish(self):
        self.results.append(self.scores.copy())
        if not self.solo:
            self.cup.append([
                len(self.names) - sum(other > score for other in self.scores)
                for score in self.scores
            ])
        self.phase = "standings"

    def tick(self, now):
        if self.phase == "kickoff":
            if now >= self.ends:
                self.begin_play(now)
            return
        if self.phase == "answer":
            if now >= self.ends:
                self.next(now, automatic=True)
            return
        if self.phase != "play":
            return
        if self.round == 1 and now >= min(self.ends, self.turn_ends):
            self.exploded = self.turn
            self.penalty = min(self.scores[self.turn], len(self.names))
            self.scores[self.turn] -= self.penalty
            self.finish()
        elif now >= self.ends:
            if self.round == 0:
                correct = self.current(0)[2]
                self.awards = [0] * len(self.names)
                points = len(self.names)
                for team, choice in self.answers.items():
                    if choice == correct:
                        self.awards[team] = points
                        self.scores[team] += points
                        points -= 1
                self.phase = "answer"
                self.ends = now + REVEAL_SECONDS
            else:
                self.finish()

    def next(self, now, automatic=False):
        if self.phase == "answer":
            if not automatic:
                return
            if self.question == 14:
                self.finish()
                return
            self.question += 1
            self.begin_play(now)
            return
        elif self.phase == "standings":
            if self.round == 2:
                self.phase = "done"
                return
            self.round += 1
            self.question = 0
            self.scores = [0] * len(self.names)
        elif self.phase != "waiting":
            return

        self.phase = "kickoff"
        self.ends = now + KICKOFF_SECONDS
        self.feedback = [None] * len(self.names)

    def begin_play(self, now):
        self.version += 1
        self.phase = "play"
        self.answers.clear()
        self.ends = now + DURATIONS[self.round]
        self.turn_ends = now + 20
        slots = range(len(self.names)) if self.round == 2 else (0,)
        for slot in slots:
            if not self.deal(slot):
                self.finish()
                break

    def answer(self, team, choice, revision, now):
        if self.phase != "play" or revision != self.revision(team):
            return
        if type(choice) is not int or not 0 <= choice < 4:
            return
        if self.round == 0:
            self.answers.setdefault(team, choice)
            return
        if self.round == 1 and team != self.turn:
            return
        correct = choice == self.current(team)[2]
        self.feedback[team] = (correct, now + 1.8)
        if correct:
            self.scores[team] += 1
        if self.round == 1:
            self.question += 1
            self.version += 1
            if not self.deal():
                self.finish()
                return
            if correct:
                self.turn = (team + 1) % len(self.names)
                self.turn_ends = now + 20
        else:
            self.positions[team] += 1
            if not self.deal(team):
                self.finish()

    def view(self, team, now, language="en"):
        question, choices, correct, topic = self.current(team) or ("", [], None, "")
        if language == "ar":
            question = ARABIC.get(question, question)
            choices = [ARABIC.get(option, option) for option in choices]
            topic = ARABIC.get(topic, topic)
        feedback = self.feedback[team]
        return dict(
            names=self.names, solo=self.solo, team=team, round=self.round,
            phase=self.phase, title=ROUND_NAMES[self.round], number=self.question + 1,
            topic=topic,
            question=question if self.phase in ("play", "answer") else "",
            choices=choices if self.phase in ("play", "answer") else [],
            correct=correct if self.phase == "answer" else None,
            submitted=team in self.answers, revision=self.revision(team),
            scores=self.scores, awards=self.awards, roundNames=ROUND_NAMES,
            exploded=self.exploded, penalty=self.penalty, cup=self.cup, results=self.results,
            feedback=feedback[0] if feedback and now < feedback[1] else None,
            totals=[sum(row[i] for row in self.cup) for i in range(len(self.names))],
            turn=self.turn, remaining=max(0, self.ends - now),
            turnRemaining=max(0, min(self.ends, self.turn_ends) - now),
            duration=DURATIONS[self.round],
        )
