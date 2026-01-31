#!/usr/bin/env python3
"""
Test script to verify the smart sync logic and change detection.
This script simulates the sync behavior without actually connecting to APIs.
"""

import json
import time
import hashlib
from typing import Dict

STATE_FILE = "sync_state_test.json"
FORCE_SYNC_INTERVAL = 3600  # 1 hour

def load_state() -> Dict:
    """Load the last sync state from file."""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"last_sync_time": 0, "agenda_hash": None, "last_force_sync": 0}

def save_state(state: Dict) -> None:
    """Save the sync state to file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def compute_test_hash(data: str) -> str:
    """Compute hash of test data."""
    return hashlib.sha256(data.encode()).hexdigest()

def should_sync(state: Dict, agenda_hash: str) -> tuple[bool, str]:
    """Determine if sync is needed."""
    current_time = time.time()
    last_force_sync = state.get("last_force_sync", 0)
    last_hash = state.get("agenda_hash")
    
    # Check if agenda has changed
    if last_hash != agenda_hash:
        return (True, f"Agenda changed (old: {last_hash[:8] if last_hash else 'none'}, new: {agenda_hash[:8]})")
    
    # Check if force sync interval has passed
    time_since_force_sync = current_time - last_force_sync
    if time_since_force_sync >= FORCE_SYNC_INTERVAL:
        return (True, f"Force sync ({int(time_since_force_sync/60)} min since last)")
    
    # No sync needed
    minutes_until_force = int((FORCE_SYNC_INTERVAL - time_since_force_sync) / 60)
    return (False, f"No changes, next force sync in {minutes_until_force} min")

def test_sync_logic():
    """Test the sync logic with various scenarios."""
    print("=== Testing Smart Sync Logic ===\n")
    
    # Test 1: First run (no state file)
    print("Test 1: First run (no state)")
    state = load_state()
    hash1 = compute_test_hash("event1,event2,event3")
    should, reason = should_sync(state, hash1)
    print(f"  Should sync: {should}")
    print(f"  Reason: {reason}")
    if should:
        state["last_sync_time"] = time.time()
        state["agenda_hash"] = hash1
        state["last_force_sync"] = time.time()
        save_state(state)
        print("  ✓ Synced and saved state\n")
    
    # Test 2: No changes (immediate re-run)
    print("Test 2: No changes detected")
    state = load_state()
    should, reason = should_sync(state, hash1)
    print(f"  Should sync: {should}")
    print(f"  Reason: {reason}\n")
    
    # Test 3: Changes detected
    print("Test 3: Changes detected (new event added)")
    state = load_state()
    hash2 = compute_test_hash("event1,event2,event3,event4")  # New event
    should, reason = should_sync(state, hash2)
    print(f"  Should sync: {should}")
    print(f"  Reason: {reason}")
    if should:
        state["last_sync_time"] = time.time()
        state["agenda_hash"] = hash2
        state["last_force_sync"] = time.time()
        save_state(state)
        print("  ✓ Synced due to changes\n")
    
    # Test 4: Force sync (simulate 1+ hour passed)
    print("Test 4: Force sync interval reached")
    state = load_state()
    state["last_force_sync"] = time.time() - 3700  # 61 minutes ago
    save_state(state)
    state = load_state()
    should, reason = should_sync(state, hash2)  # Same hash
    print(f"  Should sync: {should}")
    print(f"  Reason: {reason}")
    if should:
        state["last_sync_time"] = time.time()
        state["last_force_sync"] = time.time()
        save_state(state)
        print("  ✓ Force synced\n")
    
    # Test 5: Event deleted
    print("Test 5: Event deleted (changes detected)")
    state = load_state()
    hash3 = compute_test_hash("event1,event2,event3")  # Back to 3 events
    should, reason = should_sync(state, hash3)
    print(f"  Should sync: {should}")
    print(f"  Reason: {reason}")
    if should:
        print("  ✓ Would sync due to deletion\n")
    
    print("=== All Tests Complete ===")
    print(f"\nFinal state file: {STATE_FILE}")
    print("Check it with: cat sync_state_test.json")

if __name__ == "__main__":
    test_sync_logic()
