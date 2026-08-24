import requests
import functools
from flask import Flask, request, jsonify

app = Flask(__name__)

# Replace with a reputable exchange rate API key
EXCHANGE_RATE_API_KEY = "YOUR_EXCHANGE_RATE_API_KEY"  # Get your own key from a provider like exchangerate-api.com
EXCHANGE_RATE_API_URL = "https://v6.exchangerate-api.com/v6/{}/latest/".format(EXCHANGE_RATE_API_KEY)

# Cache to store exchange rates (currency pair -> rate)
exchange_rate_cache = {}
CACHE_TTL = 600  # Cache time-to-live in seconds (10 minutes)

def get_exchange_rate(from_currency, to_currency):
    """
    Fetches the exchange rate from the API, using the cache if available.
    """
    cache_key = f"{from_currency}_{to_currency}"

    if cache_key in exchange_rate_cache and (exchange_rate_cache[cache_key]["timestamp"] + CACHE_TTL) > time.time():
        return exchange_rate_cache[cache_key]["rate"]

    try:
        response = requests.get(EXCHANGE_RATE_API_URL + from_currency)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if "conversion_rates" and to_currency in data["conversion_rates"]:
            rate = data["conversion_rates"][to_currency]
            exchange_rate_cache[cache_key] = {"rate": rate, "timestamp": time.time()}
            return rate
        else:
            return None  # Currency pair not found
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None  # API request failed

@app.route("/currency/convert", methods=["POST"])
def convert_currency():
    """
    API endpoint for currency conversion.
    """
    try:
        data = request.get_json()
        amount = float(data["amount"])
        to_currency = data["to_currency"].upper()
        from_currency = data["from_currency"].upper()

        if not (len(to_currency) == 3 and len(from_currency) == 3):
            return jsonify({"error": "Invalid currency codes"}), 400

        exchange_rate = get_exchange_rate(from_currency, to_currency)

        if exchange_rate is None:
            return jsonify({"error": "Currency pair not supported"}), 400

        converted_amount = amount * exchange_rate

        return jsonify({"converted_amount": converted_amount}), 200

    except (TypeError, ValueError, KeyError) as e:
        print(f"Input error: {e}")
        return jsonify({"error": "Invalid input"}), 400
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500

import time

if __name__ == "__main__":
    app.run(debug=True)