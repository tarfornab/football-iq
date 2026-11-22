import json
import sqlite3
from pathlib import Path
from secrets import randbelow

ROSTER = json.loads(Path(__file__).with_name("imposter-players.json").read_text(encoding="utf-8"))


HISTORY = Path(__file__).with_name("imposter-history.sqlite3")


def draw_player():
    with sqlite3.connect(HISTORY) as db:
        db.execute("CREATE TABLE IF NOT EXISTS seen (name TEXT PRIMARY KEY, draw_order INTEGER NOT NULL)")
        db.execute("BEGIN IMMEDIATE")
        seen = db.execute("SELECT name FROM seen ORDER BY draw_order").fetchall()
        names = {name for (name,) in seen}
        available = [i for i, player in enumerate(ROSTER) if player["name"] not in names]
        if not available:
            latest = seen[-1][0]
            db.execute("DELETE FROM seen")
            available = [i for i, player in enumerate(ROSTER) if player["name"] != latest]
        picked = available[randbelow(len(available))]
        db.execute(
            "INSERT INTO seen VALUES (?, (SELECT COALESCE(MAX(draw_order), 0) + 1 FROM seen))",
            (ROSTER[picked]["name"],),
        )
        return picked


def new_round(count, revision=0):
    return {
        "count": count,
        "secret": draw_player(),
        "imposter": randbelow(count) + 1,
        "player": 1,
        "phase": "pass",
        "revision": revision,
        "suspect": None,
    }


def move(game, action, suspect=None):
    phase = game["phase"]
    if phase == "pass" and action == "reveal":
        game["phase"] = "role"
    elif phase == "role" and action == "next":
        if game["player"] == game["count"]:
            game["phase"] = "discuss"
        else:
            game["player"] += 1
            game["phase"] = "pass"
    elif phase == "discuss" and action == "vote" and suspect in range(1, game["count"] + 1):
        game["suspect"] = suspect
        game["phase"] = "result"
    elif phase == "result" and action == "again":
        return new_round(game["count"], revision=game["revision"] + 1)
    else:
        return game
    game["revision"] += 1
    return game
