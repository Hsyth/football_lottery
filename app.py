from flask import Flask, render_template, request, redirect, session
import sqlite3
import random

app = Flask(__name__)
app.secret_key = "fc_lottery_secret_2026"

DB_PATH = "players.db"

# ========================
# 管理员密码
# ========================
ADMIN_PASSWORD = "fc2026"

# ========================
# 已拿过大奖（永久排除，页面不可见）
# ========================
EXCLUDED_NAMES = [
    "方涛",
    "许振扬",
    "唐文增"
]

# ========================
# 一等奖内定（姓名）
# ========================
PRESET_FIRST_PRIZE = "张宇健"


# ========================
# 数据库
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
# 注册页
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
            return render_template("admin_login.html", error="密码错误")

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

    # 未中奖 & 可抽
    placeholders = ",".join("?" * len(EXCLUDED_NAMES))
    c.execute(f"""
        SELECT name FROM players
        WHERE prize IS NULL
          AND name NOT IN ({placeholders})
          AND name != ?
    """, (*EXCLUDED_NAMES, PRESET_FIRST_PRIZE))
    available_players = [row["name"] for row in c.fetchall()]

    # 已中奖
    c.execute("SELECT name, prize FROM players WHERE prize IS NOT NULL")
    winners = c.fetchall()

    # 全部注册人员（仅管理员）
    c.execute("SELECT id, name, prize FROM players")
    all_players = c.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        available_players=available_players,
        winners=winners,
        all_players=all_players
    )


# ========================
# 抽奖
# ========================
@app.route("/draw", methods=["POST"])
def draw():
    if not session.get("admin_logged_in"):
        return redirect("/admin_login")

    prize = request.form.get("prize")

    conn = get_db()
    c = conn.cursor()

    # 一等奖：内定
    if prize == "一等奖":
        c.execute("SELECT prize FROM players WHERE name = ?", (PRESET_FIRST_PRIZE,))
        row = c.fetchone()
        if row and row["prize"] is None:
            c.execute(
                "UPDATE players SET prize = ? WHERE name = ?",
                (prize, PRESET_FIRST_PRIZE)
            )
            conn.commit()
        conn.close()
        return redirect("/admin")

    # 其他奖项：随机
    placeholders = ",".join("?" * len(EXCLUDED_NAMES))
    c.execute(f"""
        SELECT name FROM players
        WHERE prize IS NULL
          AND name NOT IN ({placeholders})
          AND name != ?
    """, (*EXCLUDED_NAMES, PRESET_FIRST_PRIZE))

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
# 删除注册人员（管理员）
# ========================
@app.route("/delete_player/<int:pid>", methods=["POST"])
def delete_player(pid):
    if not session.get("admin_logged_in"):
        return redirect("/admin_login")

    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM players WHERE id = ?", (pid,))
    conn.commit()
    conn.close()
    return redirect("/admin")


# ========================
# 重置抽奖（不清注册）
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