from flask import Flask, render_template, abort, request, session, redirect, url_for
from dotenv import load_dotenv
import os

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

@app.route("/third_page")
def third_page():
    return render_template("third_page.html")

if __name__ == "__main__":
    app.run(debug=True)