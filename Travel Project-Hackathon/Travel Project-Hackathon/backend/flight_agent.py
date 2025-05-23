from flask import Flask, request, jsonify
from datetime import datetime
import requests
 
app = Flask(__name__)
 
API_KEY = "98393e02b2422dc99abf81520b7e36db"
 
@app.route('/flights/search/all', methods=['POST'])
def search_all_flights():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "No JSON payload provided."
            }), 400

        required_fields = ['source', 'destination']
        if not all(field in data for field in required_fields):
            return jsonify({
                "status": "error",
                "message": "Missing required fields: source, destination"
            }), 400

        source = data['source'].strip().upper()
        destination = data['destination'].strip().upper()

        api_url = (
            f"http://api.aviationstack.com/v1/flights?access_key={API_KEY}"
            f"&dep_iata={source}&arr_iata={destination}"
        )

        response = requests.get(api_url, timeout=30)
        response.raise_for_status()

        api_data = response.json()
        
        return jsonify({
            "status": "success",
            "data": api_data  # Return the complete API response
        }), 200

    except requests.exceptions.Timeout:
        return jsonify({
            "status": "error",
            "message": "Flight API request timed out."
        }), 504
    except requests.exceptions.RequestException as e:
        return jsonify({
            "status": "error",
            "message": f"Flight API request failed: {str(e)}"
        }), 502
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500

def handle_flight_prompt(prompt: str):
    """
    Simulates handling the hotel booking prompt.
    """
    print("Received prompt:")
    print(prompt)
  
@app.route('/flights/search', methods=['POST'])
def search_flights():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "No JSON payload provided."
            }), 400
 
        required_fields = ['source', 'destination', 'until_date']
        if not all(field in data for field in required_fields):
            return jsonify({
                "status": "error",
                "message": "Missing required fields: source, destination, until_date"
            }), 400
 
        source = data['source'].strip().upper()
        destination = data['destination'].strip().upper()
        until_date_str = data['until_date'].strip()
        preferred_airline = data.get('airline', '').strip().lower()
 
        try:
            until_date = datetime.strptime(until_date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({
                "status": "error",
                "message": "Invalid date format. UseYYYY-MM-DD."
            }), 400
 
        api_url = (
            f"http://api.aviationstack.com/v1/flights?access_key={API_KEY}"
            f"&dep_iata={source}&arr_iata={destination}"
        )
        if preferred_airline:
            api_url += f"&airline_name={preferred_airline}"
 
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
 
        api_data = response.json()
        flights_data = api_data.get("data", [])
 
        if not isinstance(flights_data, list):
            return jsonify({
                "status": "error",
                "message": "Unexpected API response structure."
            }), 500
 
        results = []
        for flight in flights_data:
            flight_status = flight.get("flight_status", "").lower()
            if flight_status == "landed":
                continue
 
            airline_info = flight.get("airline") or {}
            airline_name = airline_info.get("name", "").lower()
            if preferred_airline and preferred_airline not in airline_name:
                continue
 
            dep_info = flight.get("departure") or {}
            arr_info = flight.get("arrival") or {}
            dep_time = dep_info.get("scheduled")
            arr_time = arr_info.get("scheduled")
 
            if dep_time:
                try:
                    dep_dt = datetime.fromisoformat(dep_time.replace("Z", "+00:00"))
                    if dep_dt.date() > until_date.date():
                        continue
                except Exception:
                    continue
 
            duration = None
            if dep_time and arr_time:
                try:
                    arr_dt = datetime.fromisoformat(arr_time.replace("Z", "+00:00"))
                    duration_min = int((arr_dt - dep_dt).total_seconds() / 60)
                    duration = f"{duration_min // 60}h {duration_min % 60}m"
                except Exception:
                    pass
 
            results.append({
                "flight_number": flight.get("flight", {}).get("iata", ""),
                "airline": airline_info.get("name", ""),
                "departure": {
                    "airport": dep_info.get("iata", ""),
                    "time": dep_time,
                    "terminal": dep_info.get("terminal", ""),
                    "gate": dep_info.get("gate", "")
                },
                "arrival": {
                    "airport": arr_info.get("iata", ""),
                    "time": arr_time,
                    "terminal": arr_info.get("terminal", ""),
                    "gate": arr_info.get("gate", "")
                },
                "duration": duration,
                "status": flight_status,
                "aircraft": (flight.get("aircraft") or {}).get("iata", "")
            })
 
        return jsonify({
            "status": "success",
            "count": len(results),
            "flights": results
        }), 200
 
    except requests.exceptions.Timeout:
        return jsonify({
            "status": "error",
            "message": "Flight API request timed out."
        }), 504
    except requests.exceptions.RequestException as e:
        return jsonify({
            "status": "error",
            "message": f"Flight API request failed: {str(e)}"
        }), 502
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500
 
 
@app.route('/flights/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200
 
 
if __name__ == '__main__':
    app.run(port=5001, debug=True)