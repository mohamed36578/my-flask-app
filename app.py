from flask import Flask, render_template, request, redirect, session
from dotenv import load_dotenv
from datetime import timedelta
import os
import pyrebase
from flask_wtf.csrf import CSRFProtect


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
csrf = CSRFProtect(app)  # Change to something strong and secret in real apps
app.config['SESSION_COOKIE_SECURE'] = True         # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True       # No JS access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'      # Prevent CSRF
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB upload max
# Set session timeout to 30 minutes
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# You may also want to set your session to be permanent so that the timeout will be applied
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
        # Store Firebase ID token in the session
        id_token = user["idToken"]
        session["user"] = user["localId"]
        session["id_token"] = id_token  # Store the token for later use
        return redirect("/dashboard")
    except:
        return "Invalid email or password"

    
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/")

    user_id = session["user"]
    id_token = session["id_token"]

    if request.method == "POST":
        post_id = request.form.get("bgrInput")  # user-defined ID
        content = request.form.get('content').strip()

        data = {
            
            "content": content
        }

        # Replace or create a post at posts/user_id/post_id
        db.child("posts").child(user_id).child(post_id).set(data, id_token)

        return redirect("/dashboard")

    # Get all posts for the user
    posts = db.child("posts").child(user_id).get(id_token).val()

    return render_template("dashboard.html", posts=posts)

@app.route("/submit", methods=["POST"])
def submit_post():
    if "user" not in session:
        return redirect("/")

    
    content = request.form["content"]

    user_id = session["user"]
    id_token = session["id_token"]

    post_data = {
        
        "content": content
    }

    db.child("posts").child(user_id).push(post_data, id_token)

    return redirect("/dashboard")




if __name__ == "__main__":
    app.run(debug=False)

