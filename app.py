from flask import Flask, render_template, abort, request, session, redirect, url_for
from dotenv import load_dotenv
from database import Database 
import os

app = Flask(__name__)
db = None

def init_app():
    '''Runs once at the start to initialize the app with any necessary configurations.'''
    db = Database()

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

@app.route("/database_test")
def database_test():
    """Test route to check database connection and fetch card data."""
    global db
    if db is None:
        db = Database()
    
    # Fetch all card data for testing purposes
    card_data = db.get_cards()
    if not card_data:
        return "No card data available.", 404
    
    return render_template("database_test.html", cards=card_data)
    
    

if __name__ == "__main__":
    app.run(debug=True)