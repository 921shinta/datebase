from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Flask アプリの初期設定
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bbs.db'
db = SQLAlchemy(app)

# Flask-Login の初期設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ユーザーモデル
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

# 投稿モデル
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # 投稿日時
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('posts', lazy=True))
    
    comments = db.relationship('Comment', backref='post', cascade="all, delete-orphan")

# コメントモデル
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # コメント日時
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    user = db.relationship('User', backref=db.backref('comments', lazy=True))

# ログイン時にユーザー情報をロードする関数
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# トップページのルート
@app.route("/")
def index():
    # 投稿を新しい順に並べ替えて取得
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template("index.html", posts=posts)

# ユーザー登録
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])  # パスワードをハッシュ化
        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash("このユーザー名はすでに使われています。")
            return redirect(url_for("register"))

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()

        flash("登録が完了しました！ログインしてください。")
        return redirect(url_for("login"))

    return render_template("register.html")

# ログイン
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("ログイン成功！")
            return redirect(url_for("index"))

        flash("ユーザー名またはパスワードが違います。")
    
    return render_template("login.html")

# ログアウト
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("ログアウトしました。")
    return redirect(url_for("index"))

# 新規投稿
@app.route("/post", methods=["GET", "POST"])
@login_required
def post():
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        new_post = Post(title=title, content=content, user_id=current_user.id)
        db.session.add(new_post)
        db.session.commit()
        flash("投稿が完了しました！")
        return redirect(url_for("index"))
    
    return render_template("post.html")

# 投稿更新
@app.route("/update_post/<int:post_id>", methods=["GET", "POST"])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # 投稿者のみ更新できるようにする
    if post.user_id != current_user.id:
        flash("この投稿を編集する権限がありません。")
        return redirect(url_for("index"))
    
    if request.method == "POST":
        post.title = request.form["title"]
        post.content = request.form["content"]
        db.session.commit()
        flash("投稿が更新されました。")
        return redirect(url_for("index"))
    
    return render_template("update_post.html", post=post)

# 投稿削除
@app.route("/delete_post/<int:post_id>", methods=["POST"])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        flash("この投稿を削除する権限がありません。")
        return redirect(url_for("index"))
    
    db.session.delete(post)
    db.session.commit()
    flash("投稿を削除しました。")
    return redirect(url_for("index"))

# コメント追加
@app.route("/add_comment/<int:post_id>", methods=["POST"])
@login_required
def add_comment(post_id):
    content = request.form["content"]
    
    # コメントを追加する投稿を取得
    post = Post.query.get_or_404(post_id)
    
    # コメントに post_id と user_id を紐づける
    new_comment = Comment(content=content, user_id=current_user.id, post_id=post.id)
    
    db.session.add(new_comment)
    db.session.commit()
    flash("コメントを追加しました。")
    return redirect(url_for("index"))

# 投稿検索機能
@app.route("/search")
def search():
    query = request.args.get("query")
    results = Post.query.filter(Post.title.contains(query) | Post.content.contains(query)).all()
    return render_template("search_results.html", posts=results)

# アプリケーションのエントリーポイント
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)  # 外部アクセスも許可
