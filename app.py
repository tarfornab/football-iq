import base64
import io
import secrets
from threading import Lock
from time import monotonic
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from quiz import Quiz
from imposter import ROSTER, move as imposter_move, new_round as new_imposter_round
from xo import Match, PLAYER_DIRECTORY, SIZES

import qrcode
from flask import (
    Flask, abort, jsonify, redirect, render_template, render_template_string,
    request, send_from_directory, url_for,
)

app = Flask(__name__)
rooms = {}
imposter_rooms = {}
room_lock = Lock()
GAME_NAMES = {"quiz": "Quiz", "guess": "Guess", "xo": "X/O"}

@app.after_request
def preserve_language_on_redirect(response):
    language = request.args.get("lang")
    location = response.headers.get("Location")
    if language in {"ar", "en"} and 300 <= response.status_code < 400 and location:
        destination = urlsplit(location)
        if not destination.netloc and destination.path.startswith("/"):
            params = dict(parse_qsl(destination.query, keep_blank_values=True))
            params["lang"] = language
            response.headers["Location"] = urlunsplit(destination._replace(query=urlencode(params)))
    return response


PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }} | The Football IQ Game</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='design.css') }}">
<script src="/static/arabic-labels.js?v=more-clues-1"></script>
<script src="/static/language.js?v=more-clues-1"></script>
</head>
<body class="cup-body">
<main class="cup-page {{ screen }}-page">
  <a class="site-nav" href="{{ url_for('home') }}">Football <span>IQ</span> Game</a>
  <h1>{{ title }}</h1>
  {% if error %}<p role="alert">{{ error }}</p>{% endif %}

  {% if screen == "setup" %}
    <form class="card small" method="post">
      {% if mode == "xo" %}
        <p>Team 1 vs. Team 2</p>
      {% else %}
        <label for="count">How many teams?</label>
        <select id="count" name="count" required>
          <option value="" selected disabled>Choose 1 to 6</option>
          {% for total in range(1, 7) %}
            <option value="{{ total }}">{{ total }}</option>
          {% endfor %}
        </select>
      {% endif %}
      <button type="submit">Create room</button>
    </form>
    <a href="{{ url_for('home') }}#{{ mode }}">Back to mode selection</a>

  {% elif screen == "join" %}
    <form class="card small" method="post">
      <button name="action" value="join">Join as Team {{ number }}</button>
    </form>

  {% elif screen == "lobby" %}
    {% if number == 1 %}
      <div class="teams">
        <section class="card host-card">
          <h2>Team 1</h2>
          <p>Host · Joined</p>
        </section>
        {% for invite in invites %}
          <section class="card">
            <h2>Team {{ invite.number }}</h2>
            <p id="team-{{ invite.number }}" role="status">
              {{ "Joined" if invite.number in joined else "Waiting to join" }}
            </p>
            <img src="{{ invite.qr }}" alt="Scan to join Team {{ invite.number }}">
            <input aria-label="Team {{ invite.number }} invite link"
                   value="{{ invite.link }}" readonly>
            <button type="button" class="copy">Copy invite link</button>
            <p class="copy-message" role="status"></p>
          </section>
        {% endfor %}
      </div>

      <form class="small{% if mode == 'xo' %} xo-start-form{% endif %}" method="post">
        {% if mode == "xo" %}
          <label for="board-size">Board size</label>
          <select id="board-size" name="board-size">
            {% for side in board_sizes %}
              <option value="{{ side }}">{{ side }}×{{ side }}</option>
            {% endfor %}
          </select>
        {% endif %}
        <button id="start" name="action" value="start"
                {% if joined|length != count %}disabled{% endif %}>Start</button>
      </form>
      <p id="progress" role="status">{{ joined|length }} of {{ count }} teams joined</p>
    {% else %}
      <p>You joined as Team {{ number }}. Waiting for Team 1 to press Start.</p>
    {% endif %}

  {% elif screen == "naming" %}
    {% if submitted %}
      <p>You’re ready. Waiting for the other teams.</p>
    {% else %}
      <form class="card small" method="post">
        <label for="team-name">Team {{ number }} name</label>
        <input id="team-name" name="team_name" maxlength="30" required>
        <button type="submit">Ready</button>
      </form>
    {% endif %}
    <p id="progress" role="status">{{ ready_count }} of {{ count }} teams ready</p>

  {% elif screen == "reveal" %}
    <div class="teams">
      {% for team_number, name in names %}
        <section class="card ready-card">
          <p class="team-slot">Team {{ team_number }}</p>
          <h2 data-team-name>{{ name }}</h2>
        </section>
      {% endfor %}
    </div>
  {% endif %}
</main>

{% if screen in ("lobby", "naming") %}
<script>
  for (const button of document.querySelectorAll('.copy')) {
    button.addEventListener('click', async () => {
      const card = button.closest('.card');
      const field = card.querySelector('input');
      const message = card.querySelector('.copy-message');

      field.focus();
      field.select();

      try {
        if (window.isSecureContext && navigator.clipboard) {
          await navigator.clipboard.writeText(field.value);
        } else if (!document.execCommand('copy')) {
          throw new Error('Copy unavailable');
        }
        message.textContent = tr('Link copied.');
      } catch {
        message.textContent = tr('Copy the selected link manually.');
      }
    });
  }

  const screen = {{ screen | tojson }};
  const progress = document.querySelector('#progress');
  const start = document.querySelector('#start');

  async function updateRoom() {
    try {
      const response = await fetch({{ status_url | tojson }}, { cache: 'no-store' });

      if (response.ok) {
        const room = await response.json();

        if (room.stage !== screen) {
          window.location.replace(withGameLanguage(room.next_url));
          return;
        }

        if (start) {
          for (const number of room.joined) {
            const label = document.querySelector('#team-' + number);
            if (label && label.textContent.trim() !== tr('Joined')) {
              label.textContent = tr('Joined');
            }
          }
          start.disabled = room.joined.length !== room.count;
          progress.textContent = tr('{0} of {1} teams joined', room.joined.length, room.count);
        } else if (progress) {
          progress.textContent = tr('{0} of {1} teams ready', room.ready_count, room.count);
        }
      }
    } catch {
      // Retry if the connection drops.
    }

    setTimeout(updateRoom, 1500);
  }

  updateRoom();
</script>
{% endif %}
</body>
</html>
"""


def render_page(screen, title, **values):
    response = app.make_response(
        render_template_string(PAGE, screen=screen, title=title, **values)
    )
    response.headers["Cache-Control"] = "no-store"
    return response


def make_qr(link):
    image = io.BytesIO()
    qrcode.make(link).save(image, format="PNG")
    return "data:image/png;base64," + base64.b64encode(image.getvalue()).decode()


def get_team(room_id, token):
    room = rooms.get(room_id)
    if room is None or token not in room["teams"]:
        abort(404, "This room or invite is no longer available.")
    return room, room["teams"][token]


def stage_url(stage, room_id, token):
    endpoints = {"lobby": "lobby", "naming": "name_page", "reveal": "reveal"}
    return url_for(endpoints[stage], room_id=room_id, token=token)


@app.get("/")
@app.get("/index.html")
def home():
    return send_from_directory(app.root_path, "index.html")


@app.route("/game.html", methods=["GET", "POST"])
def setup():
    mode = request.args.get("mode", "quiz")
    if mode not in GAME_NAMES:
        abort(404)

    if request.method == "GET":
        return render_page("setup", f"{GAME_NAMES[mode]} Team Setup", mode=mode)

    count = 2 if mode == "xo" else request.form.get("count", type=int)
    if count is None or not 1 <= count <= 6:
        abort(400, "Choose 1 to 6 teams.")

    room_id = secrets.token_urlsafe(16)
    host_token = secrets.token_urlsafe(16)
    teams = {host_token: 1}
    for number in range(2, count + 1):
        teams[secrets.token_urlsafe(16)] = number

    with room_lock:
        rooms[room_id] = {
            "mode": mode,
            "teams": teams,
            "joined": {1},
            "names": {},
            "stage": "lobby",
        }

    return redirect(stage_url("lobby", room_id, host_token), code=303)


@app.route("/room/<room_id>/<token>", methods=["GET", "POST"])
def lobby(room_id, token):
    error = None

    with room_lock:
        room, number = get_team(room_id, token)
        count = len(room["teams"])

        if request.method == "POST":
            action = request.form.get("action")

            if action == "join" and room["stage"] == "lobby":
                room["joined"].add(number)
            elif action == "start":
                if number != 1:
                    abort(403)
                if room["stage"] == "lobby":
                    if len(room["joined"]) == count:
                        if room["mode"] == "xo":
                            size = request.form.get("board-size", "3")
                            if size not in {str(side) for side in SIZES}:
                                abort(400, "Choose a 3×3, 4×4, or 5×5 board.")
                            room["xo_size"] = int(size)
                        room["stage"] = "naming"
                    else:
                        error = "Wait for all teams to join."

            if error is None:
                return redirect(stage_url(room["stage"], room_id, token), code=303)

        if number not in room["joined"]:
            return render_page("join", f"Team {number}", number=number)

        if room["stage"] != "lobby":
            return redirect(stage_url(room["stage"], room_id, token))

        joined = set(room["joined"])
        mode = room["mode"]
        game_name = GAME_NAMES[mode]
        invite_tokens = room["teams"].copy() if number == 1 else {}

    invites = []
    for invite_token, team_number in invite_tokens.items():
        if team_number == 1:
            continue
        link = url_for("lobby", room_id=room_id, token=invite_token, _external=True)
        invites.append({"number": team_number, "link": link, "qr": make_qr(link)})

    return render_page(
        "lobby", f"{game_name} Lobby",
        number=number, count=count, joined=joined, invites=invites, error=error,
        mode=mode, board_sizes=SIZES,
        status_url=url_for("room_status", room_id=room_id, token=token),
    )


@app.route("/room/<room_id>/<token>/name", methods=["GET", "POST"])
def name_page(room_id, token):
    error = None

    with room_lock:
        room, number = get_team(room_id, token)

        if number not in room["joined"]:
            return redirect(stage_url("lobby", room_id, token), code=303)
        if room["stage"] != "naming":
            return redirect(stage_url(room["stage"], room_id, token), code=303)

        count = len(room["teams"])

        if request.method == "POST":
            if number in room["names"]:
                return redirect(stage_url("naming", room_id, token), code=303)

            name = request.form.get("team_name", "").strip()
            if 1 <= len(name) <= 30:
                room["names"][number] = name
                if len(room["names"]) == count:
                    room["stage"] = "reveal"
                return redirect(stage_url(room["stage"], room_id, token), code=303)

            error = "Enter a team name between 1 and 30 characters."

        submitted = number in room["names"]
        ready_count = len(room["names"])

    return render_page(
        "naming", "Choose your team name", number=number, count=count,
        submitted=submitted, ready_count=ready_count, error=error,
        status_url=url_for("room_status", room_id=room_id, token=token),
    )


@app.get("/room/<room_id>/<token>/reveal")
def reveal(room_id, token):
    with room_lock:
        room, number = get_team(room_id, token)

        if number not in room["joined"]:
            return redirect(stage_url("lobby", room_id, token))
        if room["stage"] != "reveal":
            return redirect(stage_url(room["stage"], room_id, token))

        names = sorted(room["names"].items())

        if room["mode"] == "quiz":
            return redirect(url_for("quiz_page", room_id=room_id, token=token))
        if room["mode"] == "xo":
            return redirect(url_for("xo_page", room_id=room_id, token=token))

    return render_page("reveal", "All teams are ready", names=names)


@app.get("/room/<room_id>/<token>/status")
def room_status(room_id, token):
    with room_lock:
        room, number = get_team(room_id, token)
        if number not in room["joined"]:
            abort(403)

        stage = room["stage"]
        return jsonify(
            stage=stage,
            joined=sorted(room["joined"]),
            count=len(room["teams"]),
            ready_count=len(room["names"]),
            next_url=stage_url(stage, room_id, token),
        )


@app.post("/quiz/solo")
def solo_quiz():
    room_id, token = secrets.token_urlsafe(16), secrets.token_urlsafe(16)
    with room_lock:
        rooms[room_id] = {
            "mode": "quiz", "stage": "reveal", "joined": {1},
            "teams": {token: 1}, "names": {1: "You"},
            "quiz": Quiz(["You"], solo=True),
        }
    return redirect(url_for("quiz_page", room_id=room_id, token=token), code=303)


def get_quiz_room(room_id, token):
    room, number = get_team(room_id, token)
    if room["mode"] != "quiz" or room["stage"] != "reveal" or number not in room["joined"]:
        abort(403)
    return room, number - 1


@app.get("/quiz/<room_id>/<token>")
def quiz_page(room_id, token):
    with room_lock:
        get_quiz_room(room_id, token)
    return render_template("quiz.html", state_url=url_for("quiz_state", room_id=room_id, token=token))


@app.route("/quiz/<room_id>/<token>/state", methods=["GET", "POST"])
def quiz_state(room_id, token):
    with room_lock:
        room, team = get_quiz_room(room_id, token)
        if "quiz" not in room:
            room["quiz"] = Quiz([name for _, name in sorted(room["names"].items())])
        quiz = room["quiz"]
        now = monotonic()
        quiz.tick(now)
        if request.method == "POST":
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                abort(400)
            action = data.get("action")
            if action == "answer":
                quiz.answer(team, data.get("choice"), data.get("revision"), now)
            elif action == "next":
                if team != 0:
                    abort(403)
                if data.get("phase") == quiz.phase and data.get("revision") == quiz.revision(team):
                    quiz.next(now)
            else:
                abort(400)
        response = jsonify(quiz.view(team, now, request.args.get("lang", request.headers.get("X-Football-Language", "en"))))
        response.headers["Cache-Control"] = "no-store"
        return response


@app.post("/xo/solo")
def solo_xo():
    room_id, token = secrets.token_urlsafe(16), secrets.token_urlsafe(16)
    with room_lock:
        rooms[room_id] = {
            "mode": "xo", "stage": "reveal", "joined": {1},
            "teams": {token: 1}, "names": {1: "You"}, "xo": Match(["You"], solo=True),
        }
    return redirect(url_for("xo_page", room_id=room_id, token=token), code=303)


def get_xo_room(room_id, token):
    room, number = get_team(room_id, token)
    if room["mode"] != "xo" or room["stage"] != "reveal" or number not in room["joined"]:
        abort(403)
    return room, number - 1


def get_xo_match(room, now):
    if "xo" not in room:
        room["xo"] = Match([name for _, name in sorted(room["names"].items())], size=room.get("xo_size", 3), now=now)
    return room["xo"]


@app.get("/xo/<room_id>/<token>")
def xo_page(room_id, token):
    with room_lock:
        room, team = get_xo_room(room_id, token)
        now = monotonic()
        match = get_xo_match(room, now)
        match.tick(now)
        board = match.view(team, now)
        response = app.make_response(render_template(
            "xo.html", state_url=url_for("xo_state", room_id=room_id, token=token),
            board=board, player_directory=PLAYER_DIRECTORY,
        ))
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/xo/<room_id>/<token>/state", methods=["GET", "POST"])
def xo_state(room_id, token):
    with room_lock:
        room, team = get_xo_room(room_id, token)
        now = monotonic()
        match = get_xo_match(room, now)
        match.tick(now)
        message = ""
        if request.method == "POST":
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                abort(400)
            action = data.get("action")
            if data.get("revision") != match.revision:
                message = "The board has changed."
            elif action == "play":
                index, guess = data.get("cell"), data.get("guess")
                if type(index) is not int or not 0 <= index < len(match.cells) or not isinstance(guess, str) or not 1 <= len(guess.strip()) <= 80:
                    abort(400)
                message = match.play(team, index, guess, now)
            elif action in {"pass", "end"} and not match.solo:
                if match.finished or team != match.turn:
                    message = "It is not your turn."
                elif action == "pass":
                    match.advance(now, "Turn passed.")
                    message = match.notice
                else:
                    new_match = match.vote_to_end(team, now)
                    if new_match is not match:
                        message = "Both teams voted. New board."
                        new_match.notice = message
                    room["xo"] = match = new_match
            elif action == "reveal" and (match.solo or match.finished):
                match.revealed = True
                match.revision += 1
            elif action == "restart" and match.solo:
                room["xo"] = match = Match(["You"], solo=True, size=match.size, revision=match.revision + 1)
            else:
                abort(403)
        response = jsonify(**match.view(team, now), message=message)
        response.headers["Cache-Control"] = "no-store"
        return response


@app.post("/imposter")
def start_imposter():
    count = request.form.get("players", type=int)
    if count not in range(3, 21):
        abort(400, "Choose between 3 and 20 players.")
    token = secrets.token_urlsafe(24)
    with room_lock:
        imposter_rooms[token] = new_imposter_round(count)
    return redirect(url_for("imposter_page", token=token), code=303)


@app.route("/imposter/<token>", methods=["GET", "POST"])
def imposter_page(token):
    with room_lock:
        game = imposter_rooms.get(token)
        if game is None:
            abort(404, "This Imposter round is no longer available.")
        if request.method == "POST":
            if request.form.get("revision", type=int) == game["revision"]:
                imposter_rooms[token] = imposter_move(
                    game, request.form.get("action")
                )
            return redirect(url_for("imposter_page", token=token), code=303)
        show_secret = game["phase"] == "role" and game["player"] != game["imposter"]
        secret = ROSTER[game["secret"]] if show_secret else None
        response = app.make_response(render_template("imposter.html", game=game.copy(), secret=secret))
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)