from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key" 
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["UPLOAD_FOLDER"] = "uploads"  
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    profile_photo = db.Column(db.String(200), nullable=True)
    dob = db.Column(db.Date, nullable=True)  
    phone = db.Column(db.String(15), nullable=True)  
    gender = db.Column(db.String(10), nullable=True)  


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    salary = db.Column(db.String(100), nullable=False)
    skills_required = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    posted_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class JobSeeker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    skills = db.Column(db.String(200), nullable=False)
    expected_salary = db.Column(db.String(100), nullable=False)
    cv_filename = db.Column(db.String(200), nullable=False)
    photo_filename = db.Column(db.String(200), nullable=False)


class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    job_seeker_id = db.Column(db.Integer, db.ForeignKey("job_seeker.id"), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="pending") 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")


        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return "Email already registered. Please use a different email."


        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")


        profile_photo = None
        if "profile_photo" in request.files:
            file = request.files["profile_photo"]
            if file.filename != "":
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                profile_photo = filename


        new_user = User(name=name, email=email, password=hashed_password, profile_photo=profile_photo)
        db.session.add(new_user)
        db.session.commit()


        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json() 
        email = data.get("email")
        password = data.get("password")

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session["user_id"] = user.id
            return redirect(url_for("dashboard")) 
        else:
            return jsonify({"error": "Invalid email or password. Please try again."}), 401  

    return render_template("login.html")


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

    job_seeker = JobSeeker.query.filter_by(user_id=user.id).first()
    job_applications = []
    if job_seeker:
        job_applications = JobApplication.query.filter_by(job_seeker_id=job_seeker.id).all()

    jobs_posted = Job.query.filter_by(posted_by=user.id).all()
    employer_applications = []
    for job in jobs_posted:
        applications = JobApplication.query.filter_by(job_id=job.id).all()
        for application in applications:
            if application.status in ["contacted", "accepted", "rejected"]: 
                job_seeker = JobSeeker.query.get(application.job_seeker_id)
                employer_applications.append({
                    "job_seeker_name": job_seeker.name,
                    "status": application.status
                })

    if request.method == "POST":

        if "profile_photo" in request.files:
            file = request.files["profile_photo"]
            if file.filename != "":

                os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)


                user.profile_photo = filename
                db.session.commit()
                flash("Profile photo updated successfully!", "success")


        user.name = request.form.get("name", user.name)
        user.email = request.form.get("email", user.email)
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))


    return render_template(
        "profile.html",
        user=user,
        job_applications=job_applications,
        employer_applications=employer_applications,
        Job=Job
    )


@app.route("/apply_job/<int:job_id>", methods=["POST"])
def apply_job(job_id):
    if "user_id" not in session:
        return redirect(url_for("login"))


    job_seeker = JobSeeker.query.filter_by(user_id=session["user_id"]).first()
    if not job_seeker:
        flash("You are not registered as a job seeker.", "error")
        return redirect(url_for("get_hired"))

    job = Job.query.get(job_id)
    if not job:
        flash("Job not found.", "error")
        return redirect(url_for("get_hired"))

    existing_application = JobApplication.query.filter_by(job_id=job_id, job_seeker_id=job_seeker.id).first()
    if existing_application:
        flash("You have already applied for this job.", "error")
        return redirect(url_for("get_hired"))


    new_application = JobApplication(
        job_id=job_id,
        job_seeker_id=job_seeker.id,
        status="pending"  
    )
    db.session.add(new_application)
    db.session.commit()

    flash("You have successfully applied for the job!", "success")
    return redirect(url_for("get_hired"))


@app.route("/contact_job_seeker/<int:job_seeker_id>", methods=["POST"])
def contact_job_seeker(job_seeker_id):
    if "user_id" not in session:
        return redirect(url_for("login"))


    user = User.query.get(session["user_id"])
    if not user:
        flash("You are not logged in.", "error")
        return redirect(url_for("login"))


    job_seeker = JobSeeker.query.get(job_seeker_id)
    if not job_seeker:
        flash("Job seeker not found.", "error")
        return redirect(url_for("hire_person"))


    job_application = JobApplication.query.filter_by(job_seeker_id=job_seeker_id).first()
    if not job_application:
        flash("No application found for this job seeker.", "error")
        return redirect(url_for("hire_person"))


    job_application.status = "contacted"
    db.session.commit()

    flash("You have contacted the job seeker!", "success")
    return redirect(url_for("hire_person"))


@app.route("/get_hired")
def get_hired():
    if "user_id" not in session:
        return redirect(url_for("login"))

    jobs = Job.query.all()
    return render_template("get_hired.html", jobs=jobs)


@app.route("/hire_person")
def hire_person():
    if "user_id" not in session:
        return redirect(url_for("login"))

    job_seekers = JobSeeker.query.all()
    return render_template("hire_person.html", job_seekers=job_seekers)

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


@app.route("/post_requirements", methods=["POST"])
def post_requirements():
    if "user_id" not in session:
        return redirect(url_for("login"))

    name = request.form.get("name")
    skills = request.form.get("skills")
    salary = request.form.get("salary")
    cv_file = request.files["cv"]
    photo_file = request.files["photo"]


    cv_filename = secure_filename(cv_file.filename)
    photo_filename = secure_filename(photo_file.filename)

    cv_file.save(os.path.join(app.config["UPLOAD_FOLDER"], cv_filename))
    photo_file.save(os.path.join(app.config["UPLOAD_FOLDER"], photo_filename))

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

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  
    app.run(debug=True)