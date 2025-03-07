from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = "your_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    skillset = db.Column(db.String(200), nullable=False)
    salary = db.Column(db.String(100), nullable=False)
    employer = db.Column(db.String(100), nullable=False)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = bcrypt.generate_password_hash(request.form["password"]).decode("utf-8")
        user = User(name=name, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    jobs = Job.query.all()
    return render_template("dashboard.html", jobs=jobs)

@app.route("/post_job", methods=["POST"])
def post_job():
    if "user_id" not in session:
        return redirect(url_for("login"))
    title = request.form["title"]
    skillset = request.form["skillset"]
    salary = request.form["salary"]
    employer = session["user_id"]
    job = Job(title=title, skillset=skillset, salary=salary, employer=employer)
    db.session.add(job)
    db.session.commit()
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
