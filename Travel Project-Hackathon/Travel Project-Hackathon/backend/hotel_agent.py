from flask import Flask, request, jsonify
import json
import random

app = Flask(__name__)

# --- Helper function to generate mock hotel data ---
def generate_mock_hotels(num_hotels_per_city=2000):
    cities = [
        "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
        "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose",
        "Austin", "Jacksonville", "Fort Worth", "Columbus", "Charlotte",
        "San Francisco", "Indianapolis", "Seattle", "Denver", "Washington",
        "Boston", "El Paso", "Nashville", "Detroit", "Oklahoma City",
        "Portland", "Las Vegas", "Memphis", "Louisville", "Baltimore",
        "Milwaukee", "Albuquerque", "Tucson", "Fresno", "Sacramento",
        "Kansas City", "Mesa", "Atlanta", "Omaha", "Colorado Springs",
        "Raleigh", "Miami", "Virginia Beach", "Long Beach", "Oakland",
        "Minneapolis", "Tulsa", "Wichita", "New Orleans", "Arlington"
    ]

    hotel_prefixes = ["Grand", "Comfort", "Elite", "Royal", "City", "Star", "Prime", "Luxury", "Inn", "Suite"]
    hotel_suffixes = ["Hotel", "Resort", "Inn", "Suites", "Place", "Lodge", "Manor", "House", "Gardens"]
    street_types = ["St", "Ave", "Blvd", "Rd", "Ln", "Dr"]

    all_hotels_data = {}

    for city in cities:
        city_hotels = []
        for i in range(num_hotels_per_city):
            name = f"{random.choice(hotel_prefixes)} {random.choice(hotel_suffixes)} {random.randint(1, 100)}"
            rating = round(random.uniform(3.0, 5.0), 1)
            address = f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Elm', 'Maple'])} {random.choice(street_types)}, {city}"
            
            # Generate price range
            base_price = random.randint(50, 500)
            price_range_low = base_price - random.randint(0, 40)
            price_range_high = base_price + random.randint(50, 150)
            price_range = f"${price_range_low} - ${price_range_high}"

            city_hotels.append({
                "name": name,
                "rating": rating,
                "address": address,
                "price_range": price_range
            })
        all_hotels_data[city] = city_hotels
    return all_hotels_data

# Load the hotel data
# Generate a large dataset of hotels
hotels_data = generate_mock_hotels(num_hotels_per_city=200) # Adjusted to generate 10,000 hotels (50 cities * 200 hotels/city)
# If you need exactly 10,000, you can calculate num_hotels_per_city = 10000 / len(cities)
# For example, with 50 cities, 10000 / 50 = 200 hotels per city.

@app.route('/hotels', methods=['POST'])
def get_hotels():
    try:
        data = request.get_json()
        city = data.get("cityname")
        num_of_rooms = data.get("num_of_rooms")
        checkin = data.get("checkin_date")
        checkout = data.get("checkout_date")
 
        if city not in hotels_data:
            return jsonify({"hotels": [], "message": "No hotels available for the selected city"}), 200
 
        results = []
        # For large datasets, consider pagination or limiting results if needed in a real application
        for hotel in hotels_data[city]:
            hotel_copy = hotel.copy()
            hotel_copy["checkin_date"] = checkin
            hotel_copy["checkout_date"] = checkout
            hotel_copy["num_of_rooms"] = num_of_rooms
            results.append(hotel_copy)
 
        return jsonify({"hotels": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
 
def handle_prompt(prompt: str):
    """
    Simulates handling the hotel booking prompt.
    """
    print("Received prompt:")
    print(prompt)
    # Add more logic here, like interacting with a booking API or automating UI

if __name__ == '__main__':
    app.run(debug=False,port=5000)
