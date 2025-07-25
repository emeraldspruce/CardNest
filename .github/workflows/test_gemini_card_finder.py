import unittest
from unittest import mock
import json
import os
import requests
import sys

# --- Path Modification ---
# This block allows the test script to find the 'geminiCardOutput.py' module
# located in the project's root directory (two levels up from .github/workflows).
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

# Now, we can import the module from the root directory
import geminiCardOutput

# --- Sample Data for Testing ---

# A sample list of cards, similar to what credit-cards.json would contain
SAMPLE_CARDS = [
    {
        "card_name": "Traveler's Dream Card",
        "issuer": "Global Bank",
        "annual_fee": 95,
        "rewards_type": ["travel", "dining"],
        "welcome_bonus": "50,000 points after spending $3,000 in 3 months.",
        "features": ["No foreign transaction fees", "Trip cancellation insurance"]
    },
    {
        "card_name": "Cash Back King",
        "issuer": "National Credit",
        "annual_fee": 0,
        "rewards_type": ["cash_back"],
        "welcome_bonus": "$200 cash back after spending $500 in 3 months.",
        "features": ["5% on rotating categories", "1% on all other purchases"]
    }
]

# A sample API response that the mock will return
MOCK_API_SUCCESS_RESPONSE = {
    "candidates": [
        {
            "content": {
                "parts": [
                    {"text": json.dumps(SAMPLE_CARDS[0])} # Recommends the travel card
                ]
            }
        }
    ]
}

# A sample API response that includes markdown formatting
MOCK_API_MARKDOWN_RESPONSE = {
    "candidates": [
        {
            "content": {
                "parts": [
                    {"text": f"```json\n{json.dumps(SAMPLE_CARDS[1])}\n```"} # Recommends the cash back card
                ]
            }
        }
    ]
}


class TestCreditCardFinder(unittest.TestCase):

    # --- Test for load_credit_cards ---

    @mock.patch('builtins.open', new_callable=mock.mock_open, read_data=json.dumps(SAMPLE_CARDS))
    def test_load_credit_cards_success(self, mock_file):
        """Tests successful loading and parsing of a valid JSON file."""
        cards = geminiCardOutput.load_credit_cards("dummy/path/cards.json")
        self.assertEqual(cards, SAMPLE_CARDS)
        mock_file.assert_called_once_with("dummy/path/cards.json", 'r')

    @mock.patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_credit_cards_file_not_found(self, mock_open):
        """Tests that the function returns None when the file is not found."""
        cards = geminiCardOutput.load_credit_cards("nonexistent/file.json")
        self.assertIsNone(cards)

    @mock.patch('builtins.open', new_callable=mock.mock_open, read_data="this is not json")
    def test_load_credit_cards_invalid_json(self, mock_file):
        """Tests that the function returns None for a file with invalid JSON."""
        cards = geminiCardOutput.load_credit_cards("invalid/format.json")
        self.assertIsNone(cards)
        
    # --- Test for find_best_card ---
    
    # FIX: Add mock for the environment variable to ensure the API key check passes
    @mock.patch.dict(os.environ, {"GEMINI_API_KEY": "DUMMY_KEY_FOR_TESTING"})
    @mock.patch('geminiCardOutput.requests.post')
    def test_find_best_card_success(self, mock_post):
        """Tests the happy path where the API returns a valid recommendation."""
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None 
        mock_response.json.return_value = MOCK_API_SUCCESS_RESPONSE
        mock_post.return_value = mock_response
        recommended_card = geminiCardOutput.find_best_card(SAMPLE_CARDS, "I want a travel card")
        self.assertEqual(recommended_card, SAMPLE_CARDS[0])

    # FIX: Add mock for the environment variable
    @mock.patch.dict(os.environ, {"GEMINI_API_KEY": "DUMMY_KEY_FOR_TESTING"})
    @mock.patch('geminiCardOutput.requests.post')
    def test_find_best_card_cleans_markdown(self, mock_post):
        """Tests that the function correctly removes markdown from the API response."""
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = MOCK_API_MARKDOWN_RESPONSE
        mock_post.return_value = mock_response
        recommended_card = geminiCardOutput.find_best_card(SAMPLE_CARDS, "I want cash back")
        self.assertEqual(recommended_card, SAMPLE_CARDS[1])

    # FIX: Add mock for the environment variable
    @mock.patch.dict(os.environ, {"GEMINI_API_KEY": "DUMMY_KEY_FOR_TESTING"})
    @mock.patch('geminiCardOutput.requests.post', side_effect=requests.exceptions.RequestException("API Error"))
    def test_find_best_card_api_error(self, mock_post):
        """Tests how the function handles a network or API error."""
        recommended_card = geminiCardOutput.find_best_card(SAMPLE_CARDS, "any query")
        self.assertIsNone(recommended_card)
        
    # This test correctly mocks an EMPTY key
    @mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""})
    def test_find_best_card_no_api_key(self):
        """Tests that the function returns None if the API key is not set."""
        recommended_card = geminiCardOutput.find_best_card(SAMPLE_CARDS, "any query")
        self.assertIsNone(recommended_card)

    # FIX: Add mock for the environment variable
    @mock.patch.dict(os.environ, {"GEMINI_API_KEY": "DUMMY_KEY_FOR_TESTING"})
    @mock.patch('geminiCardOutput.requests.post')
    def test_find_best_card_bad_json_response(self, mock_post):
        """Tests the case where the API returns non-JSON text."""
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None
        bad_response_data = {"candidates": [{"content": {"parts": [{"text": "Sorry, I can't help."}]}}]}
        mock_response.json.return_value = bad_response_data
        recommended_card = geminiCardOutput.find_best_card(SAMPLE_CARDS, "any query")
        self.assertIsNone(recommended_card)
        
    # --- Test for format_card ---
    
    def test_format_card_displays_correctly(self):
        """Tests the standard formatting of a card's details."""
        card = SAMPLE_CARDS[0] # The travel card
        formatted_string = geminiCardOutput.format_card(card)
        
        # --- Robust Check ---
        # This verifies the correct data is present, ignoring the exact spacing.
        self.assertIn("Name:", formatted_string)
        self.assertIn("Traveler's Dream Card", formatted_string)
        
        self.assertIn("Issuer:", formatted_string)
        self.assertIn("Global Bank", formatted_string)
        
        self.assertIn("Annual Fee:", formatted_string)
        self.assertIn("$95", formatted_string)

        self.assertIn("Rewards Type: travel, dining", formatted_string)
        self.assertIn("Welcome Bonus: 50,000 points after spending $3,000 in 3 months.", formatted_string)
        self.assertIn("- No foreign transaction fees", formatted_string)

    def test_format_card_handles_none(self):
        """Tests that the function handles None input gracefully."""
        formatted_string = geminiCardOutput.format_card(None)
        self.assertEqual(formatted_string, "Could not find a recommendation.")

if __name__ == '__main__':
    unittest.main()