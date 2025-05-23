from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import BaseModel, ValidationError, Field
from enum import Enum
import random
import os
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
from typing import List, Dict, Optional, Any, Union
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# ----------------------------
# 1. Data Models
# ----------------------------

class RideType(str, Enum):
    UBERX = "uberX"
    UBER_BLACK = "uberBlack"
    UBERXL = "uberXL"
    UBER_COMFORT = "uberComfort"

class CabBookingRequest(BaseModel):
    # These fields are now directly provided by the "mother agent" (hardcoded for now)
    scheduled: str # ISO format string (e.g., "2025-05-21T19:15:00+00:00")
    airport: str     # e.g., "Anaa", "Lehigh Valley International"
    num_passengers: int
    # This field now accepts only a string for the drop-off location
    cab_drop_location: str # e.g., "Hotel Name, Hotel Address" or "Some City, Some Street"
    ride_type: Optional[RideType] = None # User preference for cab type
    user_prefs: Optional[str] = None # Detailed user preferences for AI advisor

class RideEstimate(BaseModel):
    low: float
    high: float
    duration: int  # seconds
    distance: float  # miles
    surge: float = 1.0
    ride_type: RideType

class Driver(BaseModel):
    id: str
    name: str
    rating: float
    car: str
    license_plate: str
    phone: str
    eta: int  # minutes (time to reach passenger)
    current_location_airport: str # The airport where the driver is based/currently waiting
    image_url: Optional[str] = None

class BookingResponse(BaseModel):
    request_id: str
    status: str
    driver: Dict
    vehicle: Dict
    pickup_time: str
    estimated_arrival: str
    recommendation_details: Dict
    chosen_ride_type: str
    estimates: List[Dict]

# ----------------------------
# 2. Mock Database & Locations
# ----------------------------

# --- Helper function to generate mock hotel data (copied from hotel_agent.py for consistency) ---
def generate_mock_hotels_for_cab_agent(num_hotels_per_city=200):
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
            
            # Generate price range (not used in cab_agent, but kept for consistency)
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

# Generate the mock hotel data for use in MOCK_HOTEL_LOCATIONS
generated_hotels_data = generate_mock_hotels_for_cab_agent(num_hotels_per_city=200)

# Mock location mapping for Airports
MOCK_LOCATIONS = {
    "Hyderabad Airport (HYD)": {"lat": 17.2366, "lng": 78.4294},
    "Indira Gandhi International": {"lat": 28.5665, "lng": 77.1031},
    "Los Angeles International": {"lat": 33.9416, "lng": -118.4009},
    "Harry Reid International": {"lat": 36.0840, "lng": -115.1537},
    "Logan International": {"lat": 42.3656, "lng": -71.0096},
    "San Francisco International": {"lat": 37.6213, "lng": -122.3790},
    "John F. Kennedy International": {"lat": 40.6413, "lng": -73.7781},
    "LaGuardia": {"lat": 40.7769, "lng": -73.8740},
    "New York (NYC)": {"lat": 40.7128, "lng": -74.0060},

    # --- Existing NEW AIRPORTS from previous cab_agent.py ---
    "Anaa": {"lat": -17.35, "lng": -145.416667},
    "Arrabury": {"lat": -26.75, "lng": 141.05},
    "El Arish International Airport": {"lat": 31.0633, "lng": 33.8344},
    "Les Salines": {"lat": 16.4833, "lng": -61.4333},
    "Apalachicola Regional": {"lat": 29.7397, "lng": -85.0274},
    "Arapoti": {"lat": -24.166667, "lng": -49.816667},
    "Aachen/Merzbruck": {"lat": 50.816667, "lng": 6.133333},
    "Arraias": {"lat": -12.916667, "lng": -46.9},
    "Aranuka": {"lat": 0.166667, "lng": 173.6},
    "Aalborg": {"lat": 57.092778, "lng": 9.85},
    "Mala Mala": {"lat": -24.033333, "lng": 31.55},
    "Al Ain": {"lat": 24.26, "lng": 55.609167},
    "Anapa": {"lat": 45.0, "lng": 37.333333},
    "Aarhus Airport": {"lat": 56.307222, "lng": 10.613333},
    "Altay": {"lat": 47.9625, "lng": 88.086111},
    "Araxa": {"lat": -19.608333, "lng": -47.016667},
    "Al Ghaydah": {"lat": 16.208333, "lng": 52.179722},
    "Quetzaltenango": {"lat": 14.86, "lng": -91.503889},
    "Abakan": {"lat": 53.75, "lng": 91.4},
    "Asaba International": {"lat": 6.223889, "lng": 6.643333},
    "Los Llanos": {"lat": 38.946667, "lng": -1.860278},
    "Abadan": {"lat": 30.366667, "lng": 48.266667},
    "Lehigh Valley International": {"lat": 40.6521, "lng": -75.4408},
    "Alpha": {"lat": -23.633333, "lng": 146.633333},
    "Municipal (ABI)": {"lat": 32.416667, "lng": -100.466667},
    "Felix Houphouet Boigny": {"lat": 5.261389, "lng": -3.926111},
    "Kabri Dar": {"lat": 7.083333, "lng": 45.0},
    "Ambler": {"lat": 67.106667, "lng": -157.85},
    "Bamaga Injinoo": {"lat": -10.875, "lng": 142.366667},
    "Aboisso": {"lat": 5.433333, "lng": -3.333333},
    "Albuquerque International": {"lat": 35.040278, "lng": -106.609167},
    "Municipal (ABR)": {"lat": 45.45, "lng": -98.42},
    "Abu Simbel": {"lat": 22.375, "lng": 31.625},
    "Al-Aqiq": {"lat": 20.627222, "lng": 41.6375},
    "Atambua": {"lat": -8.083333, "lng": 124.9},
    "Nnamdi Azikiwe International Airport": {"lat": 9.006944, "lng": 7.263056},
    "Albury": {"lat": -36.066667, "lng": 146.95},
    "Dougherty County": {"lat": 31.533333, "lng": -84.183333},
    "Dyce": {"lat": 57.2, "lng": -2.2},
    "General Juan N. Alvarez International": {"lat": 16.76, "lng": -99.932778},
    "Antrim County": {"lat": 44.97, "lng": -85.16},
    "Kotoka": {"lat": 5.605278, "lng": -0.166667},
    "Acandi": {"lat": 8.016667, "lng": -76.966667},
    "Lanzarote": {"lat": 28.95, "lng": -13.625},
    "Altenrhein": {"lat": 47.483333, "lng": 9.55},
    "The Blaye": {"lat": 45.15, "lng": -0.666667},
    "Anuradhapura": {"lat": 8.32, "lng": 80.4},
    "Nantucket Memorial": {"lat": 41.2536, "lng": -70.0601},
    "Ciudad Acuña International Airport": {"lat": 29.35, "lng": -100.933333},
    "Sahand": {"lat": 37.383333, "lng": 46.066667},
    "Araracuara": {"lat": -0.633333, "lng": -72.4},
    "Achinsk": {"lat": 56.283333, "lng": 90.5},
    "Municipal (ACT)": {"lat": 31.5936, "lng": -97.2301},
    "Arcata": {"lat": 40.9786, "lng": -124.1086},
    "Atlantic City International": {"lat": 39.4511, "lng": -74.5772},
    "Zabol Airport": {"lat": 31.066667, "lng": 61.533333},
    "Adana": {"lat": 37.0, "lng": 35.3},
    "Adnan Menderes Airport": {"lat": 38.3, "lng": 27.15},
    "Bole International": {"lat": 9.0, "lng": 38.8},
    "Aden International Airport": {"lat": 12.8, "lng": 45.02},
    "Adiyaman": {"lat": 37.733333, "lng": 38.2},
    "Lenawee County": {"lat": 41.92, "lng": -84.07},
    "Aldan": {"lat": 58.6, "lng": 125.4},
    "Arandis": {"lat": -22.45, "lng": 14.966667},
    "Marka International Airport": {"lat": 31.97, "lng": 35.98},
    "Adak Island Ns": {"lat": 51.8781, "lng": -176.6457},
    "Adelaide International Airport": {"lat": -34.933333, "lng": 138.533333},
    "Ardmore Municipal Airport": {"lat": 34.333333, "lng": -97.166667},
    "Andamooka": {"lat": -30.083333, "lng": 137.9},
    "Kodiak Airport": {"lat": 57.75, "lng": -152.483333},
    "Andrews": {"lat": 32.366667, "lng": -102.533333},
    "Addison Airport": {"lat": 32.966667, "lng": -96.833333},
    "Ada Municipal": {"lat": 34.783333, "lng": -96.683333},
    "Ardabil": {"lat": 38.333333, "lng": 48.333333},
    "Leuchars": {"lat": 56.383333, "lng": -2.866667},
    "Alldays": {"lat": -22.7, "lng": 29.5},
    "San Andres Island": {"lat": 12.583333, "lng": -81.7},
    "Abemama Atoll": {"lat": 0.483333, "lng": 173.866667},
    "Aek Godang": {"lat": 1.583333, "lng": 99.4},
    "Abéché": {"lat": 13.816667, "lng": 20.833333},
    "Albert Lea": {"lat": 43.683333, "lng": -93.383333},
    "Aioun El Atrouss": {"lat": 16.7, "lng": -9.633333},
    "Aeroparque Jorge Newbery": {"lat": -34.55, "lng": -58.416667},
    "Sochi/Adler International Airport": {"lat": 43.433333, "lng": 39.95},
    "Vigra": {"lat": 62.566667, "lng": 6.1},
    "Allakaket": {"lat": 66.55, "lng": -152.65},
    "Abu Musa": {"lat": 25.875, "lng": 55.0},
    "Alexandria International": {"lat": 31.3275, "lng": -92.2961},
    "Akureyri": {"lat": 65.666667, "lng": -18.1},
    "San Rafael": {"lat": -34.6, "lng": -68.3},
    "Port Alfred": {"lat": -33.583333, "lng": 26.883333},
    "USAF Academy Airstrip": {"lat": 39.0, "lng": -104.85},
    "Amalfi": {"lat": -6.216667, "lng": -79.8},
    "Alta Floresta": {"lat": -10.283333, "lng": -56.1},
    "Municipal (AFN)": {"lat": 40.733333, "lng": -74.083333},
    "Municipal (AFO)": {"lat": 44.533333, "lng": -108.533333},
    "Zarafshan": {"lat": 41.566667, "lng": 64.216667},
    "Afutara Aerodrome": {"lat": -8.6, "lng": 160.05},
    "Fort Worth Alliance": {"lat": 32.966667, "lng": -97.35},
    "Afyon": {"lat": 38.75, "lng": 30.55},
}

# Add major US cities as mock airports for broader coverage
US_CITIES_AS_AIRPORTS = [
    "Houston Airport", "Phoenix Airport", "Philadelphia Airport", "San Antonio Airport", "San Diego Airport",
    "Dallas Airport", "San Jose Airport", "Austin Airport", "Jacksonville Airport", "Fort Worth Airport",
    "Columbus Airport", "Charlotte Airport", "Indianapolis Airport", "Seattle Airport", "Denver Airport",
    "Washington D.C. Airport", "Boston Airport", "El Paso Airport", "Nashville Airport", "Detroit Airport",
    "Oklahoma City Airport", "Portland Airport", "Memphis Airport", "Louisville Airport", "Baltimore Airport",
    "Milwaukee Airport", "Albuquerque Airport", "Tucson Airport", "Fresno Airport", "Sacramento Airport",
    "Kansas City Airport", "Mesa Gateway Airport", "Atlanta Airport", "Omaha Airport", "Colorado Springs Airport",
    "Raleigh-Durham Airport", "Miami International Airport", "Virginia Beach Airport", "Long Beach Airport", "Oakland Airport",
    "Minneapolis-Saint Paul Airport", "Tulsa Airport", "Wichita Dwight D. Eisenhower Airport", "New Orleans Airport", "Arlington Municipal Airport"
]

for city_airport_name in US_CITIES_AS_AIRPORTS:
    if city_airport_name not in MOCK_LOCATIONS:
        # Assign approximate coordinates for new city airports
        MOCK_LOCATIONS[city_airport_name] = {
            "lat": random.uniform(25.0, 49.0), # Latitude range for contiguous USA
            "lng": random.uniform(-125.0, -67.0) # Longitude range for contiguous USA
        }

# Mock Hotel Locations (for drop-off): Name + Address string mapped to mock coordinates
MOCK_HOTEL_LOCATIONS = {
    # Existing mock hotel locations
    "Taj Falaknuma Palace, Engine Bowli, Falaknuma, Hyderabad, Telangana 500053": {"lat": 17.3204, "lng": 78.4735},
    "ITC Kohenur, Hitec City, Hyderabad, Telangana 500081": {"lat": 17.4475, "lng": 78.3900},
    "The Leela Palace, Africa Ave, Diplomatic Enclave, Chanakyapuri, New Delhi, Delhi 110023": {"lat": 28.5988, "lng": 77.2104},
    "The Oberoi, Nariman Point, Mumbai, Maharashtra 400021": {"lat": 18.9213, "lng": 72.8228},
    "Four Seasons Hotel, Doheny Dr, Los Angeles, CA 90048": {"lat": 34.0768, "lng": -118.3846},
    "The Venetian Resort, Las Vegas Blvd S, Las Vegas, NV 89109": {"lat": 36.1210, "lng": -115.1704},
    "The Ritz-Carlton, Avery St, Boston, MA 02111": {"lat": 42.3547, "lng": -71.0634},
    "Hilton San Francisco Union Square, O'Farrell St, San Francisco, CA 94102": {"lat": 37.7865, "lng": -122.4101},
    "The Plaza Hotel, Fifth Ave, New York, NY 10019": {"lat": 40.7646, "lng": -73.9749},
    "Hyatt Regency Orlando International Airport, Jeff Fuqua Blvd, Orlando, FL 32827": {"lat": 28.4316, "lng": -81.2858},
    "Hotel Near Apalachicola Regional, Bay Ave, Apalachicola, FL 32320": {"lat": 29.7200, "lng": -85.0100},
    "Comfort Inn & Suites, Airport Rd, Lehigh Valley, PA 18031": {"lat": 40.6380, "lng": -75.4710},
    "Best Western Plus, N 1st St, Abilene, TX 79603": {"lat": 32.4400, "lng": -100.4500},
    "The Grand Hotel, S Carolina Ave, Atlantic City, NJ 08401": {"lat": 39.3620, "lng": -74.4390},
    "Radisson Blu Plaza Delhi Airport, NH8, New Delhi, Delhi 110037": {"lat": 28.5552, "lng": 77.1203},
    "Novotel Hyderabad Airport, Airport Rd, Shamshabad, Hyderabad, Telangana 500108": {"lat": 17.2435, "lng": 78.4325},
}

# Add hotels from generated_hotels_data to MOCK_HOTEL_LOCATIONS
for city, hotels in generated_hotels_data.items():
    for hotel in hotels:
        full_address = f"{hotel['name']}, {hotel['address']}"
        if full_address not in MOCK_HOTEL_LOCATIONS:
            # Assign approximate coordinates for new hotels based on city center
            # These are very rough approximations for demonstration purposes
            city_lat = MOCK_LOCATIONS.get(f"{city} Airport", {}).get("lat", random.uniform(25.0, 49.0))
            city_lng = MOCK_LOCATIONS.get(f"{city} Airport", {}).get("lng", random.uniform(-125.0, -67.0))
            MOCK_HOTEL_LOCATIONS[full_address] = {
                "lat": city_lat + random.uniform(-0.05, 0.05), # Small offset from city/airport
                "lng": city_lng + random.uniform(-0.05, 0.05)
            }


def generate_mock_drivers(num_drivers_per_location: int = 15) -> Dict[str, Dict[RideType, List[Driver]]]:
    """
    Generate mock drivers associated with specific airport locations.
    Returns a nested dictionary: {airport_name: {ride_type: [Driver, ...]}}
    """
    all_drivers = {}
    
    first_names = ["John", "Sarah", "Mike", "Emily", "David", "Lisa", "Robert", 
                  "Jennifer", "James", "Patricia", "William", "Elizabeth"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia"]

    airport_locations = list(MOCK_LOCATIONS.keys())
    airport_locations = [loc for loc in airport_locations if "(NYC)" not in loc]

    for airport_name in airport_locations:
        all_drivers[airport_name] = {
            RideType.UBERX: [],
            RideType.UBER_BLACK: [],
            RideType.UBERXL: [],
            RideType.UBER_COMFORT: []
        }
        
        for i in range(num_drivers_per_location):
            iata_code_match = re.search(r'\(([A-Z]{3})\)', airport_name)
            if iata_code_match:
                iata_code = iata_code_match.group(1)
            elif airport_name == "Indira Gandhi International":
                iata_code = "DEL"
            elif "International" in airport_name:
                iata_code = "".join([word[0] for word in airport_name.split() if len(word) > 2 and word[0].isupper()][:3]).upper()
                if len(iata_code) < 3:
                    iata_code = airport_name[:3].upper()
            else:
                iata_code = airport_name[:3].upper()
            
            driver_id = f"{iata_code}-{i+1}-{random.randint(100,999)}"
            full_name = f"{random.choice(first_names)} {random.choice(last_names)}"
            rating = round(random.uniform(4.5, 5.0), 1)
            phone = f"+1{random.randint(200, 999)}{random.randint(1000000, 9999999)}"
            eta = random.randint(2, 15)
            
            ride_type_choice = random.choices(
                [RideType.UBERX, RideType.UBERXL, RideType.UBER_COMFORT, RideType.UBER_BLACK],
                weights=[0.4, 0.25, 0.2, 0.15], k=1
            )[0]

            if ride_type_choice == RideType.UBERX:
                car = random.choice(["Toyota Camry", "Honda Accord", "Nissan Altima"])
            elif ride_type_choice == RideType.UBERXL:
                car = random.choice(["Chevrolet Suburban", "Ford Explorer", "Honda Pilot"])
            elif ride_type_choice == RideType.UBER_COMFORT:
                car = random.choice(["Toyota Avalon", "Hyundai Sonata", "Volkswagen Passat"])
            else:
                car = random.choice(["Lincoln Town Car", "Cadillac XTS", "Mercedes-Benz E-Class"])

            all_drivers[airport_name][ride_type_choice].append(
                Driver(
                    id=driver_id,
                    name=full_name,
                    rating=rating,
                    car=car,
                    license_plate=f"{random.choice(['ABC', 'XYZ', 'DEF'])}{random.randint(1000, 9999)}",
                    phone=phone,
                    eta=eta,
                    current_location_airport=airport_name
                )
            )
    return all_drivers

# Initialize mock drivers with 15 drivers per location
mock_drivers_by_location = generate_mock_drivers(num_drivers_per_location=15)

# ----------------------------
# 3. AI Recommendation Service
# ----------------------------

class AICabAdvisor:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-1.5-pro-latest')
    
    def recommend_ride(self, user_prefs: str, estimates: List[Dict], start_loc_name: str, end_loc_display: str, num_passengers: int) -> Dict:
        prompt = f"""
        You are an intelligent cab recommendation system. Analyze these ride options:

        Origin Airport: {start_loc_name}
        Destination: {end_loc_display}
        Number of Passengers: {num_passengers}

        User Preferences:
        {user_prefs if user_prefs else "No specific preferences provided."}

        Available Options:
        {json.dumps(estimates, indent=2)}

        Recommend the single best option considering:
        1. Price vs. comfort balance
        2. Number of passengers and luggage (assume standard luggage per passenger, factor in {num_passengers} passengers)
        3. Safety ratings (implied by ride type, e.g., Uber Black often has higher standards)
        4. Estimated arrival time (shorter duration is generally better)
        5. Surge pricing (lower surge is better)
        6. User's stated preferences.

        Provide a clear recommendation and a detailed reason for your choice.

        Respond with JSON containing:
        - "recommendation": chosen ride type (e.g., "uberX", "uberXL", "uberBlack", "uberComfort")
        - "reason": detailed explanation why this is the best choice for the user.
        - "price_analysis": comparison of costs if relevant.
        - "safety_notes": any safety considerations.
        - "passenger_suitability": how well the recommended car suits the number of passengers.
        """

        try:
            response = self.model.generate_content(prompt)
            clean_text = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(clean_text)
        except Exception as e:
            print(f"AI recommendation error: {e}")
            if estimates:
                if num_passengers > 3:
                    xl_options = [e for e in estimates if e['ride_type'] == RideType.UBERXL.value]
                    if xl_options:
                        return {
                            "recommendation": xl_options[0]['ride_type'],
                            "reason": f"Default recommendation (UberXL for {num_passengers} passengers) due to AI error: {e}",
                            "error": str(e)
                        }
                cheapest_option = min(estimates, key=lambda x: x['low'])
                return {
                    "recommendation": cheapest_option['ride_type'],
                    "reason": f"Default recommendation (cheapest) due to AI error: {e}",
                    "error": str(e)
                }
            return {
                "recommendation": "uberX",
                "reason": f"Default recommendation (uberX) due to AI error and no estimates: {e}",
                "error": str(e)
            }

# Initialize AI service
ai_advisor = AICabAdvisor()

# ----------------------------
# 4. API Endpoints
# ----------------------------

@app.route('/cabs/book', methods=['POST'])
def book_cab_unified():
    """
    Unified endpoint to analyze user needs, recommend, and book a cab.
    It uses hardcoded/temporary flight data for demonstration.
    Input example:
    {
        "scheduled": "2025-05-21T19:15:00+00:00",
        "airport": "Apalachicola Regional",
        "num_passengers": 2,
        "cab_drop_location": "Hotel Near Apalachicola Regional, Bay Ave, Apalachicola, FL 32320", # Hotel name and address
        "ride_type": null,
        "user_prefs": "I need a comfortable ride, willing to pay more for space."
    }
    """
    try:
        req_data = request.get_json()
        
        cab_request = CabBookingRequest(**req_data)

        flight_arrival_dt_str = cab_request.scheduled
        arrival_airport_full_name = cab_request.airport
        
        try:
            flight_arrival_dt = datetime.fromisoformat(flight_arrival_dt_str.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({"error": f"Invalid scheduled time format: {flight_arrival_dt_str}. Use ISO 8601 format."}), 400

        # --- Determine Cab Pickup Location (Airport) ---
        start_loc_coords = MOCK_LOCATIONS.get(arrival_airport_full_name)
        if not start_loc_coords:
            return jsonify({"error": f"Coordinates for arrival airport '{arrival_airport_full_name}' are not mapped. Please use one of the predefined airport names from MOCK_LOCATIONS."}), 400
        
        start_lat = start_loc_coords['lat']
        start_lng = start_loc_coords['lng']
        
        # --- Determine Cab Drop Location (Hotel or general address string) ---
        # The cab_drop_location is a string. We attempt to find its coordinates.
        drop_off_address_string = cab_request.cab_drop_location.strip()
        
        end_loc_coords = MOCK_HOTEL_LOCATIONS.get(drop_off_address_string)
        
        if not end_loc_coords:
            # If the exact string isn't found in mock hotel locations,
            # we'll approximate coordinates for demonstration.
            # In a real system, you'd integrate a geocoding API here.
            print(f"Warning: Drop-off location '{drop_off_address_string}' not found in MOCK_HOTEL_LOCATIONS. Approximating coordinates near the airport.")
            end_lat = start_lat + random.uniform(-0.1, 0.1) # Simulate nearby
            end_lng = start_lng + random.uniform(-0.1, 0.1)
            drop_off_display_name = f"{drop_off_address_string} (Approximated)"
        else:
            end_lat = end_loc_coords['lat']
            end_lng = end_loc_coords['lng']
            drop_off_display_name = drop_off_address_string

        num_passengers = cab_request.num_passengers
        user_preferred_ride_type = cab_request.ride_type
        user_prefs = cab_request.user_prefs or ""

        # --- 3. Get estimates for all ride types ---
        estimates = []
        base_distance = ((end_lat - start_lat)**2 + (end_lng - start_lng)**2)**0.5 * 70
        base_duration = base_distance * 120
        
        if base_distance < 0.1:
            base_distance = 0.1
            base_duration = 180

        pricing = {
            RideType.UBERX: 1.0,
            RideType.UBERXL: 1.5,
            RideType.UBER_COMFORT: 1.3,
            RideType.UBER_BLACK: 2.5
        }
        
        for ride_type_enum in RideType:
            base_price = (3.0 + (base_distance * 1.5)) * pricing[ride_type_enum]
            surge = random.choice([1.0, 1.2, 1.5, 2.0])
            
            estimates.append(RideEstimate(
                low=round(base_price * 0.9, 2),
                high=round(base_price * 1.1, 2),
                duration=int(base_duration * random.uniform(0.9, 1.1)),
                distance=round(base_distance, 1),
                surge=surge,
                ride_type=ride_type_enum
            ).dict())
        
        # --- 4. Determine chosen ride type (user preference or AI recommendation) ---
        chosen_ride_type = None
        recommendation_details = {}

        if user_preferred_ride_type:
            available_drivers_for_pref = mock_drivers_by_location.get(arrival_airport_full_name, {}).get(user_preferred_ride_type, [])
            if available_drivers_for_pref:
                chosen_ride_type = user_preferred_ride_type
                recommendation_details = {"reason": f"User preferred {user_preferred_ride_type.value} and drivers are available at {arrival_airport_full_name}."}
            else:
                print(f"User preferred {user_preferred_ride_type.value} but no drivers available at {arrival_airport_full_name}. Falling back to AI recommendation.")
                recommendation_details = ai_advisor.recommend_ride(
                    user_prefs=f"{user_prefs} (Preferred {user_preferred_ride_type.value} but none available at arrival airport).",
                    estimates=estimates,
                    start_loc_name=arrival_airport_full_name,
                    end_loc_display=drop_off_display_name,
                    num_passengers=num_passengers
                )
                ai_rec_type = recommendation_details.get('recommendation', 'uberX')
                chosen_ride_type = RideType(ai_rec_type) if ai_rec_type in [rt.value for rt in RideType] else RideType.UBERX
        else:
            # If no preference, ask AI to recommend
            recommendation_details = ai_advisor.recommend_ride(
                user_prefs=user_prefs,
                estimates=estimates,
                start_loc_name=arrival_airport_full_name,
                end_loc_display=drop_off_display_name,
                num_passengers=num_passengers
            )
            ai_rec_type = recommendation_details.get('recommendation', 'uberX')
            chosen_ride_type = RideType(ai_rec_type) if ai_rec_type in [rt.value for rt in RideType] else RideType.UBERX

        # --- 5. Book the ride ---
        available_drivers = mock_drivers_by_location.get(arrival_airport_full_name, {}).get(chosen_ride_type, [])
        
        # Fallback if recommended type has no drivers at the specific airport
        if not available_drivers:
            print(f"No drivers for chosen {chosen_ride_type.value} at {arrival_airport_full_name}. Trying any available uberX at this airport.")
            available_drivers = mock_drivers_by_location.get(arrival_airport_full_name, {}).get(RideType.UBERX, [])
            if available_drivers:
                chosen_ride_type = RideType.UBERX # Update chosen type to fallback
            else:
                return jsonify({"error": f"No drivers available for {chosen_ride_type.value} or uberX at {arrival_airport_full_name}. Booking failed."}), 404
        
        driver = random.choice(available_drivers)
        
        # Calculate pickup time relative to flight arrival time
        deplaning_buffer_minutes = random.randint(15, 30) 
        pickup_time = flight_arrival_dt + timedelta(minutes=deplaning_buffer_minutes + driver.eta)
        
        # Get the duration for the chosen ride type from the estimates
        chosen_ride_duration_seconds = next((e['duration'] for e in estimates if e['ride_type'] == chosen_ride_type.value), 1200) # Default 20 mins if not found
        estimated_arrival_at_dropoff = pickup_time + timedelta(seconds=chosen_ride_duration_seconds)
        
        booking_response = BookingResponse(
            request_id=f"REQ-{random.randint(1000, 9999)}",
            status="accepted",
            driver=driver.dict(),
            vehicle={
                "make": driver.car.split()[0],
                "model": " ".join(driver.car.split()[1:]),
                "license_plate": driver.license_plate
            },
            pickup_time=pickup_time.isoformat(),
            estimated_arrival=estimated_arrival_at_dropoff.isoformat(),
            recommendation_details=recommendation_details,
            chosen_ride_type=chosen_ride_type.value,
            estimates=estimates
        )
        
        return jsonify(booking_response.dict())
    
    except ValidationError as ve:
        print(f"Validation Error: {ve.errors()}")
        return jsonify({"error": "Invalid request data", "details": ve.errors()}), 400
    except Exception as e:
        print(f"Error in /cabs/book: {e}")
        return jsonify({"error": f"Internal server error: {e}"}), 500

def handle_cab_prompt(prompt: str):
    """
    Simulates handling the hotel booking prompt.
    """
    print("Received prompt:")
    print(prompt)

# ----------------------------
# 5. Health Check
# ----------------------------

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

# ----------------------------
# 6. Main Application Run
# ----------------------------

if __name__ == '__main__':
    app.run(port=5002, debug=True)
