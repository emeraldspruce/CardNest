from flask import Flask, render_template, abort, request, session, redirect, url_for
from dotenv import load_dotenv
import os
import subprocess
import sys
from geminiCardOutput import get_recommended_card

app = Flask(__name__)

def init_app():
    '''Runs once at the start to initialize the app with any necessary configurations.'''

init_app()

@app.route("/")
def first_page():
    return render_template("first_page.html")

@app.route("/second_page")
def second_page():
    return render_template("second_page.html")

@app.route("/gemini_rec", methods=["GET", "POST"])
def gemini_rec():
    if request.method == "POST":
        description = request.form.get("description")
        if description:
            output = get_recommended_card(description)
            return render_template("gemini_rec.html", message=output)
    return render_template("gemini_rec.html")

if __name__ == "__main__":
    app.run(debug=True)