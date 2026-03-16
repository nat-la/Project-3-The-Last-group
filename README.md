# Release Title: Commute Time Tracker Prototype
## Tag: v0.2.0-prototype
## Overview:
This is a web application that allows users to save commute locations and estimate travel times between them using a map based UI.

## How to run
### Prerequisites
* Node.js (frontend)
* Python 3.10+ (backend)
* A Maps API key set as an environment variable (see below)

### 1. Clone into and checkout prototype branch
* git clone https://github.com/nat-la/Project-3-The-Last-group.git
* cd Project-3-The-Last-group
* git checkout prototype-2

### 2. Start backend (FastAPI)

* cd .../backend
* python -m venv venv
* (for mac/linux)
  * source .venv/bin/activate
* (for windows)
  * .venv\Scripts\Activate
* uvicorn app.api::app --reload --port 8000
=======
* cd Project-3-The-Last-group
* run "python run_dev.py"


### 3. Start frontend (Vite + React)
* cd .../frontend
* npm install
* npm run dev

### 4. Open the application
* Frontend: http://localhost:5173
* Backend: http://127.0.0.1:8000/docs

## How to use prototype UI
* Go to the **Locations** page
* Add at least **2 locations**
  * Name of location + address, then save
* Go to the **Analyze** page
* Select an Origin and Destination from the dropdown menu
* Click analyze to view route line on map along with estimated travel time and distance

## P0 function requirements demonstrated
* P0: User location setup (users can define and store important locations)
* P0: Route and transport estimate
