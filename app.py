from flask import Flask, render_template, request, redirect, session, jsonify
from dotenv import load_dotenv
from datetime import timedelta
import os
import pyrebase
from flask_wtf.csrf import CSRFProtect
import re

# Load environment variables from .env file
load_dotenv()

# Firebase config from env
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

# Secure session settings
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max request size
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

@app.before_request
def make_session_permanent():
    session.permanent = True

# Route: Home (login page)
@app.route("/")
def home():
    return render_template("login.html")

# Route: Login
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

# Utility: sanitize Firebase keys
def sanitize_key(key):
    return re.sub(r"[.#$/\[\]]", "-", key.strip())

# Route: Dashboard
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

    # GET: Fetch user's posts
    posts = db.child("posts").child(user_id).get(id_token).val()
    return render_template("dashboard.html", posts=posts)

# Route: Receive and save paragraph preview
@app.route("/send_to_firebase", methods=["POST"])
def send_to_firebase():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user"]
    id_token = session["id_token"]

    data = request.get_json()
    content = data.get("content", "").strip()

    if not content:
        return jsonify({"error": "No content provided"}), 400

    try:
        # Save preview content under 'paragraphPreview/user_id'
        db.child("paragraphPreview").child(user_id).set({
            "content": content
        }, id_token)
        return jsonify({"message": "Content saved successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run the app
if __name__ == "__main__":
    app.run(debug=False)
