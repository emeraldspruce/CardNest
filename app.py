from collections import defaultdict

from networkx import reverse
from flask import Flask, render_template, abort, request, session, redirect, url_for, flash
from dotenv import load_dotenv
from database import Database 
from werkzeug.utils import secure_filename 
import uuid
import os
import subprocess
import sys
from geminiCardOutput import get_recommended_card
import pandas as pd
from datetime import datetime
from collections import defaultdict


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

@app.route("/dashboard")
def dashboard():
    data = session.get("data", [])
    categorized_totals = defaultdict(float)
    net_balance = 0.0
    
    #Get sorting params 
    sort_column = request.args.get("sort_column", "Date") #Default to sorting by Date
    sort_order = request.args.get("sort_order", "asc") #Default to ascending order
    reversed = sort_order == "desc"
    if sort_column == 'Amount':
        data.sort(key=lambda x: float(x.get("Amount", 0)), reverse=(reversed))
    elif sort_column == 'Date':
        data.sort(
        key=lambda x: datetime.strptime(x.get("Date", "1970-01-01"), '%Y-%m-%d'),
        reverse=(reversed)
    )
    for row in data:
        category = row.get("Category", "Uncategorized")
        amount = float(row.get("Amount", 0))
        categorized_totals[category] += amount
        net_balance += amount
    categories = list(categorized_totals.keys())
    amounts = [abs(categorized_totals[cat]) for cat in categories]
    # Calculate income and expense totals
    income_total = sum(amount for cat, amount in categorized_totals.items() if amount > 0)
    expense_total = sum(abs(amount) for cat, amount in categorized_totals.items() if amount < 0)
    
    #Trim net balance to 2 decimal places
    net_balance = round(net_balance, 2)
    return render_template("dashboard.html", require_auth=True, data=data, categories=categories, amounts=amounts, sort_column=sort_column, sort_order=sort_order, net_balance=net_balance, total_income=income_total, total_expenses=expense_total)

@app.route("/second_page", methods=["GET", "POST"])
def second_page():
    global db
    if db is None:
        db = Database()

    id = session.get('user_id')
    if id is not None:
        db.add_user_card(user_id=id, card_id=db.get_card_id_by_name("Blue Business Cash"))
        db.add_user_card(user_id=id, card_id=db.get_card_id_by_name("Blue Business Plus"))
    session.pop("data", None)  # Clear previous data if any
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