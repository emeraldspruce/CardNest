from collections import defaultdict

from networkx import reverse
from flask import Flask, render_template, abort, request, session, redirect, url_for, flash, jsonify
from dotenv import load_dotenv
from database import Database 
from werkzeug.utils import secure_filename 
import uuid
import firebase_admin
from firebase_admin import credentials, auth
import os
import json
from geminiCardOutput import get_recommended_card
import pandas as pd
from datetime import datetime
from collections import defaultdict
from functools import wraps
from gemini_analysis import get_spending_recommendations

app = Flask(__name__)
load_dotenv()
app.secret_key = os.getenv("SECRET_KEY")
firebase_service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
if not firebase_service_account_json:
    raise Exception("FIREBASE_SERVICE_ACCOUNT_JSON not found in env!")

firebase_creds_dict = json.loads(firebase_service_account_json)
cred = credentials.Certificate(firebase_creds_dict)
firebase_app = firebase_admin.initialize_app(cred)

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
    if request.method == "POST":
        data = request.get_json()
        if not data or not data.get("idToken"):
            return jsonify({"status": "error", "message": "idToken is missing."}), 400
        
        try:
            id_token = data.get("idToken")
            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token["uid"]
            email = decoded_token.get("email")

            # Store user info in the session
            session.clear()
            session["user"] = {"id": uid, "email": email}
            session.permanent = True # Make the session last longer

            # On success, return a JSON response
            return jsonify({
                "status": "success", 
                "message": "Login successful!",
                "redirect": url_for("dashboard")
            })
        except Exception as e:
            print(f"Login failed: {e}")
            return jsonify({"status": "error", "message": str(e)}), 401
        
    # For GET requests, show the login page
    return render_template("login.html")

# Formatting csv date 
@app.template_filter("format_date")
def format_date(value):
    if isinstance(value, str):
        #We assume date is in 'YYYY-MM-DD' format
        try:
            date = datetime.strptime(value, '%Y-%m-%d')
            return date.strftime('%B %d, %Y')  # Format as 'Jul, 28, 2025'
        except Exception:
            return value
    return value

# Format csv dollar values
@app.template_filter("format_currency")
def format_currency(value):
    try: 
        if isinstance(value, (int, float)):
            return f"${(value):,.2f}" #Already int or float so just format
        elif isinstance(value, str):
            return f"${(float(value)):.2f}"  # Convert string to float and format
    except Exception:
        return value
    return value

@app.route("/profile")
def profile():
    return render_template("profile.html", require_auth=True)

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    global db
    if not db:
        db = Database()
    data = session.get("data", [])
    categorized_totals = defaultdict(float)
    net_balance = 0.0
    
    sort_column = request.args.get("sort_column", "Date")
    sort_order = request.args.get("sort_order", "asc")
    reversed_sort = sort_order == "desc"
    
    if sort_column == 'Amount' and data:
        data.sort(key=lambda x: float(x.get("Amount", 0)), reverse=reversed_sort)
    elif sort_column == 'Date' and data:
        data.sort(key=lambda x: datetime.strptime(x.get("Date", "1970-01-01"), '%Y-%m-%d'), reverse=reversed_sort)

    for row in data:
        category = row.get("Category", "Uncategorized")
        amount = float(row.get("Amount", 0))
        categorized_totals[category] += amount
        net_balance += amount

    categories = list(categorized_totals.keys())
    amounts = [abs(categorized_totals[cat]) for cat in categories]
    income_total = sum(amount for cat, amount in categorized_totals.items() if amount > 0)
    expense_total = sum(abs(amount) for cat, amount in categorized_totals.items() if amount < 0)
    net_balance = round(net_balance, 2)
    user_cards = db.get_user_cards(session["user"]["id"])

    if request.method == "POST":
        card_id = request.form.get('cardId')
        db.remove_user_card(session["user"]["id"], card_id)

    # --- NEW LOGIC: Handle the Gemini analysis request ---
    analysis_result = None
    if request.args.get('action') == 'analyze':
        if not data or not user_cards:
            flash("Please upload a statement and add your cards before analyzing.", "warning")
        else:
            # Call the new function with the user's data
            analysis_result = get_spending_recommendations(user_cards, data)
    
    return render_template(
        "dashboard.html", 
        data=data, 
        categories=categories, 
        amounts=amounts, 
        sort_column=sort_column, 
        sort_order=sort_order, 
        net_balance=net_balance, 
        total_income=income_total, 
        total_expenses=expense_total, 
        cards=user_cards,
        analysis=analysis_result  # Pass the analysis result to the template
    )

@app.route("/browse_cards", methods=["GET", "POST"])
def browse_cards():
    if request.method == "POST":
        # This part handles ADDING a card
        card_id = request.form.get('cardId')
        user_id = session["user"]["id"]
        db.add_user_card(user_id, card_id)
        
        # Redirect to prevent form resubmission on page refresh
        # We include the search query to keep the filter active
        search_query = request.args.get('q', '')
        return redirect(url_for('browse_cards', q=search_query))

    # This part handles DISPLAYING the cards (GET request)
    search_query = request.args.get('q', '').lower()
    all_cards = db.get_cards()
    
    if search_query:
        # Filter the cards if a search query exists
        filtered_cards = [
            card for card in all_cards
            if search_query in card['name'].lower() or search_query in card['issuer'].lower()
        ]
    else:
        filtered_cards = all_cards

    return render_template(
        "browse_cards.html",
        cards=filtered_cards,
        search_query=search_query
    )

@app.route("/upload_page", methods=["GET", "POST"])
def upload_page():
    global db
    if db is None:
        db = Database()

    id = session.get('user_id')
    if id is not None:
        db.add_user_card(user_id=id, card_id=db.get_card_id_by_name("Blue Business Cash"))
        db.add_user_card(user_id=id, card_id=db.get_card_id_by_name("Blue Business Plus"))
    session.pop("data", None)  # Clear previous data if any
    return render_template("upload_page.html", require_auth=True)

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

        #parse the CSV file and store data in session
        try:
            df = pd.read_csv(filepath)
            session['data'] = df.to_dict(orient='records')  # Store data as a list of dictionaries
        except Exception as e:
            flash(f"Error processing file: {e}")
        flash("File uploaded successfully!")
        return redirect(url_for('dashboard'))
    else:
        flash("Invalid file type. Please upload a CSV file.")
        return redirect(url_for('upload_page'))

@app.route("/third_page")
def third_page():
    return render_template("third_page.html", require_auth=True)

@app.route("/gemini_rec", methods=["GET", "POST"])
def gemini_rec():
    global db
    if db is None:
        db = Database()

    if request.method == "POST":
        description = request.form.get("description")
        if description:
            output = get_recommended_card(description, db)
            return render_template("gemini_rec.html", message=output, require_auth=True)
    return render_template("gemini_rec.html", require_auth=True)

@app.route("/tips")
def tips():
    return render_template("tips.html", require_auth=True)

@app.template_filter("normalize_issuer")
def normalize_issuer_name(name):
    """
    Converts an issuer string like 'AMERICAN_EXPRESS' to 'American Express'.
    """
    if not isinstance(name, str):
        return name
    # Capitalize each word and replace underscores with spaces
    return ' '.join(word.capitalize() for word in name.split('_'))

if __name__ == "__main__":
    app.run(debug=True)