from flask import Flask, render_template, request, redirect, session
import sqlite3
import random

app = Flask(__name__)
app.secret_key = "fc_lottery_secret_key"

# ===== 管理员密码 =====
ADMIN_PASSWORD = "QS2025"   # ← 自己改

# ===== 已获得大奖，永久排除抽奖（按姓名）=====
EXCLUDED_NAMES = ["方涛", "唐文增", "许振扬"]   # ← 改成真实姓名

# ===== 一等奖内定人员（按姓名）=====
FIXED_FIRST_PRIZE_NAME = "张宇健"   # ← 改成真实姓名

DB_PATH = "players.db"


# ===== 初始化数据库（姓名唯一，防重复注册）=====
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            number TEXT NOT NULL,
            prize TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


# ===== 注册页面 =====
@app.route("/register", methods=["GET", "POST"])
def register():
    msg = None
    if request.method == "POST":
        name = request.form.get("name")
        number = request.form.get("number")

        if not name or not number:
            msg = "请填写完整信息"
        else:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            try:
                c.execute(
                    "INSERT INTO players (name, number) VALUES (?, ?)",
                    (name.strip(), number.strip())
                )
                conn.commit()
                msg = "注册成功！"
            except sqlite3.IntegrityError:
                msg = "该姓名已注册，请勿重复报名"
            finally:
                conn.close()

    return render_template("register.html", msg=msg)


# ===== 管理员登录 =====
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect("/admin")
        else:
            error = "密码错误"
    return render_template("admin_login.html", error=error)


# ===== 抽奖管理页面 =====
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("admin_logged_in"):
        return redirect("/admin_login")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ===== 抽奖池（排除指定姓名）=====
    if EXCLUDED_NAMES:
        placeholders = ",".join(["?"] * len(EXCLUDED_NAMES))
        query = f"""
            SELECT name, number FROM players
            WHERE prize IS NULL
            AND name NOT IN ({placeholders})
        """
        c.execute(query, EXCLUDED_NAMES)
    else:
        c.execute("SELECT name, number FROM players WHERE prize IS NULL")

    players = c.fetchall()
    remaining = len(players)

    # ===== 奖项配置 =====
    prize_info = {
        "一等奖": {"total": 3, "left": 3},
        "二等奖": {"total": 5, "left": 5},
        "三等奖": {"total": 5, "left": 5},
    }

    for prize in prize_info:
        c.execute("SELECT COUNT(*) FROM players WHERE prize = ?", (prize,))
        used = c.fetchone()[0]
        prize_info[prize]["left"] -= used

    winner = None

    # ===== 抽奖逻辑 =====
    if request.method == "POST":
        prize = request.form.get("prize")

        # 🎯 一等奖内定
        if prize == "一等奖":
            c.execute(
                "SELECT name, number FROM players WHERE name = ? AND prize IS NULL",
                (FIXED_FIRST_PRIZE_NAME,)
            )
            fixed = c.fetchone()
            if fixed:
                winner = fixed
                c.execute(
                    "UPDATE players SET prize = ? WHERE name = ?",
                    (prize, fixed[0])
                )
                conn.commit()

        # 🎯 普通随机抽奖
        if not winner and players and prize_info[prize]["left"] > 0:
            winner = random.choice(players)
            c.execute(
                "UPDATE players SET prize = ? WHERE name = ?",
                (prize, winner[0])
            )
            conn.commit()

    conn.close()

    return render_template(
        "admin.html",
        players=players,
        winner=winner,
        remaining=remaining,
        prize_info=prize_info,
        excluded_names=EXCLUDED_NAMES,
        fixed_first=FIXED_FIRST_PRIZE_NAME
    )


# ===== 重置抽奖（不清注册、不清规则）=====
@app.route("/reset", methods=["POST"])
def reset():
    if not session.get("admin_logged_in"):
        return redirect("/admin_login")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE players SET prize = NULL")
    conn.commit()
    conn.close()

    return redirect("/admin")


# ===== 管理员退出 =====
@app.route("/admin_logout")
def admin_logout():
    session.clear()
    return redirect("/admin_login")


if __name__ == "__main__":
    app.run(debug=True)