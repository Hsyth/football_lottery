from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import random

app = Flask(__name__)
app.secret_key = "fc_lottery_secret"

DB_PATH = "players.db"

# =====================
# 配置区（只改这里）
# =====================

# 已经拿过“第一大奖”的人（永远不进抽奖池）
EXCLUDED_PLAYERS = {
    "方涛",
    "许振扬",
    "唐文增"
}

# 一等奖内定
PRESET_FIRST_PRIZE = "张宇健"

# =====================
# 数据库
# =====================

def get_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        prize TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# =====================
# 注册页
# =====================

@app.route("/", methods=["GET", "POST"])
def register():
    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("名字不能为空")
        else:
            c.execute("INSERT INTO players (name) VALUES (?)", (name,))
            conn.commit()
            flash("注册成功")

        return redirect(url_for("register"))

    c.execute("SELECT name FROM players")
    players = [row[0] for row in c.fetchall()]
    conn.close()

    return render_template("register.html", players=players)

# =====================
# 后台工具函数
# =====================

def deduplicate_players():
    """按名字去重，只保留最早一条"""
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

def get_draw_pool():
    """构建真实抽奖池"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name FROM players WHERE prize IS NULL")
    names = [row[0] for row in c.fetchall()]
    conn.close()

    pool = []
    for n in names:
        if n not in EXCLUDED_PLAYERS:
            pool.append(n)
    return pool

# =====================
# 管理 / 抽奖页
# =====================

@app.route("/admin", methods=["GET", "POST"])
def admin():
    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        action = request.form.get("action")

        # ① 去重
        if action == "dedupe":
            deduplicate_players()
            flash("已按名字清理重复注册")
            return redirect(url_for("admin"))

        # ② 抽奖
        if action == "draw":
            prize = request.form.get("prize")

            # 一等奖内定
            if prize == "一等奖":
                c.execute(
                    "UPDATE players SET prize=? WHERE name=?",
                    (prize, PRESET_FIRST_PRIZE)
                )
                conn.commit()
                flash(f"一等奖：{PRESET_FIRST_PRIZE}")
                return redirect(url_for("admin"))

            pool = get_draw_pool()
            if not pool:
                flash("没有可抽奖的人")
                return redirect(url_for("admin"))

            winner = random.choice(pool)
            c.execute(
                "UPDATE players SET prize=? WHERE name=?",
                (prize, winner)
            )
            conn.commit()
            flash(f"{prize}：{winner}")
            return redirect(url_for("admin"))

        # ③ 重置抽奖
        if action == "reset":
            c.execute("UPDATE players SET prize=NULL")
            conn.commit()
            flash("已重置抽奖结果（不清注册）")
            return redirect(url_for("admin"))

    # 页面数据
    c.execute("SELECT name, prize FROM players")
    rows = c.fetchall()
    conn.close()

    all_players = [r[0] for r in rows]
    winners = [(r[0], r[1]) for r in rows if r[1]]
    unawarded = [r[0] for r in rows if not r[1] and r[0] not in EXCLUDED_PLAYERS]

    return render_template(
        "admin.html",
        all_players=all_players,
        winners=winners,
        unawarded=unawarded,
        excluded=EXCLUDED_PLAYERS
    )

if __name__ == "__main__":
    app.run(debug=True)