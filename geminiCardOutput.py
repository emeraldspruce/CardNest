import json
import os
import requests
import textwrap
from database import Database

# --- Configuration ---
# IMPORTANT: Set your Gemini API key as an environment variable named 'GEMINI_API_KEY'
# How to set an environment variable:
# - Linux/macOS: export GEMINI_API_KEY='your_api_key_here'
# - Windows: set GEMINI_API_KEY='your_api_key_here'
# You can get an API key from Google AI Studio.
API_KEY = os.getenv("GEMINI_API_KEY")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

def find_best_card(card_list, user_query, fail_num=0, fail_max=5):
    """
    Uses the Gemini API to find the best card based on a user's query.

    Args:
        card_list (list): The list of available credit cards.
        user_query (str): The user's description of their desired card.
        fail_num (int): The current number of failed attempts.
        fail_max (int): The maximum number of fails allowed.

    Returns:
        dict: The dictionary of the recommended card, or None if an error occurs.
    """
    if not API_KEY:
        print("Error: GEMINI_API_KEY environment variable not set.")
        return None

    # We serialize the list of cards into a JSON string to send to the model.
    cards_json_string = json.dumps(card_list, indent=2)

    # This prompt is engineered to get a clean JSON object as a response.
    prompt = textwrap.dedent(f"""
        You are an expert credit card recommendation assistant.
        Your task is to analyze a user's request and find the single best matching credit card from a provided JSON list.

        Here is the list of available credit cards:
        {cards_json_string}

        Here is the user's request:
        "{user_query}"

        Based on the user's request, please identify the single best card from the list.
        Your response MUST be ONLY the JSON object of the recommended card from the list provided.
        Do not add any explanation, introduction, or markdown formatting.
    """)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    headers = {
        'Content-Type': 'application/json'
    }
    
    card_text = "" # Initialize card_text to be available in the final except block
    try:
        print("\nAsking Gemini to find the best card for you...")
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()  # Raises an exception for bad status codes (4xx or 5xx)

        response_data = response.json()
        
        # Extract the text content from the API response
        card_text = response_data['candidates'][0]['content']['parts'][0]['text']
        
        # --- FIX: Clean the response to remove markdown formatting ---
        # The API sometimes returns the JSON wrapped in ```json ... ```
        # This code finds the start and end of the JSON object to extract it.
        if '```' in card_text:
            start = card_text.find('{')
            end = card_text.rfind('}') + 1
            if start != -1 and end != 0:
                 card_text = card_text[start:end]

        # The model should return a clean JSON string, so we parse it.
        recommended_card = json.loads(card_text)
        return recommended_card

    except requests.exceptions.RequestException as e:
        print(f"An API error occurred: {e}")
        fail_num += 1
        print(f"Number of fails: {fail_num}")
        if fail_num < fail_max:
            return find_best_card(card_list, user_query, fail_num)
        return None
    except (KeyError, IndexError):
        print("Error: Could not parse the response from the Gemini API.")
        print("Raw response:", response.text)
        fail_num += 1
        print(f"Number of fails: {fail_num}")
        if fail_num < fail_max:
            return find_best_card(card_list, user_query, fail_num)
        return None
    except json.JSONDecodeError:
        print("Error: Failed to decode the JSON response from the API.")
        print("Received text:", card_text)
        fail_num += 1
        print(f"Number of fails: {fail_num}")
        if fail_num < fail_max:
            return find_best_card(card_list, user_query, fail_num)
        return None


def format_card(card):
    """
    Nicely prints the details of a credit card.
    This function is updated to handle multiple JSON formats.

    Args:
        card (dict): The credit card dictionary to display.
    """
    if not card:
        return "Could not find a recommendation."

    lines = []
    lines.append("--- Recommended Card ---")
    # Handle multiple possible keys for the same data
    name = card.get('card_name', card.get('name', 'N/A'))
    issuer = card.get('issuer', 'N/A')
    annual_fee = card.get('annual_fee', card.get('annualFee', 'N/A'))

    lines.append(f"Name:         {name}")
    lines.append(f"Issuer:       {issuer}")
    lines.append(f"Annual Fee:   ${annual_fee}")

    # --- Improved Formatting Logic ---

    # Attempt to parse rewards from the original format
    rewards_type = card.get('rewards_type')
    if rewards_type:
        lines.append(f"Rewards Type: {', '.join(rewards_type)}")
    # Otherwise, parse rewards from the new format
    elif 'universalCashbackPercent' in card:
        cashback = card.get('universalCashbackPercent', 0)
        if cashback > 0:
            lines.append(f"Rewards:      {cashback}% universal cash back.")
    
    # Attempt to parse welcome bonus from the original format
    welcome_bonus = card.get('welcome_bonus')
    if welcome_bonus:
         lines.append(f"Welcome Bonus: {welcome_bonus}")
    # Otherwise, parse the 'offers' array from the new format
    elif 'offers' in card and card['offers']:
        offer = card['offers'][0] # Get the first offer
        spend = offer.get('spend')
        days = offer.get('days')
        amount = offer.get('amount', [{}])[0].get('amount', 0)
        if amount and spend and days:
            lines.append(f"Welcome Bonus: Earn ${amount} after spending ${spend} in the first {days} days.")

    # Attempt to get features from the original format
    features = card.get('features', [])
    # Also add features from the new format
    if 'credits' in card and card['credits']:
        for credit in card['credits']:
            desc = credit.get('description', 'N/A')
            val = credit.get('value', 0)
            features.append(f"${val} {desc} credit")
    
    if card.get('url'):
        features.append(f"More info: {card.get('url')}")

    if features:
        lines.append("Features:")
        for feature in features:
            lines.append(f"  - {feature}")
    
    lines.append("------------------------")
    return "\n".join(lines)

def simplify(cards):
    """
    Removes unused data from the cards JSON.

    Args:
        cards (list): The list of available credit cards.

    Returns:
        list: The list of availible credit cards simplified
    """
    return_cards = []
    for card in cards:
        simple_card = {}
        simple_card["name"] = card["name"]
        simple_card["issuer"] = card["issuer"]
        simple_card["currency"] = card["currency"]
        simple_card["annualFee"] = card["annualFee"]
        simple_card["universalCashbackPercent"] = card["universalCashbackPercent"]
        simple_card["url"] = card["url"]
        simple_card["credits"] = card["credits"]
        simple_card["offers"] = card["offers"]
        return_cards.append(simple_card)
    return return_cards

def get_recommended_card(user_query, db):
    """
    Main function to run the credit card parser program.
    """
    cards_verbose = db.get_cards()
    cards = simplify(cards_verbose)
    if not cards:
        return "Could not load credit card data."
    card = find_best_card(cards, user_query)
    return format_card(card)

# Only run main if executed directly
if __name__ == "__main__":
    print("--- Credit Card Finder powered by Gemini ---")
    db = Database()
    cards = db.get_cards()
    if not cards:
        exit()
    user_query = input("> ")
    card = find_best_card(cards, user_query)
    print(format_card(card))
