import os

from flask import Flask, jsonify, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

PUZZLES = [
    {
        "id": 1,
        "type": "rebus_set",
        "title": "Rebus Round",
        "question": "Solve all four rebus puzzles to unlock the next clue.",
        "hint": "Say the picture out loud like a phrase, object, or expression.",
        "rebuses": [
            {
                "key": "rebus_1",
                "label": "Rebus 1",
                "answer": "face the music",
                "hint": "The letters seem to be making a shape.",
                "kind": "face-the-music"
            },
            {
                "key": "rebus_2",
                "label": "Rebus 2",
                "answer": "feeling under the weather",
                "hint": "Achoo! Sorry. I'm too sick to help you with this.",
                "kind": "feeling-under-the-weather"
            },
            {
                "key": "rebus_3",
                "label": "Rebus 3",
                "answer": "first edition",
                "hint": "I wonder which edition is marked out.",
                "kind": "first-edition"
            },
            {
                "key": "rebus_4",
                "label": "Rebus 4",
                "answer": "spill the beans",
                "hint": "Whoops! I spilled something.",
                "kind": "spill-the-beans"
            }
        ]
    },
    {
        "id": 2,
        "type": "progressive_single",
        "question": "Puzzle 2: UIF GJOBM DMVF JT TJLF! OPU IFSF",
        "answer": "THE FINAL CLUE IS SIKE! NOT HERE",
        "hint1": "Think Caesar cipher",
        "hint2": "The message has been shifted 1 step forward."
    },
    {
        "id": 3,
        "type": "inspect_clue",
        "title": "Final Puzzle",
        "question": "Hmmm nothing suspicious here 👀. Maybe there's something under the surface?",
        "hidden_clue": "TODO:\n"
        "remove hardcoded clue before production \n\n"
        "final clue location : Find me hiding under the couch\n"
    }
]


@app.route("/")
def index():
    session["level"] = 0
    session["rebus_progress"] = {}
    session["rebus_answers"] = {}
    session["single_attempts"] = {}
    session["single_answers"] = {}
    return render_template("index.html")


@app.route("/puzzle", methods=["GET", "POST"])
def puzzle():
    level = session.get("level", 0)

    if level >= len(PUZZLES):
        return redirect(url_for("final"))

    current_puzzle = PUZZLES[level]
    error = None
    submitted_answers = {}
    rebus_feedback = {}
    rebus_progress = session.get("rebus_progress", {})
    rebus_answers = session.get("rebus_answers", {})
    single_attempts = session.get("single_attempts", {})
    single_answers = session.get("single_answers", {})
    single_feedback = None
    progressive_hints = []
    puzzle_key = f"puzzle_{current_puzzle['id']}"

    if current_puzzle.get("type") == "rebus_set":
        submitted_answers = {
            rebus["key"]: rebus_answers.get(rebus["key"], "")
            for rebus in current_puzzle["rebuses"]
        }
    elif current_puzzle.get("type") == "progressive_single":
        submitted_answers["answer"] = single_answers.get(puzzle_key, "")
        attempts = single_attempts.get(puzzle_key, 0)
        if attempts >= 1:
            progressive_hints.append(current_puzzle["hint1"])
        if attempts >= 2:
            progressive_hints.append(current_puzzle["hint2"])

    if request.method == "POST":
        if current_puzzle.get("type") == "rebus_set":
            is_async_request = request.headers.get("X-Requested-With") == "XMLHttpRequest"
            rebus_key = request.form.get("rebus_key", "")
            rebus = next(
                (item for item in current_puzzle["rebuses"] if item["key"] == rebus_key),
                None
            )
            all_correct = False

            if rebus is not None:
                submitted_answer = request.form.get(rebus_key, "").strip()
                submitted_answers[rebus_key] = submitted_answer
                rebus_answers[rebus_key] = submitted_answer

                if submitted_answer.lower() == rebus["answer"].lower():
                    rebus_progress[rebus_key] = True
                    rebus_feedback[rebus_key] = {
                        "status": "success",
                        "message": "Solved! Cute and clever 😏"
                    }
                else:
                    rebus_feedback[rebus_key] = {
                        "status": "hint",
                        "message": f"Hint: {rebus['hint']}"
                    }

                session["rebus_progress"] = rebus_progress
                session["rebus_answers"] = rebus_answers

                all_correct = all(
                    rebus_progress.get(item["key"], False)
                    for item in current_puzzle["rebuses"]
                )

                if is_async_request:
                    next_url = None
                    if all_correct:
                        session["level"] = level + 1
                        session["rebus_progress"] = {}
                        session["rebus_answers"] = {}
                        next_url = url_for("final") if session["level"] >= len(PUZZLES) else url_for("puzzle")

                    return jsonify(
                        {
                            "ok": submitted_answer.lower() == rebus["answer"].lower(),
                            "message": rebus_feedback[rebus_key]["message"],
                            "status": rebus_feedback[rebus_key]["status"],
                            "rebus_key": rebus_key,
                            "all_correct": all_correct,
                            "next_url": next_url
                        }
                    )
        elif current_puzzle.get("type") == "progressive_single":
            is_async_request = request.headers.get("X-Requested-With") == "XMLHttpRequest"
            submitted_answers["answer"] = request.form.get("answer", "").strip()
            single_answers[puzzle_key] = submitted_answers["answer"]
            session["single_answers"] = single_answers
            all_correct = submitted_answers["answer"].lower() == current_puzzle["answer"].lower()

            if all_correct and is_async_request:
                session["level"] = level + 1
                single_attempts.pop(puzzle_key, None)
                single_answers.pop(puzzle_key, None)
                session["single_attempts"] = single_attempts
                session["single_answers"] = single_answers
                next_url = url_for("final") if session["level"] >= len(PUZZLES) else url_for("puzzle")
                return jsonify(
                    {
                        "ok": True,
                        "message": "Correct! Open the next clue.",
                        "status": "success",
                        "hints": [],
                        "next_url": next_url
                    }
                )

            if not all_correct:
                attempts = single_attempts.get(puzzle_key, 0) + 1
                single_attempts[puzzle_key] = attempts
                session["single_attempts"] = single_attempts
                progressive_hints = []
                if attempts >= 1:
                    progressive_hints.append(current_puzzle["hint1"])
                if attempts >= 2:
                    progressive_hints.append(current_puzzle["hint2"])
                single_feedback = "Nope. Try decoding it again."

                if is_async_request:
                    return jsonify(
                        {
                            "ok": False,
                            "message": single_feedback,
                            "status": "hint",
                            "hints": progressive_hints,
                            "next_url": None
                        }
                    )
        else:
            submitted_answers["answer"] = request.form.get("answer", "").strip()
            all_correct = submitted_answers["answer"].lower() == current_puzzle["answer"].lower()

        if all_correct:
            session["level"] = level + 1
            session["rebus_progress"] = {}
            session["rebus_answers"] = {}
            session["single_attempts"] = {}
            session["single_answers"] = {}

            if session["level"] >= len(PUZZLES):
                return redirect(url_for("final"))

            return redirect(url_for("puzzle"))


    return render_template(
        "puzzle.html",
        puzzle=current_puzzle,
        error=error,
        submitted_answers=submitted_answers,
        rebus_feedback=rebus_feedback,
        rebus_progress=rebus_progress,
        single_feedback=single_feedback,
        progressive_hints=progressive_hints
    )


@app.route("/final")
def final():
    if session.get("level", 0) < len(PUZZLES):
        return redirect(url_for("puzzle"))

    return render_template("final.html")


@app.route("/finish")
def finish():
    if session.get("level", 0) < len(PUZZLES) - 1:
        return redirect(url_for("puzzle"))

    session["level"] = len(PUZZLES)
    return redirect(url_for("final"))


@app.route("/celebrate")
def celebrate():
    if session.get("level", 0) < len(PUZZLES):
        return redirect(url_for("puzzle"))

    return render_template("celebrate.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5050"))
    app.run(debug=True, host="127.0.0.1", port=port)
