import requests
import pandas as pd
from datetime import datetime, timezone


# Base URL for the hackathon API
BASE_URL = "https://hackutd2025.eog.systems/api"

# Make a GET request to fetch cauldron info
response = requests.get(f"{BASE_URL}/Information/cauldrons")
response.raise_for_status()  # raises an exception if the request failed

# Convert the JSON response to a list of dictionaries
cauldrons = response.json()

# Load into a Pandas DataFrame
df_cauldrons = pd.DataFrame(cauldrons)

# Display the DataFrame
print(df_cauldrons)


# Base URL for the hackathon API
BASE_URL = "https://hackutd2025.eog.systems/api"

# Make a GET request to fetch ticket info
response = requests.get(f"{BASE_URL}/Tickets")
response.raise_for_status()  # raises an exception if the request failed

# Convert the JSON response to Python objects
tickets_response = response.json()

# Extract the list of tickets
tickets = tickets_response.get("transport_tickets", [])

# Load into a Pandas DataFrame
df_tickets = pd.DataFrame(tickets)

# Display the DataFrame
print(df_tickets)