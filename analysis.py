import pandas as pd
import numpy as np
import api_loader
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import uvicorn
from fastapi.middleware.cors import CORSMiddleware # or other middleware
from pydantic import BaseModel
import datetime

def get_baseline_fill_rate(cauldron_data: pd.DataFrame) -> float:
    """
    Calculates the baseline fill rate by finding the 90th percentile
    of all positive, minute-by-minute deltas.
    """
    delta = cauldron_data.sort_values(by='timestamp')['volume'].diff()
    
    # Filter for only positive deltas (when it's filling)
    positive_deltas = delta[delta > 0]
    
    if positive_deltas.empty:
        return 0
    
    # Use quantile(0.9) to find the "true" undisturbed fill rate.
    # This ignores the median, which might be polluted by slow drains.
    baseline_fill_rate = positive_deltas.median()
    return baseline_fill_rate

def add_analysis_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds 'fill_rate' and 'observed_delta' columns.
    """
    print("Adding analysis columns (fill_rate, observed_delta)...")
    
    fill_rate_map = {}
    for cauldron_id, data in df.groupby('cauldron_id'):
        fill_rate_map[cauldron_id] = get_baseline_fill_rate(data)

    df['fill_rate'] = df['cauldron_id'].map(fill_rate_map)
    
    # Calculate and store the raw, observed change
    df['observed_delta'] = df.groupby('cauldron_id')['volume'].diff().fillna(0)
    
    print("Analysis columns added.")
    return df

def get_drain_events(df_today: pd.DataFrame):
    """
    Finds only the "fast drain" events for ticket matching.
    """
    
    # A "Fast Drain" is any minute the cauldron level drops noticably
    FAST_DRAIN_THRESHOLD = -0.25
    
    df_today = df_today.sort_values(by=['cauldron_id', 'timestamp'])
    
    # Find all minutes that are part of a "fast drain"
    is_draining = df_today['observed_delta'] < FAST_DRAIN_THRESHOLD
    
    # Create a 'group_id' for consecutive draining minutes
    new_event_group = (is_draining != is_draining.shift()).cumsum()
    
    # Filter for only the draining minutes
    draining_data = df_today[is_draining]
    
    # Group by cauldron AND the new event group
    events_df = draining_data.groupby(['cauldron_id', new_event_group])
    
    drain_events_list = []
    
    #Loop through each event to calculate its true total drain
    for (cauldron_id, group_id), event_data in events_df:
        
        # Calculate the total potion lost
        total_delta_loss = event_data['observed_delta'].sum()
        
        # Calculate the total potion gained from filling
        # during that time 
        total_fill_gain = event_data['fill_rate'].sum()
        
        # The true amount the witch took is the gain minus loss
        total_drain = total_fill_gain - total_delta_loss
        
        # Setting a minimum to filter out small fluctuations
        MINIMUM_TICKET_THRESHOLD = 15.0
        
        if total_drain > MINIMUM_TICKET_THRESHOLD:
            drain_events_list.append({
                'cauldron_id': cauldron_id,
                'start_time': event_data['timestamp'].iloc[0],
                'total_drain': total_drain
            })

    return drain_events_list

def reconcile_events_and_tickets(drain_events_list, tickets_today_list):
    """
    Matches drain events to tickets using a "best-fit" algorithm.
    """
    
    flagged_tickets = []
    unlogged_drains = []
    reconciled_pairs = []
    
    events_to_match = list(drain_events_list)
    tickets_to_match = list(tickets_today_list)
    
    # We can keep a 5% tolerance between events and tickets for matching
    MATCH_TOLERANCE = 0.05

    # Loop through each DRAIN EVENT
    for event in events_to_match:
        
        best_match_ticket = None
        smallest_diff_percent = float('inf') # Start with infinity
        ticket_index_to_remove = -1

        # Finding the best match
        # Loop through all available tickets to find the single best partner
        for i, ticket in enumerate(tickets_to_match):
            
            # Only compare tickets for the same cauldron
            if event['cauldron_id'] == ticket['cauldron_id']:
                
                # Calculate the percentage difference
                # (Handle division by zero if ticket amount is 0)
                if ticket['amount_collected'] > 0:
                    diff_percent = abs(event['total_drain'] - ticket['amount_collected']) / ticket['amount_collected']
                else:
                    diff_percent = float('inf') # Can't match with a 0L ticket
                
                # If this is the new "best" match, record it
                if diff_percent < smallest_diff_percent:
                    smallest_diff_percent = diff_percent
                    best_match_ticket = ticket
                    ticket_index_to_remove = i

        # Validating the best app
        # After checking all tickets, see if our best find is correspondence
        if best_match_ticket is not None and smallest_diff_percent <= MATCH_TOLERANCE:
            reconciled_pairs.append({
                "ticket": best_match_ticket,
                "event": event
            })
            
            # Remove the ticket from the pool so it can't be used again
            tickets_to_match.pop(ticket_index_to_remove)
        
        else:
            # This event had no good match (or no match at all).
            # It is an "unlogged drain".
            unlogged_drains.append(event)

    # Marking remaining tickets as flagged
    # Any tickets left in the pool at the end are "ghost" tickets.
    flagged_tickets = tickets_to_match

    return flagged_tickets, unlogged_drains, reconciled_pairs

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cauldron_df = api_loader.fetch_cauldron_levels()
tickets_df = api_loader.fetch_tickets()
cauldron_df = add_analysis_columns(cauldron_df)

# --- MAIN SCRIPT Testing (This runs when you execute the file) ---
if __name__ == "__main__":
    uvicorn.run("analysis:app", host="127.0.0.1", port=8000, reload=True)

class QDayData(BaseModel):
    days: list[str]
@app.post("/query_days")
def query_day(in_days: QDayData):
    # --- STEP 3: DEFINE THE DATES YOU WANT TO TEST ---
    #
    # THIS IS THE PART YOU CHANGE
    # Instead of finding unique dates, just define your list.
    # Use 'YYYY-MM-DD' format.
    #
    dates_to_test = in_days.days
    
    # This list will hold our final report
    all_results = []

    # --- STEP 4: LOOP AND ANALYZE EACH DAY ---
    for target_date_str in dates_to_test:
        
        # Convert the string to a datetime.date object
        target_dt = pd.to_datetime(target_date_str).date()
        
        # Filter data for the specific day
        df_today = cauldron_df[cauldron_df['timestamp'].dt.date == target_dt]
        tickets_today = tickets_df[tickets_df['date'].dt.date == target_dt]

        # Check if there is data for this day
        if df_today.empty and tickets_today.empty:
            print(f"No data found for {target_date_str}, skipping.")
            continue
        
        # Get the total number of tickets by finding the length of the DataFrame
        total_tickets_count = len(tickets_today)
        
        # You can now use this variable. Let's print it:
        print(f"--- Found {total_tickets_count} tickets for {target_dt} ---")
        
        # --- A. "Daily Auditor" Check (New Robust Logic) ---
        
        # This logic is now separate and more accurate.
        # It calculates: Total_Out = Total_Fill - Net_Change
        
        total_calculated_drain = 0
        
        # Loop through each cauldron's data for the day
        for cauldron_id, data in df_today.groupby('cauldron_id'):
            if data.empty:
                continue
                
            # Get the single fill_rate for this cauldron (from Step 2)
            fill_rate = data['fill_rate'].iloc[0]
            
            # 1. Calculate Total_Fill
            # (e.g., 1.5L/min * 1440 minutes)
            total_fill = fill_rate * len(data) # len(data) is num of minutes
            
            # 2. Calculate Net_Change
            volume_start = data['volume'].iloc[0]
            volume_end = data['volume'].iloc[-1]
            net_change = volume_end - volume_start
            
            # 3. The formula: Total_Out = Total_Fill - Net_Change
            cauldron_drain_total = total_fill - net_change
            
            # Add this cauldron's total drain to the day's total
            total_calculated_drain += cauldron_drain_total
            
        # Now get the final discrepancy
        total_ticketed_drain = tickets_today['amount_collected'].sum()
        total_discrepancy = total_calculated_drain - total_ticketed_drain

        # --- B. "Detective" Check (Reconciliation) ---
        drain_events = get_drain_events(df_today)
        tickets_today_list = tickets_today.to_dict('records')
        
        flagged_tickets, unlogged_drains, reconciled_pairs = reconcile_events_and_tickets(
            drain_events, 
            tickets_today_list
        )
        
        # --- C. Store the results for this day ---
        day_summary = {
            "date": target_dt,
            "total_discrepancy_L": total_discrepancy,
            "flagged_tickets_count": len(flagged_tickets),
            "unlogged_drains_count": len(unlogged_drains),
            "flagged_tickets": flagged_tickets,
            "unlogged_drains": unlogged_drains,
            "reconciled_pairs": reconciled_pairs
        }
        all_results.append(day_summary)

    # --- STEP 5: REPORT THE FINDINGS ---
    print("\n--- Analysis Complete ---")
    
    if not all_results:
        print("No results to report for the specified dates.")
    else:
        results_df = pd.DataFrame(all_results)
        discrepancy_tolerance = 1.0
        
        flagged_days_df = results_df[
            (results_df['total_discrepancy_L'].abs() > discrepancy_tolerance) |
            (results_df['flagged_tickets_count'] > 0) |
            (results_df['unlogged_drains_count'] > 0)
        ]

        if flagged_days_df.empty:
            print("\n All specified days reconciled! No discrepancies found.")
        else:
            print("\n DISCREPANCIES FOUND on the following days:")
            print(flagged_days_df[['date', 'total_discrepancy_L', 'flagged_tickets_count', 'unlogged_drains_count']])
            # --- ADD THIS DEBUG BLOCK ---
            print("\n--- SUCCESSFULLY MATCHED PAIRS (for first flagged day) ---")

            # Get the full details for the first flagged day
            first_bad_day = flagged_days_df.iloc[0] # (this variable name is fine)

            # Get the list of pairs from the summary
            pairs = first_bad_day.get('reconciled_pairs', [])

            print(f"\nFound {len(pairs)} matched pairs for {first_bad_day['date']}:")
            for pair in pairs:
                ticket = pair['ticket']
                event = pair['event']
                # Calculate the difference
                diff = event['total_drain'] - ticket['amount_collected']

                print(f"  - MATCH: Ticket {ticket['ticket_id']} ({ticket['amount_collected']}L) <--> Event ({event['total_drain']:.2f}L) [Diff: {diff:+.2f}L]")
            print("\n--- DETAILED FLAGGED ITEMS (for first flagged day) ---")
            
            # Get the full details for the first flagged day
            first_bad_day = flagged_days_df.iloc[0]
            
            print(f"\nFlagged Tickets for {first_bad_day['date']}:")
            # Loop and print each flagged ticket's details
            for ticket in first_bad_day['flagged_tickets']:
                print(f"  - Ticket {ticket['ticket_id']}: Cauldron {ticket['cauldron_id']}, Amount: {ticket['amount_collected']}L")

            print(f"\nUnlogged Drains for {first_bad_day['date']}:")
            # Loop and print each unlogged drain's details
            for event in first_bad_day['unlogged_drains']:
                print(f"  - Event: Cauldron {event['cauldron_id']}, Total Drain: {event['total_drain']:.2f}L, Start: {event['start_time']}")
            # --- END DEBUG BLOCK ---

    def serialize_item(item):
        if isinstance(item, pd.Timestamp):
            return item.isoformat()
        elif isinstance(item, list):
            return [serialize_item(i) for i in item]
        elif isinstance(item, dict):
            return {k: serialize_item(v) for k, v in item.items()}
        else:
            return item

    serializable_results = [serialize_item(day) for day in all_results]
    return JSONResponse(content=jsonable_encoder(serializable_results))