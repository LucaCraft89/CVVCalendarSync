#!/usr/bin/env python3
"""
Debug script to test ClasseViva API and view responses.
Usage: python3 debug_api.py
"""

import json
import sys
import os
from classevivaSync import login, get_periods, get_agenda

def main():
    # Load configuration
    config_file = "/app/config.json" if os.path.isdir("/app") else "config.json"
    
    if not os.path.exists(config_file):
        print(f"Error: Config file not found: {config_file}")
        print("Please create config.json based on config.example.json")
        sys.exit(1)
    
    with open(config_file) as f:
        config = json.load(f)
    
    user_id = config.get("user_id")
    user_pass = config.get("user_pass")
    
    if not user_id or not user_pass:
        print("Error: Missing user_id or user_pass in config.json")
        sys.exit(1)
    
    student_id = "".join(filter(str.isdigit, user_id))
    
    print("=" * 60)
    print("ClasseViva API Debug Tool")
    print("=" * 60)
    print()
    
    try:
        # Test login
        print("1. Testing login...")
        login_response = login(user_id, user_pass)
        print("✓ Login successful")
        print(f"   User: {login_response.get('firstName')} {login_response.get('lastName')}")
        print(f"   Token: {login_response.get('token')[:20]}...")
        print()
        
        token = login_response.get("token")
        
        # Test periods
        print("2. Fetching periods...")
        periods = get_periods(student_id, token)
        print("✓ Periods fetched successfully")
        print(f"   Number of periods: {len(periods.get('periods', []))}")
        print()
        print("Periods Details:")
        print(json.dumps(periods, indent=2))
        print()
        
        # Test agenda
        if periods.get("periods"):
            period_start = periods["periods"][0]["dateStart"].replace("-", "")
            period_end = periods["periods"][-1]["dateEnd"].replace("-", "")
            
            print(f"3. Fetching agenda from {period_start} to {period_end}...")
            agenda = get_agenda(student_id, period_start, period_end, token)
            print("✓ Agenda fetched successfully")
            print(f"   Number of events: {len(agenda.get('agenda', []))}")
            print()
            print("Agenda Details (first 3 events):")
            for i, event in enumerate(agenda.get('agenda', [])[:3]):
                print(f"\n--- Event {i+1} ---")
                print(json.dumps(event, indent=2))
            
            if len(agenda.get('agenda', [])) > 3:
                print(f"\n... and {len(agenda.get('agenda', [])) - 3} more events")
            
            print()
            print("=" * 60)
            print("Full agenda JSON saved to: agenda_debug.json")
            with open("agenda_debug.json", "w") as f:
                json.dump(agenda, f, indent=2)
            
        print()
        print("✓ All API calls successful!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
