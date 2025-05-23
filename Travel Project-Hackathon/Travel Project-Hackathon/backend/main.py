import json
from controller_agent import run_controller_agent

def pretty_print_itinerary(itinerary: dict):
    """Print the itinerary details in a readable way."""
    print("\n=== Itinerary Summary ===\n")

    user = itinerary.get("user", {})
    print(f"User: {user.get('name', '')} ({user.get('email', '')})\n")

    flight = itinerary.get("flight", {})
    print("Flight:")
    print(f"  Airline: {flight.get('airline', 'N/A')}")
    print(f"  Flight Number: {flight.get('flight_number', 'N/A')}")
    print(f"  Departure: {flight.get('departure', {}).get('airport', 'N/A')} at {flight.get('departure', {}).get('time', 'N/A')}")
    print(f"  Arrival: {flight.get('arrival', {}).get('airport', 'N/A')} at {flight.get('arrival', {}).get('time', 'N/A')}")
    print(f"  Price: ${flight.get('price', 'N/A')}\n")

    hotel = itinerary.get("hotel", {})
    print("Hotel:")
    print(f"  Name: {hotel.get('hotelname', 'N/A')}")
    print(f"  Address: {hotel.get('address', 'N/A')}")
    print(f"  Price per Night: ${hotel.get('price_per_night', 'N/A')}")
    print(f"  Total Price: ${hotel.get('total_price', 'N/A')}\n")

    cab = itinerary.get("cab", {})
    print("Cab:")
    print(f"  Pickup Time: {cab.get('pickup_time', 'N/A')}")
    print(f"  Driver: {cab.get('driver_name', 'N/A')}")
    print(f"  Vehicle: {cab.get('vehicle', 'N/A')}")
    print(f"  Price: ${cab.get('price', 'N/A')}\n")

if __name__ == "__main__":
    # Example user preferences dictionary
    user_preferences = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "source_airport": "HYD",
        "destination_airport": "LAX",
        "until_date": "2025-06-01",
        "airline": "Delta",
        "destination_city": "Los Angeles",
        "num_of_rooms": 1,
        "checkin_date": "2025-06-02",
        "checkout_date": "2025-06-05",
        "num_passengers": 2,
        "ride_type": "standard",
        "cab_user_prefs": "quiet"
    }

    try:
        itinerary = run_controller_agent(user_preferences)
        print("Itinerary generated successfully!")
        pretty_print_itinerary(itinerary)
    except Exception as e:
        print(f"Error running controller agent: {e}")
