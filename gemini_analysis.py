import json
import os
import requests
import textwrap

API_KEY = os.getenv("GEMINI_API_KEY")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

def get_spending_recommendations(user_cards, purchase_history):
    """
    Uses the Gemini API to analyze spending patterns and recommend optimal card usage.
    """
    if not API_KEY:
        return "Error: GEMINI_API_KEY environment variable not set."

    # Convert the user's cards and purchase history to JSON strings
    cards_json = json.dumps(user_cards, indent=2)
    history_json = json.dumps(purchase_history, indent=2)

    # This prompt is engineered to get a clear, markdown-formatted analysis.
    prompt = textwrap.dedent(f"""
        You are a financial analyst specializing in credit card rewards.
        Your task is to analyze a user's spending history and their current credit cards to provide actionable recommendations for maximizing rewards.

        Here is the list of the user's credit cards and their benefits:
        {cards_json}

        Here is the user's recent purchase history:
        {history_json}

        Based on both lists, please provide a brief analysis and a set of recommendations. Structure your response in markdown format as follows:

        **Spending Analysis:**
        A one or two-sentence summary of the user's main spending categories (e.g., "Your top spending categories are Grocery and Food & Dining.").

        **Card Recommendations:**
        Create a bulleted list. For each major spending category from the user's history, recommend which of their cards would have been the best to use and briefly explain why.
        For example:
        - **Grocery**: Use your 'Amex Gold' card to earn 4x points on all grocery purchases.
        - **Subscriptions**: Your 'Chase Freedom Unlimited' would be best here for its flat 1.5% cash back.

        **Missed Opportunities:**
        If you spot any clear missed opportunities, mention one or two. For example: "You spent a lot on travel using a low-reward card; your 'Chase Sapphire' would have earned significantly more."

        Keep the entire response concise and easy to read.
    """)

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        response_data = response.json()
        
        # Extract the markdown text content from the API response
        analysis_text = response_data['candidates'][0]['content']['parts'][0]['text']
        return analysis_text

    except requests.exceptions.RequestException as e:
        return f"An API error occurred: {e}"
    except (KeyError, IndexError):
        return "Error: Could not parse the response from the Gemini API."