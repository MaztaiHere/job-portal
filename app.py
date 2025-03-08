from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a secure secret key
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["UPLOAD_FOLDER"] = "uploads"  # Folder to store uploaded files
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Ensure the upload folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    profile_photo = db.Column(db.String(200), nullable=True)  # New column for profile photo

# Job Model
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    salary = db.Column(db.String(100), nullable=False)
    skills_required = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    posted_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

# JobSeeker Model (to store job seeker details)
class JobSeeker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    skills = db.Column(db.String(200), nullable=False)
    expected_salary = db.Column(db.String(100), nullable=False)
    cv_filename = db.Column(db.String(200), nullable=False)
    photo_filename = db.Column(db.String(200), nullable=False)

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

        # Handle profile photo upload during registration
        profile_photo = None
        if "profile_photo" in request.files:
            file = request.files["profile_photo"]
            if file.filename != "":
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                profile_photo = filename

        # Create a new user
        new_user = User(name=name, email=email, password=hashed_password, profile_photo=profile_photo)
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
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])

    if request.method == "POST":
        # Handle profile photo upload
        if "profile_photo" in request.files:
            file = request.files["profile_photo"]
            if file.filename != "":
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                user.profile_photo = filename  # Save the filename in the database
                db.session.commit()
                flash("Profile photo updated successfully!", "success")

        # Handle other profile updates (e.g., name, email, etc.)
        user.name = request.form.get("name", user.name)
        user.email = request.form.get("email", user.email)
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user)

# Get Hired Route
@app.route("/get_hired")
def get_hired():
    if "user_id" not in session:
        return redirect(url_for("login"))

    jobs = Job.query.all()
    return render_template("get_hired.html", jobs=jobs)

# Hire a Person Route
@app.route("/hire_person")
def hire_person():
    if "user_id" not in session:
        return redirect(url_for("login"))

    job_seekers = JobSeeker.query.all()
    return render_template("hire_person.html", job_seekers=job_seekers)

# Post Job Route (for companies)
@app.route("/post_job", methods=["POST"])
def post_job():
    if "user_id" not in session:
        return redirect(url_for("login"))

    title = request.form.get("title")
    description = request.form.get("description")
    location = request.form.get("location")
    salary = request.form.get("salary")
    skills_required = request.form.get("skills_required")
    company_name = request.form.get("company_name")

    # Create a new job
    new_job = Job(
        title=title,
        description=description,
        location=location,
        salary=salary,
        skills_required=skills_required,
        company_name=company_name,
        posted_by=session["user_id"]
    )
    db.session.add(new_job)
    db.session.commit()

    flash("Job posted successfully!", "success")
    return redirect(url_for("hire_person"))

# Post Requirements Route (for job seekers)
@app.route("/post_requirements", methods=["POST"])
def post_requirements():
    if "user_id" not in session:
        return redirect(url_for("login"))

    name = request.form.get("name")
    skills = request.form.get("skills")
    salary = request.form.get("salary")
    cv_file = request.files["cv"]
    photo_file = request.files["photo"]

    # Save files to the upload folder
    cv_filename = secure_filename(cv_file.filename)
    photo_filename = secure_filename(photo_file.filename)

    cv_file.save(os.path.join(app.config["UPLOAD_FOLDER"], cv_filename))
    photo_file.save(os.path.join(app.config["UPLOAD_FOLDER"], photo_filename))

    # Save job seeker details to the database
    job_seeker = JobSeeker(
        user_id=session["user_id"],
        name=name,
        skills=skills,
        expected_salary=salary,
        cv_filename=cv_filename,
        photo_filename=photo_filename
    )
    db.session.add(job_seeker)
    db.session.commit()

    flash("Your requirements have been submitted successfully!", "success")
    return redirect(url_for("get_hired"))

# Route to serve uploaded files
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# Run the application
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)