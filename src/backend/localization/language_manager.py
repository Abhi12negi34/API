import json
import logging
import os

from flask import Flask, request, jsonify

app = Flask(__name__)

# Define the directory for translation files
TRANSLATION_DIR = 'translations'
# Define the default language
DEFAULT_LANGUAGE = 'en'
# Supported languages
SUPPORTED_LANGUAGES = ['en', 'es', 'fr', 'de']

# Load translations
translations = {}
for language_code in SUPPORTED_LANGUAGES:
    try:
        with open(os.path.join(TRANSLATION_DIR, f'{language_code}.json'), 'r', encoding='utf-8') as f:
            translations[language_code] = json.load(f)
    except FileNotFoundError:
        logging.warning(f"Translation file not found for language: {language_code}")
        translations[language_code] = {}  # Use an empty dictionary as fallback
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON for language: {language_code}")
        translations[language_code] = {}  # Use an empty dictionary as fallback

# Set the current language (initially to the default)
current_language = DEFAULT_LANGUAGE


@app.route('/language/switch', methods=['POST'])
def switch_language():
    """
    API endpoint to switch the application's language.
    """
    try:
        data = request.get_json()
        language_code = data.get('language_code')

        if not language_code:
            logging.error("Language code is missing in request")
            return jsonify({'error': 'Language code is required'}), 400

        if language_code not in SUPPORTED_LANGUAGES:
            logging.error(f"Invalid language code: {language_code}")
            return jsonify({'error': 'Invalid language code'}), 400

        global current_language
        current_language = language_code

        return jsonify({'message': 'Language switched successfully'}), 200

    except Exception as e:
        logging.exception(f"An error occurred while switching language: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500


def get_translation(phrase):
    """
    Retrieves the translation for a given phrase.
    Falls back to the default language if translation is missing.
    """
    if current_language in translations and phrase in translations[current_language]:
        return translations[current_language][phrase]
    elif phrase in translations[DEFAULT_LANGUAGE]:
        return translations[DEFAULT_LANGUAGE][phrase]
    else:
        # Log missing translation
        logging.warning(f"Translation missing for phrase: {phrase} in language: {current_language}")
        return phrase  # Return the original phrase as fallback


if __name__ == '__main__':
    # Create the translations directory if it doesn't exist
    if not os.path.exists(TRANSLATION_DIR):
        os.makedirs(TRANSLATION_DIR)

    # Example translation files (create these manually)
    if not os.path.exists(os.path.join(TRANSLATION_DIR, 'en.json')):
        with open(os.path.join(TRANSLATION_DIR, 'en.json'), 'w', encoding='utf-8') as f:
            json.dump({'hello': 'Hello', 'world': 'World'}, f, indent=4)
    if not os.path.exists(os.path.join(TRANSLATION_DIR, 'es.json')):
        with open(os.path.join(TRANSLATION_DIR, 'es.json'), 'w', encoding='utf-8') as f:
            json.dump({'hello': 'Hola', 'world': 'Mundo'}, f, indent=4)

    app.run(debug=True)