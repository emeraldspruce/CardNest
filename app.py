from flask import Flask, render_template, abort, request, session, redirect, url_for, flash
from dotenv import load_dotenv
import os

app = Flask(__name__)

def init_app():
    '''Runs once at the start to initialize the app with any necessary configurations.'''

init_app()

@app.route("/")
def first_page():
    return render_template("first_page.html")

@app.route("/second_page", methods=["GET", "POST"])
def second_page():
    return render_template("second_page.html")

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
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        flash("File uploaded successfully!")
        # Optionally, process the CSV file here
        return redirect(url_for('second_page'))
    else:
        flash("Invalid file type. Please upload a CSV file.")
        return redirect(url_for('second_page'))

@app.route("/third_page")
def third_page():
    return render_template("third_page.html")

if __name__ == "__main__":
    app.run(debug=True)