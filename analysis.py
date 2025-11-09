import pandas as pd
import api_loader
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import uvicorn
from fastapi.middleware.cors import CORSMiddleware # or other middleware
from pydantic import BaseModel

def get_baseline_fill_rate(cauldron_data: pd.DataFrame) -> float:
    """
    Calculates the baseline fill rate for a single cauldron by finding
    the mode (most common value) of all positive, minute-by-minute deltas.
    """
    delta = cauldron_data.sort_values(by='timestamp')['volume'].diff()
    positive_deltas = delta[delta > 0]
    
    if positive_deltas.empty:
        return 0
    
    baseline_fill_rate = positive_deltas.mode()[0]
    return baseline_fill_rate

def add_analysis_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds 'fill_rate' and 'actual_drain' columns to the main DataFrame.
    """
    print("Calculating fill rates and drain...")
    
    # 1. Get the fill rate for every cauldron
    fill_rate_map = {}
    for cauldron_id, data in df.groupby('cauldron_id'):
        fill_rate_map[cauldron_id] = get_baseline_fill_rate(data)

    # 2. Add the new 'fill_rate' column by mapping the cauldron_id
    df['fill_rate'] = df['cauldron_id'].map(fill_rate_map)
    
    # 3. Calculate 'observed_delta'
    df['observed_delta'] = df.groupby('cauldron_id')['volume'].diff()

    # 4. Calculate 'actual_drain'
    df['actual_drain'] = (df['fill_rate'] - df['observed_delta']).fillna(0)
    
    # 5. Clean up the data (no negative drains)
    df['actual_drain'] = df['actual_drain'].apply(lambda x: max(0, x))
    
    print("Analysis columns added.")
    return df

def get_drain_events(df_today: pd.DataFrame):
    """
    Finds all individual drain events by grouping consecutive
    minutes of draining.
    """
    df_today = df_today.sort_values(by=['cauldron_id', 'timestamp'])
    
    # Create a 'group_id' that changes every time a new drain starts
    is_draining = df_today['actual_drain'] > 0
    new_event_group = (is_draining != is_draining.shift()).cumsum()
    
    # Filter for only the draining minutes
    draining_data = df_today[is_draining]
    
    # Group by cauldron AND the new event group, then sum the drains
    events_df = draining_data.groupby(
        ['cauldron_id', new_event_group]
    ).agg(
        start_time=('timestamp', 'first'),
        total_drain=('actual_drain', 'sum')
    ).reset_index()
    
    # This gives you a clean list of events
    # e.g., [{'cauldron_id': 'A', 'total_drain': 100.5}, ...]
    return events_df.to_dict('records')

def reconcile_events_and_tickets(drain_events_list, tickets_today_list):
    
    flagged_tickets = []
    unlogged_drains = []
    
    # Make copies so we can remove items as we match them
    events_to_match = list(drain_events_list)
    tickets_to_match = list(tickets_today_list)
    
    # Set a tolerance for matching (e.g., 2% = 0.02)
    # A 100L drain might be ticketed as 99.8L
    MATCH_TOLERANCE = 0.02 

    for ticket in tickets_today_list:
        found_match = False
        
        # Try to find a matching drain event
        for i, event in enumerate(events_to_match):
            
            # Check for same cauldron
            if event['cauldron_id'] == ticket['cauldron_id']:
                
                # Check if amounts are within tolerance
                required_drain = ticket['amount_collected']
                actual_drain = event['total_drain']
                
                if abs(actual_drain - required_drain) <= (required_drain * MATCH_TOLERANCE):
                    # It's a match!
                    found_match = True
                    
                    # Remove the event so it can't be matched again
                    events_to_match.pop(i)
                    break # Stop searching for this ticket
        
        if not found_match:
            # We checked all drains and none matched this ticket.
            # This is a "ghost" ticket or a fraudulent amount.
            flagged_tickets.append(ticket)

    # After checking all tickets, anything left in 'events_to_match'
    # is a drain event that *never got a ticket*. This is theft.
    unlogged_drains = events_to_match

    return flagged_tickets, unlogged_drains

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:3000"] for more control
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- STEP 1: LOAD DATA ---
cauldron_df = api_loader.fetch_cauldron_levels()
tickets_df = api_loader.fetch_tickets()
cauldron_df = add_analysis_columns(cauldron_df)

# --- MAIN SCRIPT (This runs when you execute the file) ---
if __name__ == "__main__":
    uvicorn.run("analysis:app", host="127.0.0.1", port=8000, reload=True)

class QDayData(BaseModel):
    days: list[str]

@app.post("/query_days")
def query_day(in_days: QDayData):
    dates_to_test = in_days.days
    all_results = []

    for target_date_str in dates_to_test:
        target_dt = pd.to_datetime(target_date_str).date()
        
        df_today = cauldron_df[cauldron_df['timestamp'].dt.date == target_dt]
        tickets_today = tickets_df[tickets_df['date'].dt.date == target_dt]

        if df_today.empty and tickets_today.empty:
            all_results.append({
                "date": target_date_str,
                "message": "No data found for this date."
            })
            continue

        drain_events = get_drain_events(df_today)
        tickets_today_list = tickets_today.to_dict('records')
        flagged_tickets, unlogged_drains = reconcile_events_and_tickets(
            drain_events, tickets_today_list
        )

        # Compute totals
        total_calculated_drain = df_today['actual_drain'].sum()
        total_ticketed_drain = tickets_today['amount_collected'].sum()
        total_discrepancy = total_calculated_drain - total_ticketed_drain

        # Add to results
        day_summary = {
            "date": target_date_str,
            "total_discrepancy_L": float(total_discrepancy),
            "flagged_tickets_count": len(flagged_tickets),
            "unlogged_drains_count": len(unlogged_drains),
            "drain_events": drain_events,           # includes start_time
            "flagged_tickets": flagged_tickets,     # list of problematic tickets
            "unlogged_drains": unlogged_drains      # list of un-ticketed drains
        }
        all_results.append(day_summary)

    return JSONResponse(content=jsonable_encoder({"results": all_results}))