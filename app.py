from flask import Flask, render_template, abort, request, session, redirect, url_for, flash
from dotenv import load_dotenv
from database import Database 
from werkzeug.utils import secure_filename 
import uuid
import firebase_admin
from firebase_admin import credentials, auth
import os
import json
from geminiCardOutput import get_recommended_card


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = None


def init_app():
    '''Runs once at the start to initialize the app with any necessary configurations.'''
    global db
    db = Database()
init_app()

@app.errorhandler(404)
def page_not_found(e):
    '''Handles 404 errors by rendering a custom 404 page.'''
    return render_template("404.html"), 404

@app.route("/")
@app.route("/login", methods=["GET", "POST"])
def login():
    global db
    if db is None:
        db = Database()
    if request.method == "POST":
        data = request.get_json()
        id_token = data.get("idToken")
        try:
            # Verify the ID token
            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token["uid"]
            email = decoded_token.get("email")

            # Optional: store in session
            session["user"] = {
                "id": uid,
                "email": email,
            }
            db.add_user(uid, email)
            print("User added!")
        except Exception as e:
            print(f"Login failed: {e}")
    return render_template("login.html")

@app.route("/profile")
def profile():
    ############################################ TESTING #########################################
    global db
    print("---------- ALL USERS ----------")
    db.print_users()
    print("-------- CURRENT USERS --------")
    user = db.get_user(session["user"]["id"])
    if user is not None:
        print(f"User ID: {user["id"]}")
        print(f"User email: {user["email"]}")
    ############################################ TESTING #########################################
    return render_template("profile.html")

@app.route("/home")
def home():
    return render_template("home.html")

@app.route("/upload_page", methods=["GET", "POST"])
def upload_page():
    global db
    if db is None:
        db = Database()
    return render_template("upload_page.html")

UPLOAD_FOLDER = 'uploads'  
os.makedirs(UPLOAD_FOLDER, exist_ok=True) 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route("/upload_statement", methods=["POST"])
def upload_statement():
    if 'file' not in request.files:
        flash("No file part")
        return redirect(url_for('upload_page'))

    file = request.files['file']
    if file.filename == '':
        flash("No selected file")
        return redirect(url_for('upload_page'))

    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename) 
        unique_filename = f"{uuid.uuid4().hex}_{filename}"  
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        flash("File uploaded successfully!")
        return redirect(url_for('upload_page'))
    else:
        flash("Invalid file type. Please upload a CSV file.")
        return redirect(url_for('upload_page'))

@app.route("/third_page")
def third_page():
    return render_template("third_page.html")

@app.route("/gemini_rec", methods=["GET", "POST"])
def gemini_rec():
    global db
    if db is None:
        db = Database()

    if request.method == "POST":
        description = request.form.get("description")
        if description:
            output = get_recommended_card(description, db)
            return render_template("gemini_rec.html", message=output)
    return render_template("gemini_rec.html")


if __name__ == "__main__":
    app.run(debug=True)