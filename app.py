from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import random
import os

app = Flask(__name__)

DB_PATH = "players.db"

# ======== 配置区（只改这里） ========

# 已获得大奖，永久排除（不显示、不参与抽奖）
EXCLUDED_PLAYERS = {
    "方涛",
    "许振扬",
    "唐文增"
}

# 一等奖内定（必须在注册名单中）
PRESET_FIRST_PRIZE = "张宇健"

# 奖项顺序
PRIZES = ["一等奖", "二等奖", "三等奖"]

# ===================================


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            prize TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


# ============ 注册页 ============

@app.route("/", methods=["GET", "POST"])
def register():
    message = ""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            message = "请输入姓名"
        else:
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM players WHERE name = ?", (name,))
            exists = c.fetchone()[0]
            if exists:
                message = "该姓名已注册"
            else:
                c.execute("INSERT INTO players (name) VALUES (?)", (name,))
                conn.commit()
                message = "注册成功"
            conn.close()

    return render_template("register.html", message=message)


# ============ 管理页 ============

@app.route("/admin")
def admin():
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM players WHERE prize IS NULL")
    all_available = [row["name"] for row in c.fetchall()]

    # 抽奖池：去重 + 排除大奖获得者
    available_players = sorted(set(all_available) - EXCLUDED_PLAYERS)

    c.execute("SELECT name, prize FROM players WHERE prize IS NOT NULL")
    winners = c.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        available_players=available_players,
        winners=winners
    )


# ============ 清理重复注册 ============

@app.route("/clean_duplicates", methods=["POST"])
def clean_duplicates():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        DELETE FROM players
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM players
            GROUP BY name
        )
    """)
    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


# ============ 重置抽奖 ============

@app.route("/reset_lottery", methods=["POST"])
def reset_lottery():
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE players SET prize = NULL")
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


# ============ 抽奖 ============

@app.route("/draw", methods=["POST"])
def draw():
    prize = request.form.get("prize")

    conn = get_db()
    c = conn.cursor()

    # 一等奖内定
    if prize == "一等奖":
        c.execute(
            "UPDATE players SET prize = ? WHERE name = ? AND prize IS NULL",
            (prize, PRESET_FIRST_PRIZE)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("admin"))

    # 普通抽奖
    c.execute("SELECT name FROM players WHERE prize IS NULL")
    candidates = {row["name"] for row in c.fetchall()}
    candidates -= EXCLUDED_PLAYERS

    if not candidates:
        conn.close()
        return redirect(url_for("admin"))

    winner = random.choice(list(candidates))
    c.execute(
        "UPDATE players SET prize = ? WHERE name = ?",
        (prize, winner)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(debug=True)