import requests
import pandas as pd

# Base URL for the hackathon API
BASE_URL = "https://hackutd2025.eog.systems/api"


def get_cauldrons():
    """
    Gets cauldron metadata from the API and returns a Pandas DataFrame.
    Each row represents a cauldron with ID, name, location, and max volume.
    """
    response = requests.get(f"{BASE_URL}/Information/cauldrons")
    response.raise_for_status()  # Raise an error if the request failed

    # Convert JSON response (list of dicts) into DataFrame
    cauldrons = response.json()
    df_cauldrons = pd.DataFrame(cauldrons)
    return df_cauldrons


def get_tickets():
    """
    Gets potion transport ticket data from the API and returns a Pandas DataFrame.
    Each row represents a ticket with the amount collected, cauldron id, date, etc.
    """
    response = requests.get(f"{BASE_URL}/Tickets")
    response.raise_for_status()

    tickets_response = response.json()

    # Extract the list of tickets inside the "transport_tickets" key
    tickets = tickets_response.get("transport_tickets", [])
    df_tickets = pd.DataFrame(tickets)
    return df_tickets



print(df_tickets)
