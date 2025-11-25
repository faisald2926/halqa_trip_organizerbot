
# 🚗 halqa_trip_organizerbot

A sophisticated logistics bot designed to optimize group transportation in Riyadh. It utilizes the **Vehicle Routing Problem (VRP)** algorithm via Google OR-Tools to assign passengers to drivers based on real-time proximity, traffic constraints, and vehicle capacity.

## 🌟 Key Features

-   **Parallel Insertion Algorithm:** Uses a "Parallel Cheapest Insertion" strategy to ensure fair distribution and cluster neighbors together, preventing inefficient routing.
-   **Smart Outbound/Inbound Logic:**
    -   *Inbound:* Routes all cars from homes to a single gathering point.
    -   *Outbound:* Routes all cars from the gathering point back to homes (dropping passengers on the way).
-   **Soft Capacity & Crowding:**
    -   **Ideal Capacity:** 6 passengers.
    -   **Crowding Logic:** Allows up to 8 passengers if the alternative is an excessively long trip for another driver (Cost-Benefit Analysis).
-   **Real-World Heuristics:**
    -   **Traffic Multiplier:** Adds a 1.4x buffer to map times to account for Riyadh traffic.
    -   **Service Time:** Adds 3 minutes per stop for passenger boarding/alighting.
-   **Automated Backend:** Includes `setup_map.bat` to automatically configure the OSRM routing engine.

## 🏗️ System Architecture (How It Works)

Think of this application as a restaurant operation:
1.  **The Map Data (Ingredients):** The raw map file (`.osm.pbf`) downloaded by `setup_map.bat`.
2.  **OSRM Server (The Kitchen):** The Docker container that processes the map and calculates travel times.
3.  **The Bot (The Waiter):** The Python script (`bot.py`) that takes orders from Telegram, asks the "Kitchen" for travel times, and delivers the optimized routes to the user.

## 🚀 Installation & Setup

### Prerequisites
1.  **Python 3.9+** installed.
2.  **Docker Desktop** installed and running (Required for the map server).

### 1. Clone & Configure

# Install dependencies
pip install -r requirements.txt
````




## 📖 Detailed Usage Guide

### Step 1: Prepare the Map (One-Time Setup)

Before the bot can calculate anything, it needs a processed map of Saudi Arabia.

  * **Command:** Double-click `setup_map.bat` (or run it in terminal).
  * **What it does:** Downloads the raw map data (\~250MB) and processes it into a graph format that the routing engine can understand.
  * **When to run:** Only once when you first install the project, or if you want to update the map data.

### Step 2: Start the Map Server

  * **Command:**
    ```bash
    docker-compose up --build ( later just up without build )
    ```


### Step 3: Run the Bot

  * **Command:**
    ```bash
    python bot.py
    ```
  * **Explanation:** This starts the "Brain" of the operation.
    1.  It connects to Telegram using your Token.
    2.  It listens for messages (`/start`, location, attendance).
    3.  When calculating routes, it sends requests to your local OSRM server (Step 2) to get distances.
    4.  It runs the VRP algorithm and sends the results back to the chat.

### To Stop the Server

When you are done using the bot, you can stop the background map server to save RAM:

```bash
docker-compose down
```

## 📂 Project Structure

  - `bot.py`: Main application logic.
  - `setup_map.bat`: Automation script for downloading and processing map data.
  - `docker-compose.yml`: Configuration to run the OSRM server.
  - `osrm-data/`: Directory where map data is stored (created automatically).
  - `.env`: Stores your Telegram API Token (Not uploaded to GitHub).

## 👨‍💻 Credits

**Made by Faisal Aldawood and Abdulrahman Al Kharif**
