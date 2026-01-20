from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import random
import os

app = Flask(__name__)

# 数据库配置（本地 SQLite / 云端 PostgreSQL 自动切换）
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 'sqlite:///players.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 数据表
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    number = db.Column(db.String(10), unique=True, nullable=False)
    prize = db.Column(db.String(20))

# Flask 3.x 正确建表方式
with app.app_context():
    db.create_all()

# 注册页
@app.route('/', methods=['GET', 'POST'])
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        number = request.form.get('number')

        if not name or not number:
            return '信息不完整'

        if Player.query.filter_by(number=number).first():
            return '球衣号已存在'

        db.session.add(Player(name=name, number=number))
        db.session.commit()
        return '注册成功'

    return render_template('register.html')

# 管理页
@app.route('/admin')
def admin():
    return render_template('admin.html')

# 抽奖接口
@app.route('/draw/<prize>/<int:count>')
def draw(prize, count):
    pool = Player.query.filter_by(prize=None).all()
    if not pool:
        return '没有可抽奖人员'

    winners = random.sample(pool, min(count, len(pool)))
    for w in winners:
        w.prize = prize

    db.session.commit()

    return '<br>'.join([f'{w.name}（{w.number}号）' for w in winners])

# 本地运行
if __name__ == '__main__':
    app.run(debug=True)