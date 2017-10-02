from flask import Flask, render_template, redirect, request, session, flash
from mysqlconnection import MySQLConnector
import re
from datetime import datetime
import os, binascii
import md5
LETTER_REGEX = re.compile(r"^[a-zA-Z]+$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$")
app = Flask(__name__)
app.secret_key = "KeepItSecretKeepItSafe"
mysql = MySQLConnector(app,'project_board')
@app.route("/")
def form():
    if "id" in session:
        print session["id"]
        return redirect("/dashboard")
    else:
        return render_template("index.html")
@app.route("/reg", methods=["POST"])
def reg():
    valid = True
    if len(request.form["first_name"]) < 1:
        flash("First name must not be blank!", "reg")
        valid = False
    elif not LETTER_REGEX.match(request.form["first_name"]):
        flash("First name must be alphabetic characters only!", "reg")
        valid = False
    if len(request.form["last_name"]) < 1:
        flash("Last name cannot be blank!", "reg")
        valid = False
    elif not LETTER_REGEX.match(request.form["last_name"]):
        flash("Last name must be alphabetic characters only!", "reg")
        valid = False
    if len(request.form["email"]) < 1:
        flash("Email must not be blank!", "reg")
        valid = False
    elif not EMAIL_REGEX.match(request.form["email"]):
        flash("Invalid email!", "reg")
        valid = False
    else:
        query = "SELECT email FROM users WHERE email = :email"
        data = {"email":request.form["email"]}
        if mysql.query_db(query, data) != []:
            flash("An account with that email is already registered!", "reg")
            valid = False
    if len(request.form["birth_date"]) <1:
        flash("Birthdate must not be blank!")
        valid = False
    else:
        try:
            birth_date = datetime.strptime(request.form["birth_date"], "%Y-%m-%d")
            if birth_date > datetime.today():
                flash("Birthdate cannot be in the future!")
                valid = False
        except ValueError:
            flash("Invalid date!")
            valid = False
    if len(request.form["password"]) < 1:
        flash("Password must not be blank!", "reg")
        valid = False
    elif len(request.form["password"])<8:
        flash("Password must be at least 8 characters!", "reg")
        valid = False
    if len(request.form["confirm_password"]) < 1:
        flash("Password confirmation cannot be blank!", "reg")
        valid = False
    elif request.form["password"] != request.form["confirm_password"]:
        flash("Password confirmation must match password!", "reg")
        valid = False
    if valid:
        salt = binascii.b2a_hex(os.urandom(15))
        hashed_password = md5.new(request.form["password"] + salt).hexdigest()
        query = "INSERT INTO users (first_name, last_name, email, birthdate, hashed_pw, salt, created_at, updated_at) VALUES (:first_name, :last_name, :email, :dob, :hashed_pw, :salt, NOW(), NOW())"
        data = {
            "first_name": request.form["first_name"],
            "last_name": request.form["last_name"],
            "email": request.form["email"],
            "dob": birth_date,
            "hashed_pw": hashed_password,
            "salt": salt
        }
        session["id"] = mysql.query_db(query, data)
        return redirect("/dashboard")
    return redirect("/")
@app.route("/log", methods=["POST"])
def log():
    valid = True
    if len(request.form["email"]) < 1:
        flash("Email must not be blank!", "log")
        valid = False
    elif not EMAIL_REGEX.match(request.form["email"]):
        flash("Invalid email!", "log")
        valid = False
    if len(request.form["password"]) < 1:
        flash("Password must not be blank!", "log")
        valid = False
    if valid:
        query = "SELECT id, hashed_pw, salt FROM users WHERE email = :email"
        data = {"email": request.form["email"]}
        pw_info = mysql.query_db(query, data)
        if pw_info == []:
            flash("Email not registered!", "log")
        elif md5.new(request.form["password"]+pw_info[0]["salt"]).hexdigest() == pw_info[0]["hashed_pw"]:
            session["id"]=pw_info[0]["id"]
            return redirect("/dashboard")
        else:
            flash("Email and password do not match!", "log")
    return redirect("/")
@app.route("/dashboard")
def dashboard():
    if "id" not in session:
        return redirect("/")
    query = "SELECT id, name, DATE_FORMAT(date_due, '%m/%d/%Y') as date_due, DATE_FORMAT(date_completed, '%m/%d/%Y') as date_completed FROM projects WHERE user_id = :user_id"
    data = {"user_id" : session["id"]}
    all_projects = mysql.query_db(query, data)
    return render_template("dashboard.html", all_projects=all_projects)
@app.route("/logout")
def logout():
    session.pop("id")
    return redirect("/")
@app.route("/show/<project_id>")
def show(project_id):
    if "id" not in session:
        return redirect("/")
    query = "SELECT name, description, DATE_FORMAT(date_due, '%m/%d/%Y') as date_due, DATE_FORMAT(date_completed, '%m/%d/%Y') as date_completed FROM projects WHERE id = :id and user_id = :user_id"
    data = {
        "id":int(project_id),
        "user_id":session["id"]
        }
    project = mysql.query_db(query, data)
    print project
    return render_template("details.html", project=project[0])
@app.route("/add")
def add():
    if "id" not in session:
        return redirect("/")
    return render_template("add.html")
@app.route("/create", methods=["POST"])
def create():
    if "id" not in session:
        return redirect("/")
    valid=True
    if len(request.form["name"])<1:
        flash("Project name cannot be blank")
        valid=False
    try:
        if datetime.strptime(request.form["date_due"], "%Y-%m-%d") < datetime.today():
            flash("Deadline must be in the future")
            valid=False
    except ValueError:
        flash("Deadline date not valid")
        valid=False
    if valid:
        query = "INSERT INTO projects (name, date_due, description, user_id, created_at, updated_at) VALUES (:name, :date_due, :description, :user_id, NOW(), NOW())"
        data = {
            "name" : request.form["name"],
            "date_due" : datetime.strptime(request.form["date_due"], "%Y-%m-%d"),
            "description" : request.form["description"],
            "user_id" : session["id"],
        }
        newproject = mysql.query_db(query, data)
        return redirect("/show/"+str(newproject))
    return redirect("/add")
@app.route("/destroy/<project_id>")
def delete(project_id):
    if "id" not in session:
        return redirect("/")
    query = "SELECT date_completed FROM projects WHERE id = :id AND user_id = :user_id"
    data = {
        "id" : int(project_id),
        "user_id":session["id"]
        }
    if mysql.query_db(query, data)[0]["date_completed"]:
        return redirect("/dashboard")
    query = "DELETE FROM projects WHERE id=:id"
    mysql.query_db(query, data)
    return redirect("/dashboard")
@app.route("/update/<project_id>")
def update(project_id):
    if "id" not in session:
        return redirect("/")
    query = "UPDATE projects SET date_completed = NOW(), updated_at = NOW() WHERE id = :id AND user_id = :user_id"
    data = {
        "id" : int(project_id),
        "user_id":session["id"]
        }
    mysql.query_db(query, data)
    return redirect("/dashboard")
app.run(debug=True)