import streamlit as st
import json
from datetime import date
import os
import requests

# --- Page Setup ---
st.set_page_config(page_title="Flight Planner", page_icon="✈️", layout="wide")

# --- Initialize Session State ---
if "current_page" not in st.session_state:
    st.session_state.current_page = "main"
if "api_response" not in st.session_state:
    st.session_state.api_response = None

# --- Main Page ---
def show_main_page():
    st.title("✈️ Flight Planning Assistant")
    
    # --- Button Actions ---
    st.subheader("Actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗺️ RE-PLAN"):
            st.session_state.current_page = "replan"
    with col2:
        if st.button("⏱️ RE-SCHEDULE"):
            st.session_state.current_page = "reschedule"

# --- User Details ---
def render_user_details():
    st.markdown("### 👤 User Details")
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("First Name", key="user_first_name")
        phone_number = st.text_input("Phone Number", key="user_phone")
    with col2:
        last_name = st.text_input("Last Name", key="user_last_name")
        email = st.text_input("Email", key="user_email")
    password = st.text_input("Password", type="password", key="user_password")

    return {
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "name": f"{first_name.strip()} {last_name.strip()}",
        "phone_number": phone_number.strip(),
        "email": email.strip(),
        "password": password.strip()
    }

# --- Flight Details ---
def render_flight_details():
    st.markdown("### ✈️ Flight Details")
    col1, col2 = st.columns(2)
    with col1:
        source = st.text_input("Source Airport (IATA Code)", key="flight_source")
        airline = st.text_input("Airline", key="flight_airline")
    with col2:
        destination = st.text_input("Destination Airport (IATA Code)", key="flight_destination")
        until_date = st.date_input("Flight Bookable Until", value=date.today(), key="flight_until_date")

    return {
        "source": source.strip(),
        "destination": destination.strip(),
        "until_date": str(until_date),
        "airline": airline.strip()
    }

# --- Hotel Details ---
def render_hotel_details():
    st.markdown("### 🏨 Hotel Details")
    col1, col2 = st.columns(2)
    with col1:
        cityname = st.text_input("City Name", key="hotel_city")
        checkin_date = st.date_input("Check-in Date", value=date.today(), key="hotel_checkin")
    with col2:
        num_of_rooms = st.number_input("Number of Rooms", min_value=1, step=1, value=1, key="hotel_rooms")
        checkout_date = st.date_input("Check-out Date", value=date.today(), key="hotel_checkout")

    return {
        "cityname": cityname.strip(),
        "num_of_rooms": num_of_rooms,
        "checkin_date": str(checkin_date),
        "checkout_date": str(checkout_date)
    }

# --- Cab Details ---
def render_cab_details():
    st.markdown("### 🚗 Cab Details")
    num_passengers = st.number_input("Number of Passengers", min_value=1, step=1, value=1, key="cab_passengers")
    ride_type = st.selectbox("Ride Type", ["uberX", "uberXL", "uberBlack", "uberComfort"], key="cab_ride_type")
    user_prefs = st.text_area("User Preferences (e.g. luggage, comfort notes)", key="cab_prefs")

    return {
        "num_passengers": num_passengers,
        "ride_type": ride_type,
        "user_prefs": user_prefs.strip()
    }

# --- Validation Helper ---
def validate_fields(data):
    for key, val in data.items():
        if isinstance(val, str) and val == "":
            return False, key
        if isinstance(val, int) and val <= 0:
            return False, key
    return True, None

# --- Function to send data to API ---
def send_to_api(data, endpoint_suffix):
    url = f"http://localhost:5004/travel/{endpoint_suffix}"
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"API Error: {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        return False, f"Failed to connect to the API: {str(e)}"

# --- Re-Plan Page ---
def show_replan_page():
    st.title("🧭 Re-Plan Travel")
    userdetails = render_user_details()
    flightdetails = render_flight_details()
    hoteldetails = render_hotel_details()
    cabdetails = render_cab_details()

    if st.button("Submit RE-PLAN"):
        for section_name, section_data in [("userdetails", userdetails),
                                       ("flightdetails", flightdetails),
                                       ("hoteldetails", hoteldetails),
                                       ("cabdetails", cabdetails)]:
            valid, missing_field = validate_fields(section_data)
            if not valid:
                st.warning(f"⚠️ Please fill the field '{missing_field}' in {section_name} before submitting.")
                st.stop()

        data = {
            "userdetails": userdetails,
            "flightdetails": flightdetails,
            "hoteldetails": hoteldetails,
            "cabdetails": cabdetails
        }

        file_path = "replan_data.json"
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                try:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
                except json.JSONDecodeError:
                    existing_data = []
        else:
            existing_data = []

        existing_data.append(data)
        with open(file_path, "w") as f:
            json.dump(existing_data, f, indent=4)
        
        success, api_response = send_to_api(data, "plan")
        if success:
            st.session_state.api_response = api_response
            st.session_state.current_page = "response"
            st.rerun()
        else:
            st.error(f"Error: {api_response}")

    if st.button("Back to Main"):
        st.session_state.current_page = "main"
        st.rerun()

# --- Re-Schedule Page ---
def show_reschedule_page():
    st.title("🔁 Re-Schedule Travel")
    userdetails = render_user_details()
    flightdetails = render_flight_details()

    if st.button("Submit RE-SCHEDULE"):
        for section_name, section_data in [("userdetails", userdetails),
                                       ("flightdetails", flightdetails)]:
            valid, missing_field = validate_fields(section_data)
            if not valid:
                st.warning(f"⚠️ Please fill the field '{missing_field}' in {section_name} before submitting.")
                st.stop()

        data = {
            "userdetails": userdetails,
            "flightdetails": flightdetails
        }

        file_path = "reschedule_data.json"
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                try:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
                except json.JSONDecodeError:
                    existing_data = []
        else:
            existing_data = []

        existing_data.append(data)
        with open(file_path, "w") as f:
            json.dump(existing_data, f, indent=4)
        
        success, api_response = send_to_api(data, "plan")
        if success:
            st.session_state.api_response = api_response
            st.session_state.current_page = "response"
            st.rerun()
        else:
            st.error(f"Error: {api_response}")

    if st.button("Back to Main"):
        st.session_state.current_page = "main"
        st.rerun()

# --- Response Page ---
def show_response_page():
    st.title("✨ Your Travel Plan")
    
    if st.session_state.api_response is None:
        st.warning("No travel plan data available.")
        st.button("Back to Main", on_click=lambda: st.session_state.update({"current_page": "main"}))
        return
    
    response = st.session_state.api_response
    
    # Flight Information
    st.markdown("## ✈️ Flight Information")
    flight = response.get('flight', {})
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Airline:** {flight.get('airline', 'N/A')}")
        st.markdown(f"**Flight Number:** {flight.get('flight_number', 'N/A')}")
        st.markdown(f"**Status:** {flight.get('status', 'N/A')}")
    with col2:
        st.markdown(f"**Departure:** {flight.get('departure', {}).get('time', 'N/A')}")
        st.markdown(f"**Arrival:** {flight.get('arrival', {}).get('time', 'N/A')}")
        st.markdown(f"**Duration:** {flight.get('duration', 'N/A')}")
    
    st.markdown("---")
    
    # Hotel Information
    st.markdown("## 🏨 Hotel Information")
    hotel = response.get('hotel', {})
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Name:** {hotel.get('name', 'N/A')}")
        st.markdown(f"**Address:** {hotel.get('address', 'N/A')}")
    with col2:
        st.markdown(f"**Check-in:** {hotel.get('checkin_date', 'N/A')}")
        st.markdown(f"**Check-out:** {hotel.get('checkout_date', 'N/A')}")
        st.markdown(f"**Price Range:** {hotel.get('price_range', 'N/A')}")
    
    st.markdown("---")
    
    # Cab Information
    st.markdown("## 🚗 Cab Information")
    cab = response.get('cab', {})
    driver = cab.get('driver', {})
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Ride Type:** {cab.get('chosen_ride_type', 'N/A')}")
        st.markdown(f"**Driver:** {driver.get('name', 'N/A')}")
        st.markdown(f"**Car:** {driver.get('car', 'N/A')}")
    with col2:
        st.markdown(f"**ETA:** {cab.get('driver', {}).get('eta', 'N/A')} minutes")
        st.markdown(f"**Pickup Time:** {cab.get('pickup_time', 'N/A')}")
        st.markdown(f"**License Plate:** {driver.get('license_plate', 'N/A')}")
    
    st.markdown("---")
    
    # User Information
    st.markdown("## 👤 User Information")
    user = response.get('user', {})
    st.markdown(f"**Name:** {user.get('name', 'N/A')}")
    st.markdown(f"**Email:** {user.get('email', 'N/A')}")
    st.markdown(f"**Phone:** {user.get('phone_number', 'N/A')}")
    
    if st.button("Back to Main"):
        st.session_state.current_page = "main"
        st.rerun()

# --- Main App Logic ---
if st.session_state.current_page == "main":
    show_main_page()
elif st.session_state.current_page == "replan":
    show_replan_page()
elif st.session_state.current_page == "reschedule":
    show_reschedule_page()
elif st.session_state.current_page == "response":
    show_response_page()