from flask import Flask, render_template, abort, request, session, redirect, url_for, flash
from dotenv import load_dotenv
from database import Database 
from werkzeug.utils import secure_filename 
import uuid
import os
import subprocess
import sys
from geminiCardOutput import get_recommended_card


app = Flask(__name__)
load_dotenv()
db = None

app.secret_key = os.getenv("SECRET_KEY")

def init_app():
    '''Runs once at the start to initialize the app with any necessary configurations.'''
    db = Database()

init_app()
@app.errorhandler(404)
def page_not_found(e):
    '''Handles 404 errors by rendering a custom 404 page.'''
    return render_template("404.html"), 404

@app.route("/")
@app.route("/login")
def login():
    return render_template("login.html", require_auth=False)

@app.route("/profile")
def profile():
    return render_template("profile.html", require_auth=True)

@app.route("/first_page")
def first_page():
    return render_template("first_page.html", require_auth=True)

@app.route("/second_page", methods=["GET", "POST"])
def second_page():
    global db
    if db is None:
        db = Database()

    id = session.get('user_id')
    if id is not None:
        db.add_user_card(user_id=id, card_id=db.get_card_id_by_name("Blue Business Cash"))
        db.add_user_card(user_id=id, card_id=db.get_card_id_by_name("Blue Business Plus"))
    return render_template("second_page.html", require_auth=True)

UPLOAD_FOLDER = 'uploads'  
os.makedirs(UPLOAD_FOLDER, exist_ok=True) 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route("/upload_statement", methods=["POST"])
def upload_statement():
    if 'file' not in request.files:
        flash("No file part")
        return redirect(url_for('second_page'))

    file = request.files['file']
    if file.filename == '':
        flash("No selected file")
        return redirect(url_for('second_page'))

    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename) 
        unique_filename = f"{uuid.uuid4().hex}_{filename}"  
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        flash("File uploaded successfully!")
        return redirect(url_for('second_page'))
    else:
        flash("Invalid file type. Please upload a CSV file.")
        return redirect(url_for('second_page'))

@app.route("/third_page")
def third_page():
    return render_template("third_page.html", require_auth=True)

@app.route("/gemini_rec", methods=["GET", "POST"])
def gemini_rec():
    if request.method == "POST":
        description = request.form.get("description")
        if description:
            output = get_recommended_card(description)
            return render_template("gemini_rec.html", message=output, require_auth=True)
    return render_template("gemini_rec.html", require_auth=True)


if __name__ == "__main__":
    app.run(debug=True)