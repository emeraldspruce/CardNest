from flask import Flask, render_template, abort, request, session, redirect, url_for
from dotenv import load_dotenv
from database import Database 
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)
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
    global db
    if db is None:
        db = Database()

    id = session.get('user_id')
    if id is not None:
        db.add_user_card(user_id=id, card_id=db.get_card_id_by_name("Blue Business Cash"))
        db.add_user_card(user_id=id, card_id=db.get_card_id_by_name("Blue Business Plus"))
    return render_template("second_page.html")

@app.route("/third_page")
def third_page():
    return render_template("third_page.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    global db
    if db is None:
        db = Database()

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        user = db.get_user(username=username)
        if user is None:
            db.add_user(username=username, email=email, password=password)
            user = db.get_user(username=username)
        elif user['password'] != password:
            return redirect(url_for('login'))

        session['username'] = username
        session['user_id'] = user['id']  # optional
        return redirect(url_for('first_page'))

    return render_template("login.html")

@app.route("/database_test", methods=['GET', 'POST'])
def database_test():
    """Test route to check database connection and fetch card data."""
    global db
    if db is None:
        db = Database()
    
    # Fetch all card data for testing purposes
    view = request.form.get("view")
    user_id = session.get('user_id')
    cards = []
    users = []
    raw = []

    if view == "users":
        users = db.get_all_users()
    elif view == "user_cards" and user_id:
        raw = db.get_user_cards(int(user_id))
        # raw = [(card_id,), (card_id,), ...]
        cards = [card for card in raw]
    elif view == "all_cards":
        cards = db.get_cards()
    
    return render_template("database_test.html", cards=cards, users=users, raw=raw, view=view)
    
    

if __name__ == "__main__":
    app.run(debug=True)