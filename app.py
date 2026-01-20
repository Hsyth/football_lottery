from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import random
import os

app = Flask(__name__)
DB_NAME = "players.db"


# ======================
# 初始化数据库
# ======================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            number INTEGER NOT NULL,
            prize TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


# ======================
# 工具函数
# ======================
def get_all_unwon_players():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name, number FROM players WHERE prize IS NULL")
    data = c.fetchall()
    conn.close()
    return data


def draw_winner(prize):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, number FROM players WHERE prize IS NULL")
    candidates = c.fetchall()

    if not candidates:
        conn.close()
        return None

    winner = random.choice(candidates)
    c.execute("UPDATE players SET prize=? WHERE id=?", (prize, winner[0]))
    conn.commit()
    conn.close()

    return winner[1], winner[2]


def get_remaining_count():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM players WHERE prize IS NULL")
    count = c.fetchone()[0]
    conn.close()
    return count


def get_prize_status():
    prize_total = {
        "一等奖": 3,
        "二等奖": 5,
        "三等奖": 5
    }

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    result = {}

    for prize, total in prize_total.items():
        c.execute("SELECT COUNT(*) FROM players WHERE prize=?", (prize,))
        used = c.fetchone()[0]
        result[prize] = {
            "used": used,
            "total": total,
            "left": total - used
        }

    conn.close()
    return result


def reset_lottery():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE players SET prize = NULL")
    conn.commit()
    conn.close()


# ======================
# 路由
# ======================
@app.route("/", methods=["GET", "POST"])
def register():
    msg = None
    if request.method == "POST":
        name = request.form["name"]
        number = request.form["number"]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(
            "INSERT INTO players (name, number) VALUES (?, ?)",
            (name, number)
        )
        conn.commit()
        conn.close()

        msg = "✅ 注册成功，已进入抽奖池"

    return render_template("register.html", message=msg)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    winner = None

    if request.method == "POST":
        prize = request.form["prize"]
        winner = draw_winner(prize)

    players = get_all_unwon_players()
    remaining = get_remaining_count()
    prize_info = get_prize_status()

    return render_template(
        "admin.html",
        winner=winner,
        players=players,
        remaining=remaining,
        prize_info=prize_info
    )


@app.route("/reset", methods=["POST"])
def reset():
    reset_lottery()
    return redirect(url_for("admin"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)