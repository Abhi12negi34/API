from flask import Flask, jsonify, request
from flask import current_app
import logging

# Assuming MOD-017 provides a function to fetch reviews
from src.backend.review.review_data import get_reviews_by_entity  # Replace with actual import

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route("/reviews/<string:entity_id>/<string:entity_type>", methods=["GET"])
def view_reviews(entity_id, entity_type):
    """
    Retrieves reviews for a specific entity.

    Args:
        entity_id (str): The ID of the entity (destination, accommodation, or flight).
        entity_type (str): The type of entity ("destination", "accommodation", or "flight").

    Returns:
        jsonify: A JSON response containing the reviews.
                 Returns 200 on success, 404 if the entity is not found.
    """
    try:
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 10, type=int)

        # Fetch reviews from the data source (MOD-017)
        reviews = get_reviews_by_entity(entity_id, entity_type, page, limit)

        if not reviews:
            return jsonify([]), 200  # Handle entities with no reviews

        return jsonify(reviews), 200

    except Exception as e:
        logging.error(f"Error fetching reviews: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(debug=True)