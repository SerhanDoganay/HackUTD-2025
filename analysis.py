import pandas as pd
import numpy as np
import api_loader

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
    # Define noise as 5% of the fill rate and SAVE IT as a column
    df['noise_threshold'] = df['fill_rate'] * 0.05 
    
    df['actual_drain'] = np.where(
        df['actual_drain'] > df['noise_threshold'],  # The condition
        df['actual_drain'],                         # Value if True
        0                                           # Value if False
    )
    
    print("Analysis columns added.")
    return df

def get_drain_events(df_today: pd.DataFrame):
    """
    Finds all individual drain events by grouping consecutive
    minutes of draining.
    """
    df_today = df_today.sort_values(by=['cauldron_id', 'timestamp'])
    
    # Create a 'group_id' that changes every time a new drain starts
    # Only count drains that are NEGATIVE *and* greater than the noise threshold
    FAST_DRAIN_THRESHOLD = 10.0 
    is_draining = df_today['actual_drain'] > FAST_DRAIN_THRESHOLD
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
    """
    Matches drain events to tickets and flags discrepancies.
    This version loops through EVENTS first to be more robust.
    """
    
    flagged_tickets = []
    unlogged_drains = []
    
    # Make copies so we can remove items as we match them
    events_to_match = list(drain_events_list)
    tickets_to_match = list(tickets_today_list)
    
    # Set a tolerance for matching (e.g., 2% = 0.02)
    MATCH_TOLERANCE = 0.02 

    # --- THIS IS THE NEW LOGIC ---
    # Loop through each DRAIN EVENT and try to find a ticket for it
    for event in events_to_match:
        found_match = False
        
        # Try to find a matching ticket
        for i, ticket in enumerate(tickets_to_match):
            
            # Check for same cauldron
            if event['cauldron_id'] == ticket['cauldron_id']:
                
                # Check if amounts are within tolerance
                required_drain = ticket['amount_collected']
                actual_drain = event['total_drain']
                
                if abs(actual_drain - required_drain) <= (required_drain * MATCH_TOLERANCE):
                    # It's a match!
                    found_match = True
                    
                    # Remove the ticket so it can't be matched again
                    tickets_to_match.pop(i)
                    break # Stop searching for this event
        
        if not found_match:
            # We checked all tickets and none matched this event.
            # This is an "unlogged drain".
            unlogged_drains.append(event)

    # After checking all events, any ticket left in 'tickets_to_match'
    # is a "ghost" ticket (it had no matching event).
    flagged_tickets = tickets_to_match

    return flagged_tickets, unlogged_drains

# --- MAIN SCRIPT (This runs when you execute the file) ---
if __name__ == "__main__":
    
    print("Starting batch analysis...")
    
    # --- STEP 1: LOAD DATA ---
    cauldron_df = api_loader.fetch_cauldron_levels()
    tickets_df = api_loader.fetch_tickets()
    
    # --- STEP 2: PREPARE DATA ---
    cauldron_df = add_analysis_columns(cauldron_df)
    
    print("Data prepared. Analyzing specified days...")

    # --- STEP 3: DEFINE THE DATES YOU WANT TO TEST ---
    #
    # THIS IS THE PART YOU CHANGE
    # Instead of finding unique dates, just define your list.
    # Use 'YYYY-MM-DD' format.
    #
    dates_to_test = ["2025-10-30"]
    
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

        # --- A. "Daily Auditor" Check (Simple Total) ---
        total_calculated_drain = df_today['actual_drain'].sum()
        total_ticketed_drain = tickets_today['amount_collected'].sum()
        total_discrepancy = total_calculated_drain - total_ticketed_drain

        # --- B. "Detective" Check (Reconciliation) ---
        drain_events = get_drain_events(df_today)
        tickets_today_list = tickets_today.to_dict('records')
        
        flagged_tickets, unlogged_drains = reconcile_events_and_tickets(
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
            "unlogged_drains": unlogged_drains
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