from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import random
import os

app = Flask(__name__)
app.secret_key = "football_lottery_secret"

DB_PATH = "players.db"

# =========================
# 配置区（只改这里就行）
# =========================

# 已经拿过大奖、但仍允许注册展示的球员（永远不进抽奖池）
EXCLUDED_PLAYERS = {
    "方涛",
    "唐文增",
    "许振扬"
}

# 一等奖内定球员（必须在注册名单中）
PRESET_FIRST_PRIZE = "张宇健"

# =========================
# 数据库初始化
# =========================

def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        prize TEXT DEFAULT NULL
    )
    """)
    conn.commit()
    conn.close()

init_db()

# =========================
# 工具函数
# =========================

def normalize_name(name: str) -> str:
    """统一名字格式，彻底防重复"""
    return name.strip().lower()

def display_name(name: str) -> str:
    """用于页面展示"""
    return name.capitalize()

# =========================
# 注册页面
# =========================

@app.route("/", methods=["GET", "POST"])
def register():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        raw_name = request.form.get("name", "")
        name = normalize_name(raw_name)

        if not name:
            flash("名字不能为空")
            return redirect(url_for("register"))

        try:
            cur.execute(
                "INSERT INTO players (name) VALUES (?)",
                (name,)
            )
            conn.commit()
            flash("注册成功")
        except sqlite3.IntegrityError:
            flash("该名字已注册，请勿重复注册")

        return redirect(url_for("register"))

    cur.execute("SELECT name FROM players")
    players = [display_name(row[0]) for row in cur.fetchall()]
    conn.close()

    return render_template("register.html", players=players)

# =========================
# 管理员 / 抽奖页面
# =========================

@app.route("/admin", methods=["GET", "POST"])
def admin():
    conn = get_db()
    cur = conn.cursor()

    # 所有注册用户
    cur.execute("SELECT name, prize FROM players")
    rows = cur.fetchall()

    all_players = []
    winners = []
    unawarded = []

    for name, prize in rows:
        show_name = display_name(name)

        all_players.append(show_name)

        if prize:
            winners.append((show_name, prize))
        else:
            # 排除已获大奖的人
            if show_name not in EXCLUDED_PLAYERS:
                unawarded.append(show_name)

    remaining_count = len(unawarded)

    if request.method == "POST":
        action = request.form.get("action")

        # ========= 抽奖 =========
        if action == "draw":
            prize = request.form.get("prize")

            # 一等奖：内定
            if prize == "一等奖":
                preset = normalize_name(PRESET_FIRST_PRIZE)
                cur.execute(
                    "UPDATE players SET prize = ? WHERE name = ? AND prize IS NULL",
                    (prize, preset)
                )
                conn.commit()
                flash(f"一等奖：{PRESET_FIRST_PRIZE}")
                return redirect(url_for("admin"))

            # 其他奖项：随机
            if not unawarded:
                flash("没有可抽奖的参与者")
                return redirect(url_for("admin"))

            winner = random.choice(unawarded)
            cur.execute(
                "UPDATE players SET prize = ? WHERE name = ?",
                (prize, normalize_name(winner))
            )
            conn.commit()
            flash(f"{prize}：{winner}")
            return redirect(url_for("admin"))

        # ========= 重置抽奖 =========
        if action == "reset":
            cur.execute("UPDATE players SET prize = NULL")
            conn.commit()
            flash("已重置抽奖结果（注册名单保留）")
            return redirect(url_for("admin"))

    conn.close()

    return render_template(
        "admin.html",
        all_players=all_players,
        winners=winners,
        unawarded=unawarded,
        remaining_count=remaining_count
    )

# =========================
# 启动
# =========================

if __name__ == "__main__":
    app.run(debug=True)