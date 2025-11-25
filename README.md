# halqa_trip_organizerbot 🚗

Smart Carpool Organizer Bot (VRP) is a sophisticated Telegram bot designed to optimize carpooling logistics for group transportation. It uses the **Vehicle Routing Problem (VRP)** algorithm to assign passengers to drivers based on location, traffic, and capacity constraints.

## 🌟 Features

-   **Parallel Insertion Algorithm:** Uses intelligent clustering to ensure neighbors ride together and no driver is unfairly burdened with distant pickups.
-   **Real-World Logic:** Accounts for traffic (1.4x multiplier) and service time (3 mins per stop).
-   **Dual Mode:** Supports both **Inbound** (Home → Meeting Point) and **Outbound** (Meeting Point → Home) trips.
-   **Soft Capacity & Load Balancing:**
    -   Ideal capacity: 6 passengers.
    -   Soft limit: Up to 8 passengers (with penalty) to avoid sending a separate car for a single distant person.
-   **Arabic Interface:** Fully localized user experience.
-   **Interactive Maps:** Generates Google Maps links for every route.

## 🛠️ Tech Stack

-   **Language:** Python
-   **Optimization Engine:** Google OR-Tools
-   **Routing Data:** OSRM (Open Source Routing Machine)
-   **Interface:** Python Telegram Bot API

## 🚀 How to Run

1.  **Clone the repository:**

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure:**
    -   Add your Telegram Bot Token in the script.
    -   Ensure you have access to an OSRM server (Local or Public).

4.  **Run the bot:**
    ```bash
    python bot.py
    ```

## 📸 Usage

1.  Send `/start` to the bot.
2.  Send the location of the gathering point (Google Maps link or Coordinates).
3.  Choose the trip mode (Going to gathering / Returning home).
4.  Confirm attendance (The bot allows excluding absent members).
5.  Receive optimized routes with maps!

---

## 👨‍💻 Credits

**Made by Faisal Aldawood and Abdul Rahman Al Kharif**
