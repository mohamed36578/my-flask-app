from flask import Flask, render_template, request, redirect, session
from dotenv import load_dotenv
from datetime import timedelta
import os
import pyrebase
from flask_wtf.csrf import CSRFProtect
import re

# Load environment variables
load_dotenv()

# Firebase config
config = {
    "apiKey": os.getenv("API_KEY"),
    "authDomain": os.getenv("AUTH_DOMAIN"),
    "databaseURL": os.getenv("DATABASE_URL"),
    "storageBucket": os.getenv("STORAGE_BUCKET"),
}

# Initialize Firebase and Flask
firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
csrf = CSRFProtect(app)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        session["user"] = user["localId"]
        session["id_token"] = user["idToken"]
        return redirect("/dashboard")
    except:
        return "Invalid email or password"

def sanitize_key(key):
    # Replace Firebase-restricted characters with "-"
    return re.sub(r"[.#$/\[\]]", "-", key.strip())

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/")

    user_id = session["user"]
    id_token = session["id_token"]

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if not title:
            return "Title is required."

        sanitized_title = sanitize_key(title)

        data = {
            "title": title,
            "content": content
        }

        db.child("posts").child(user_id).child(sanitized_title).set(data, id_token)

        return redirect("/dashboard")

    # GET: Display posts
    posts = db.child("posts").child(user_id).get(id_token).val()
    return render_template("dashboard.html", posts=posts)

if __name__ == "__main__":
    app.run(debug=False)
