# Voyage ai

## 1. Project Overview 

### **Project Name**:*Voyage Ai- Travel Orchestrator* 
### **Description:** 
The AI Travel Orchestrator is a multi-agent system for rescheduling travel components like
flights, cabs, and hotels when disruptions occur, such as flight delays. It comprises a
Mother Agent (orchestrator), a Flight Agent, a Cab Agent, and a Hotel Agent. The system
uses LangGraph for workflow orchestration and Gemini Pro for decision-making

## 2. Prerequisites

- **Python Version:** 3.11
- **Steamlit**
- **flask**
- **playwright**
- **fast API**
- **Web ui**
- **Browser use**
- **Vs code**
- **Gemini model**

## 3. Project Setup

### Clone the Repository:
```
git clone https://github.com/Surisettideepika999/Hackathon_Zapcom_Voyage_ai.git
```

## 4. Configuration

**Ports**:
- hotel_agent.py: 5000
- flight_agent.py: 5001
- cab_agent.py: 5002
- controller_agent.py: 5004
- interface.py: 8501

## 5. Directory Structure

```
travel_project_hackathon/
│
├── backend/                            
│   ├── __init__.py                  
│   ├── main.py                          
│   ├── controller_agent.py             
│   ├── flight_agent.py                  
│   ├── hotel_agent.py                   
│   ├── cab_agent.py                   
│   ├── hotels_data.json                 
│   ├── requirements.txt                 
│
├── frontend/                           
│   ├── interface.py                     
│   ├── replan_data.json            
│
├── env/                               
│
├── README.md                         
├── .gitignore                           
└── .env                          

```

## 6. Project Structure Description

-**`backend/`**
Contains the core business logic for the travel planning system. Each agent (flight, cab, hotel) is responsible for handling a specific domain of the travel experience.

-**`main.py`**
Entry point of the backend application; it orchestrates the travel plan by interacting with various agent modules.

-**`controller_agent.py`**
Coordinates communication between the main orchestrator and agent modules. Also acts as a central point for logging, request validation, and response aggregation.

-**`flight_agent.py`**
Responsible for simulating flight booking logic, including itinerary generation and availability checks.

-**`hotel_agent.py`**
Simulates hotel booking by matching availability with requirements from the travel plan.

-**`cab_agent.py`**
Handles cab booking, including pickup and drop logic simulation.

-**`hotels_data.json`**
Mock dataset containing hotel availability and pricing, used by the hotel_agent.

-**`requirements.txt`**
Lists all Python dependencies needed for the backend to run, including standard libraries and utilities.

-**`frontend/`**
Contains components for simulating or building a user interface.

-**`interface.py`**
CLI or UI handler that accepts user input and invokes the backend orchestrator.

-**`replan_data.json`**
Sample input for re-planning a travel itinerary based on specific constraints or changes.

-**`env/`**
Virtual environment directory for Python package isolation.

## 7. API Endpoints

The Gateway Service routes to the following services:
### Authentication Service Routes

- `POST /travel/plan` – Takes details from the user
- `POST /flights/search` – To generate flight details.
- `POST /cab` – To fetch available cab details
- `POST /hotel` – To fetch hotel details

## 8. Steps to run the application
Open 5 terminals in the vs code, then each run the following
```
python hotel_agent.py
python flight_agent.py
python cab_agent.py
python controler_agent.py
streamlit run interface.py
```
The streamlit application will be opened in a browser provide the required fields and click on the submit. 3 prompts will be genearted for flight, 
hotel and cab agents. Provide the prompts to browser use, then it will automtically perform the bookings. Finally the reshceduled itinerary will be shown to the user.
