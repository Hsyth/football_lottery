from flask import Flask, render_template, request, redirect, session
import sqlite3
import random
import os

app = Flask(__name__)
app.secret_key = "fc_lottery_secret_2026"

DB_PATH = "players.db"

# ========================
# 管理员密码（只你知道）
# ========================
ADMIN_PASSWORD = "QSFC2025"

# ========================
# 已拿大奖，永久排除（后台不可见）
# ========================
EXCLUDED_NAMES = [
    "方涛",
    "许振扬",
    "唐文增"
]

# ========================
# 一等奖内定（按名字）
# ========================
PRESET_FIRST_PRIZE = "张宇健"


# ========================
# 数据库工具
# ========================
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
            name TEXT UNIQUE,
            prize TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


# ========================
# 注册页面
# ========================
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
                c.execute(
                    "INSERT INTO players (name, prize) VALUES (?, NULL)",
                    (name,)
                )
                conn.commit()
                message = "注册成功"

            conn.close()

    return render_template("register.html", message=message)


# ========================
# 管理员登录
# ========================
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        pwd = request.form.get("password")
        if pwd == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect("/admin")
        else:
            return render_template(
                "admin_login.html",
                error="密码错误"
            )
    return render_template("admin_login.html")


@app.route("/admin_logout")
def admin_logout():
    session.clear()
    return redirect("/")


# ========================
# 管理后台
# ========================
@app.route("/admin")
def admin():
    if not session.get("admin_logged_in"):
        return redirect("/admin_login")

    conn = get_db()
    c = conn.cursor()

    # 可抽名单：未中奖 + 不在排除名单 + 非内定一等奖
    c.execute("""
        SELECT name FROM players
        WHERE prize IS NULL
          AND name NOT IN ({})
          AND name != ?
    """.format(",".join("?" * len(EXCLUDED_NAMES))),
              (*EXCLUDED_NAMES, PRESET_FIRST_PRIZE))

    available_players = [row["name"] for row in c.fetchall()]

    # 已中奖
    c.execute("SELECT name, prize FROM players WHERE prize IS NOT NULL")
    winners = c.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        available_players=available_players,
        winners=winners
    )


# ========================
# 抽奖逻辑
# ========================
@app.route("/draw", methods=["POST"])
def draw():
    if not session.get("admin_logged_in"):
        return redirect("/admin_login")

    prize = request.form.get("prize")

    conn = get_db()
    c = conn.cursor()

    # 一等奖内定
    if prize == "一等奖":
        c.execute(
            "SELECT prize FROM players WHERE name = ?",
            (PRESET_FIRST_PRIZE,)
        )
        row = c.fetchone()
        if row and row["prize"] is None:
            c.execute(
                "UPDATE players SET prize = ? WHERE name = ?",
                (prize, PRESET_FIRST_PRIZE)
            )
            conn.commit()
        conn.close()
        return redirect("/admin")

    # 其他奖项随机
    c.execute("""
        SELECT name FROM players
        WHERE prize IS NULL
          AND name NOT IN ({})
          AND name != ?
    """.format(",".join("?" * len(EXCLUDED_NAMES))),
              (*EXCLUDED_NAMES, PRESET_FIRST_PRIZE))

    candidates = [row["name"] for row in c.fetchall()]

    if candidates:
        winner = random.choice(candidates)
        c.execute(
            "UPDATE players SET prize = ? WHERE name = ?",
            (prize, winner)
        )
        conn.commit()

    conn.close()
    return redirect("/admin")


# ========================
# 清理重复注册（兜底）
# ========================
@app.route("/clean_duplicates", methods=["POST"])
def clean_duplicates():
    if not session.get("admin_logged_in"):
        return redirect("/admin_login")

    conn = get_db()
    c = conn.cursor()
    c.execute("""
        DELETE FROM players
        WHERE id NOT IN (
            SELECT MIN(id) FROM players GROUP BY name
        )
    """)
    conn.commit()
    conn.close()
    return redirect("/admin")


# ========================
# 重置抽奖（不清空注册）
# ========================
@app.route("/reset_lottery", methods=["POST"])
def reset_lottery():
    if not session.get("admin_logged_in"):
        return redirect("/admin_login")

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE players SET prize = NULL")
    conn.commit()
    conn.close()
    return redirect("/admin")


# ========================
# 启动
# ========================
if __name__ == "__main__":
    app.run(debug=True)