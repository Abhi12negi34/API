from flask import Flask, request, jsonify
import uuid
import sqlite3

app = Flask(__name__)

DATABASE = 'travel_reviews.db'

def create_table():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            review_id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            user_id TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT
        )
    ''')
    conn.commit()
    conn.close()

create_table()

@app.route('/reviews', methods=['POST'])
def submit_review():
    data = request.get_json()

    # Input validation
    if not all(key in data for key in ['rating', 'comment', 'entity_id', 'entity_type']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        rating = int(data['rating'])
        if not 1 <= rating <= 5:
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid rating format'}), 400

    if not isinstance(data['comment'], str):
        return jsonify({'error': 'Comment must be a string'}), 400
    
    if not isinstance(data['entity_id'], str):
        return jsonify({'error': 'Entity ID must be a string'}), 400
    
    if not isinstance(data['entity_type'], str):
        return jsonify({'error': 'Entity type must be a string'}), 400

    # Assuming user_id is obtained from authentication (MOD-016 dependency)
    user_id = "default_user"  # Replace with actual user ID from authentication

    # Store review in the database
    review_id = str(uuid.uuid4())
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO reviews (review_id, entity_id, entity_type, user_id, rating, comment)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (review_id, data['entity_id'], data['entity_type'], user_id, rating, data['comment']))
    conn.commit()
    conn.close()

    return jsonify({'review_id': review_id}), 201

if __name__ == '__main__':
    app.run(debug=True)