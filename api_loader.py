import requests
import pandas as pd

# Base URL for the hackathon API
BASE_URL = "https://hackutd2025.eog.systems/api"

def fetch_cauldron_levels() -> pd.DataFrame:
    """
    Fetches the minute-by-minute cauldron level data.
    This uses the CORRECT logic to flatten the nested JSON.
    """
    print("Fetching cauldron levels...")
    url = f"{BASE_URL}/Data/?start_date=0&end_date=2000000000"
    response = requests.get(url)
    response.raise_for_status()  # stop if there's a request error
    json_data = response.json()

    # Flatten the JSON into a list of records
    records = []
    for entry in json_data:
        timestamp = entry['timestamp']
        for cauldron_id, level in entry['cauldron_levels'].items():
            records.append({
                "timestamp": timestamp,
                "cauldron_id": cauldron_id,
                "volume": level  # Renaming to 'volume' to match our analysis code
            })

    df = pd.DataFrame(records)
    
    # CRITICAL: Convert timestamp strings to datetime objects
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"Cauldron levels fetched. (Total {len(df)} records)")
    
    # Return the "long" DataFrame. DO NOT PIVOT.
    return df

def fetch_tickets() -> pd.DataFrame:
    """
    Fetches all transport tickets.
    """
    print("Fetching tickets...")
    url = f"{BASE_URL}/Tickets"
    response = requests.get(url)
    response.raise_for_status()
    
    tickets_response = response.json()
    # Check if 'transport_tickets' key exists, otherwise use the root list
    if 'transport_tickets' in tickets_response:
        tickets = tickets_response.get("transport_tickets", [])
    else:
        tickets = tickets_response # Handle if it's just a list
    
    df = pd.DataFrame(tickets)
    
    # CRITICAL: Convert date strings to datetime objects
    df['date'] = pd.to_datetime(df['date'])
    print("Tickets fetched.")
    return df

def fetch_cauldron_info() -> pd.DataFrame:
    """
    Fetches the static info about each cauldron (name, location, etc.)
    """
    print("Fetching cauldron info...")
    url = f"{BASE_URL}/Information/cauldrons"
    response = requests.get(url)
    response.raise_for_status()
    
    data = response.json()
    df = pd.DataFrame(data)
    print("Cauldron info fetched.")
    return df

# You can run this file by itself to test it
# if __name__ == "__main__":
#     df_levels = fetch_cauldron_levels()
#     print("\n--- Cauldron Levels (Head) ---")
#     print(df_levels.head())
#     print(df_levels.info())
    
#     df_tickets = fetch_tickets()
#     print("\n--- Tickets (Head) ---")
#     print(df_tickets.head())
#     print(df_tickets.info())