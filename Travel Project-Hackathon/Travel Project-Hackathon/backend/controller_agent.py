from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta
from hotel_agent import handle_prompt
from flight_agent import handle_flight_prompt
from cab_agent import handle_cab_prompt

app = Flask(__name__)

FLIGHT_AGENT_URL = "http://localhost:5001/flights/search"
HOTEL_AGENT_URL = "http://localhost:5000/hotels"
CAB_AGENT_URL = "http://localhost:5002/cabs/book"

IATA_TO_FULL_AIRPORT_NAME = {
    "HYD": "Hyderabad Airport (HYD)",
    "DEL": "Indira Gandhi International",
    "LAX": "Los Angeles International",
    "LAS": "Harry Reid International",
    "BOS": "Logan International",
    "SFO": "San Francisco International",
    "JFK": "John F. Kennedy International",
    "LGA": "LaGuardia",
    "NYC": "New York (NYC)",
    "ABL": "Ambler",
    "ABE": "Lehigh Valley International",
    "ABQ": "Albuquerque International",
    "ACY": "Atlantic City International",
    "ADD": "Bole International",
}

latest_itinerary = {}

@app.route('/travel/plan', methods=['POST'])
def plan_travel():
    try:
        data = request.get_json()
        print(data)
        user_details = data.get("userdetails")
        flight_details = data.get("flightdetails")
        hotel_details = data.get("hoteldetails")
        cab_details = data.get("cabdetails")

        # --- Step 1: Flight Agent ---
        flight_payload = {
            "source": flight_details["source"],
            "destination": flight_details["destination"],
            "until_date": flight_details["until_date"],
            "airline": flight_details.get("airline", "")
        }

        flight_response = requests.post(FLIGHT_AGENT_URL, json=flight_payload).json()
        if flight_response.get("status") != "success" or not flight_response.get("flights"):
            return jsonify({"error": "No valid flights found."}), 400

        selected_flight = flight_response["flights"][0]
        flight_arrival_time = selected_flight["arrival"]["time"]
        destination_airport_iata = selected_flight["arrival"]["airport"]
        destination_airport_for_cab = IATA_TO_FULL_AIRPORT_NAME.get(destination_airport_iata, destination_airport_iata)

        # --- Step 2: Hotel Agent ---
        hotel_payload = {
            "cityname": hotel_details["cityname"],
            "num_of_rooms": hotel_details["num_of_rooms"],
            "checkin_date": hotel_details["checkin_date"],
            "checkout_date": hotel_details["checkout_date"]
        }

        hotel_response = requests.post(HOTEL_AGENT_URL, json=hotel_payload).json()
        if not hotel_response.get("hotels"):
            return jsonify({"error": "No hotels found for the selected city."}), 400

        selected_hotel = hotel_response["hotels"][0]
        hotel_name = selected_hotel.get("hotelname", "Hotel Near Destination")
        hotel_address = selected_hotel.get("address", "Some Street, Some City")
        drop_location = selected_hotel.get("location", {"lat": 34.0522, "lng": -118.2437})

        # --- Step 3: Cab Agent ---
        cab_payload = {
            "scheduled": flight_arrival_time,
            "airport": destination_airport_for_cab,
            "num_passengers": cab_details["num_passengers"],
            "cab_drop_location": f"{hotel_name}, {hotel_address}",
            "ride_type": cab_details.get("ride_type"),
            "user_prefs": cab_details.get("user_prefs")
        }

        cab_response = requests.post(CAB_AGENT_URL, json=cab_payload).json()
        pickup_time_str = cab_response.get("pickup_time")

        if not pickup_time_str:
            pickup_time_str = (datetime.fromisoformat(flight_arrival_time.replace("Z", "+00:00")) + timedelta(minutes=15)).isoformat()

        pickup_time = datetime.fromisoformat(pickup_time_str)
        arrival_time = datetime.fromisoformat(flight_arrival_time.replace("Z", "+00:00"))

        if pickup_time < arrival_time + timedelta(minutes=10):
            cab_payload["scheduled"] = (arrival_time + timedelta(minutes=20)).isoformat()
            cab_response = requests.post(CAB_AGENT_URL, json=cab_payload).json()

        # Final itinerary response
        itinerary = {
            "user": user_details,
            "flight": selected_flight,
            "hotel": selected_hotel,
            "cab": cab_response
        }
        json_=jsonify({

            "user": user_details,

            "flight": selected_flight,

            "hotel": selected_hotel,

            "cab": cab_response

        })
        handle_prompt(generate_hotel_prompt(itinerary))
        handle_flight_prompt(generate_flight_prompt(itinerary, cab_details))
        handle_cab_prompt(generate_cab_prompt(itinerary))

        global latest_itinerary
        latest_itinerary = itinerary
        print(itinerary)
        return jsonify(itinerary), 200

    except Exception as e:
        return jsonify({"error": f"Failed to process travel plan: {str(e)}"}), 500

def generate_hotel_prompt(data):
    hotel = data['hotel']
    user = data['user']

    prompt = (
        f'Go to google.com and open "Booking.com". '
        f'Search for the {hotel["name"]} at {hotel["address"]}, '
        f'the checkin date: {hotel["checkin_date"]} and checkout date: {hotel["checkout_date"]} '
        f'and for {str(hotel["num_of_rooms"])} rooms. '
        f'Click "Search" and see availability for hotel room, then Click on "Reserve", '
        f'select the first accommodation, choose {str(hotel["num_of_rooms"])} in "select rooms", '
        f'then click "I\'ll Reserve" and fill the required details as following, '
        f'First Name: {user["first_name"]}, Last Name: {user["last_name"]}, '
        f'email: {user["email"]}, phone number: {user["phone_number"]}. '
        f'Then Click on "Final: Next details".'
    )
    
    return prompt

def generate_flight_prompt(response_json,cab):
    try:
        email = response_json["user"]["email"]
        password = response_json["user"]["password"]
        departure_airport = response_json["flight"]["departure"]["airport"]
        arrival_airport = response_json["flight"]["arrival"]["airport"]
        departure_date = response_json["flight"]["departure"]["time"].split("T")[0]
        num_passengers = cab["num_passengers"]
        # print("################################"+num_passengers)

        prompt = (
            f'Open Booking.com in your web browser. If prompted, accept or dismiss any cookie or popup dialogs. '
            f'Click on the "Sign In" button in the top-right corner and choose "Sign in with Google." '
            f'In the Google login window, enter the email address {email}, click "Next", then enter the password {password}, '
            f'and click "Next" again to log in. Once signed in, go to the Flights section on the homepage. '
            f'Choose the "One-way" trip option. Under "Leaving from," enter {arrival_airport}, and under "Going to," enter {departure_airport}. '
            f'Set the departure date to {departure_date}, and update the number of travelers to {num_passengers} adults. '
            f'Click "Search" to see available flights. Once results are displayed, choose the most suitable option based on timing or price. '
            f'Continue through the booking steps until the passenger information section, and stop before final payment confirmation.'
        )

        return prompt
    except KeyError as e:
        return f"Failed to process travel plan: missing key {str(e)}"


def generate_cab_prompt(data):
    try:
        departure_airport = data["flight"]["departure"]["airport"]
        hotel_name = data["hotel"]["name"]
        hotel_address = data["hotel"]["address"]
        user_email = data["user"]["email"]
        user_password = data["user"]["password"]

        return (
            f"Implement an Uber ride-booking system that allows a user to schedule a ride from "
            f"{departure_airport}, to the {hotel_name}, {hotel_address}. "
            f"User authentication should be handled via Google Sign-In, using the account associated with "
            f"{user_email} and password {user_password}. "
            f"The system should support seamless login and automate the cab booking process for this predefined route."
        )
    except KeyError as e:
        return f"Cab prompt generation failed: missing key {str(e)}"


@app.route('/travel/itinerary/latest', methods=['GET'])
def get_latest_itinerary():
    if not latest_itinerary:
        return jsonify({"message": "No itinerary generated yet."}), 404
    return jsonify(latest_itinerary)



@app.route('/travel/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})


if __name__ == '__main__':
    app.run(port=5004, debug=True)



