from flask import Flask, render_template, request, redirect, url_for, session,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a secure secret key
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Job Model
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    skillset = db.Column(db.String(200), nullable=False)
    salary = db.Column(db.String(100), nullable=False)
    employer = db.Column(db.String(100), nullable=False)

# Home Route
@app.route("/")
def home():
    return render_template("index.html")

# Register Route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        # Check if the email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return "Email already registered. Please use a different email."

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        # Create a new user
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        # Redirect to login page after successful registration
        return redirect(url_for("login"))

    return render_template("register.html")

# Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json()  # Get JSON data from the request
        email = data.get("email")
        password = data.get("password")

        # Check if the user exists
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))  # Redirect to dashboard
        else:
            return jsonify({"error": "Invalid email or password. Please try again."}), 401  # Return error message

    return render_template("login.html")

# Dashboard Route
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    jobs = Job.query.all()
    return render_template("dashboard.html", jobs=jobs)

# Post Job Route
@app.route("/post_job", methods=["POST"])
def post_job():
    if "user_id" not in session:
        return redirect(url_for("login"))

    title = request.form.get("title")
    skillset = request.form.get("skillset")
    salary = request.form.get("salary")
    employer = session["user_id"]

    # Create a new job
    new_job = Job(title=title, skillset=skillset, salary=salary, employer=employer)
    db.session.add(new_job)
    db.session.commit()

    return redirect(url_for("dashboard"))

# Run the application
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)