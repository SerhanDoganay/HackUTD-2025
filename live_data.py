import requests
import pandas as pd

# 1. Pull the full week of data
url = "https://hackutd2025.eog.systems/api/Data/?start_date=0&end_date=2000000000"
response = requests.get(url)
response.raise_for_status()  # stop if there's a request error
json_data = response.json()

# 2. Flatten the JSON into a DataFrame
records = []
for entry in json_data:
    timestamp = entry['timestamp']
    for cauldron_id, level in entry['cauldron_levels'].items():
        records.append({
            "timestamp": timestamp,
            "cauldron_id": cauldron_id,
            "level": level
        })

df = pd.DataFrame(records)

# 3. Set timestamp as datetime and pivot to wide format (each cauldron as a column)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df_wide = df.pivot(index='timestamp', columns='cauldron_id', values='level')

print(df_wide.head())
