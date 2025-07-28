import sqlite3
import requests
import json
import os

class Database:
    def __init__(self, db_name='credit_cards.db'):
        self.db_name = db_name

        # Fetch credit card data from GitHub or local cache.
        self.card_data = []
        try:
            credit_cards_url = "https://raw.githubusercontent.com/andenacitelli/credit-card-bonuses-api/main/exports/data.json"
            response = requests.get(credit_cards_url)
            response.raise_for_status()
            self.card_data = response.json()
            with open("cards_cache.json", "w") as f:
                json.dump(self.card_data, f)
            print(f"Fetched {len(self.card_data)} cards from GitHub.")
        except Exception as e:
            print(f"Fetch failed: {e}")
            if os.path.exists("cards_cache.json"):
                with open("cards_cache.json") as f:
                    self.card_data = json.load(f)
                print(f"Loaded {len(self.card_data)} cards from local cache.")
            else:
                print("No card data available.")

        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn


    def init_db(self):
        """Initialize the database and create the tables if they doesn't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    balance REAL DEFAULT 0
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_cards (
                    user_id INTEGER NOT NULL,
                    card_id TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE (user_id, card_id)
                )
            ''')
            conn.commit()

    # All of the following methods are for accessing the credit cards.
    def get_card_id_by_name(self, card_name):
        """Retrieve the ID of a credit card by its name."""
        for card in self.card_data:
            if card['name'].lower() == card_name.lower():
                return card['cardId']
        return None

    def get_card(self, card_name):
        """Retrieve a credit card by its name."""
        for card in self.card_data:
            if card['name'].lower() == card_name.lower():
                return card
        return None

    def get_card_by_id(self, card_id):
        """Retrieve a credit card by its ID."""
        for card in self.card_data:
            if card['cardId'] == card_id:
                return card
        return None

    def get_cards(self):
        """Retrieve all credit cards."""
        return self.card_data

    # All of the following methods are for managing the user table.
    def add_user(self, username, email, password):
        """Add a new user to the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, email, password)
                VALUES (?, ?, ?)
            ''', (username, email, password))
            conn.commit()

    def get_user(self, username=None, email=None):
        """Retrieve a user by username or email."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if username:
                cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            elif email:
                cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            else:
                return None
            return cursor.fetchone()

    def get_all_users(self):
        """Retrieve all users from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users')
            return cursor.fetchall()

    def update_user(self, user_id, username=None, email=None, password=None):
        """Update user information."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if username:
                cursor.execute('UPDATE users SET username = ? WHERE id = ?', (username, user_id))
            if email:
                cursor.execute('UPDATE users SET email = ? WHERE id = ?', (email, user_id))
            if password:
                cursor.execute('UPDATE users SET password = ? WHERE id = ?', (password, user_id))
            conn.commit()

    # All of the following methods are for managing the users' credit cards.
    def add_user_card(self, user_id, card_id):
        """Add a credit card to a user's account."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO user_cards (user_id, card_id)
                VALUES (?, ?)
            ''', (user_id, card_id))
            conn.commit()

    def get_user_cards(self, user_id):
        """Retrieve all credit cards associated with a user."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT card_id FROM user_cards WHERE user_id = ?
            ''', (user_id,))
            ids = [row[0] for row in cursor.fetchall()]  # extract card_id strings
            user_cards = []
            for card_id in ids:
                match = next((card for card in self.card_data if card.get('cardId') == card_id), None)
                if match:
                    user_cards.append(match)

            return user_cards

    def remove_user_card(self, user_id, card_id):
        """Remove a credit card from a user's account."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM user_cards WHERE user_id = ? AND card_id = ?
            ''', (user_id, card_id))
            conn.commit()

    # The following methods are for clearing the database.
    def clear_users(self):
        """Clear all users from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users')
            conn.commit()

    def clear_user_cards(self):
        """Clear all user cards from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_cards')
            conn.commit()

    def clear_database(self):
        """Clear the entire database."""
        self.clear_users()
        self.clear_user_cards()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DROP TABLE IF EXISTS users')
            cursor.execute('DROP TABLE IF EXISTS user_cards')
            conn.commit()
        self.init_db()

    # Debugging methods.
    def print_users(self):
        """Print all users in the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users')
            users = cursor.fetchall()
            for user in users:
                print(user)

    def print_user_cards(self, user_id):
        """Print all credit cards associated with a user."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT card_id FROM user_cards WHERE user_id = ?
            ''', (user_id,))
            cards = cursor.fetchall()
            for card in cards:
                print(card)
    
    def print_all_cards(self):
        """Print all credit cards in the database."""
        for card in self.card_data:
            print(card)