import requests
import pandas as pd

def get_potion_levels():
    """
    Gets full historical potion level data from the API and returns
      it as a wide-format pandas DataFrame:
      index: timestamp (datetime)
      columns: cauldron IDs
      values: potion levels at each timestamp
    """
    url = "https://hackutd2025.eog.systems/api/Data/?start_date=0&end_date=2000000000"
    response = requests.get(url)
    response.raise_for_status()
    json_data = response.json()

    # Flatten JSON into rows for DataFrame
    records = []
    for entry in json_data:
        ts = entry['timestamp']
        for cauldron_id, level in entry['cauldron_levels'].items():
            records.append({
                "timestamp": ts,
                "cauldron_id": cauldron_id,
                "level": level
            })

    # Create DataFrame
    df = pd.DataFrame(records)

    # Convert timestamp to datetime and pivot to wide
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df_wide = df.pivot(index='timestamp', columns='cauldron_id', values='level')

    return df_wide
