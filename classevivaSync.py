import datetime
import os
import requests
import json
import logging
import sys
import time
import hashlib
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import Dict, List, Optional

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# State file to track last sync and changes
STATE_FILE = "/app/sync_state.json" if os.path.isdir("/app") else "sync_state.json"
FORCE_SYNC_INTERVAL = 3600  # Force sync every 1 hour (in seconds)

# Event ID prefix to identify events created by this sync
EVENT_ID_PREFIX = "cvv_sync_"

# Configure requests session with retry logic
def get_requests_session() -> requests.Session:
    """Create a requests session with retry logic and connection pooling."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,  # Wait 2, 4, 8 seconds between retries
        status_forcelist=[408, 429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# Global session
http_session = get_requests_session()

def load_state() -> Dict:
    """Load the last sync state from file."""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                logger.debug(f"Loaded state: last_sync={state.get('last_sync_time', 'never')}, last_hash={state.get('agenda_hash', 'none')}")
                return state
    except Exception as e:
        logger.warning(f"Failed to load state file: {e}")
    return {"last_sync_time": 0, "agenda_hash": None, "last_force_sync": 0}

def save_state(state: Dict) -> None:
    """Save the sync state to file."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        logger.debug(f"Saved state: {state}")
    except Exception as e:
        logger.error(f"Failed to save state file: {e}")

def compute_agenda_hash(agenda: Dict) -> str:
    """Compute a hash of the agenda to detect changes."""
    # Create a consistent string representation of the agenda
    # Sort events by datetime to ensure consistent ordering
    events = sorted(
        agenda.get("agenda", []),
        key=lambda x: (x.get("evtDatetimeBegin", ""), x.get("evtId", ""))
    )
    
    # Create hash from key fields
    hash_data = []
    for event in events:
        event_str = (
            f"{event.get('evtId', '')}"
            f"{event.get('evtDatetimeBegin', '')}"
            f"{event.get('evtDatetimeEnd', '')}"
            f"{event.get('notes', '')}"
            f"{event.get('authorName', '')}"
        )
        hash_data.append(event_str)
    
    combined = "|".join(hash_data)
    return hashlib.sha256(combined.encode()).hexdigest()

def get_agenda(student_id: str, begin: str, end: str, token: str) -> Dict:
    """Fetch agenda from ClasseViva API with retry logic."""
    url = f"https://web.spaggiari.eu/rest/v1/students/{student_id}/agenda/all/{begin}/{end}"
    headers = {
        "Content-Type": "application/json",
        "Z-Dev-ApiKey": "Tg1NWEwNGIgIC0K",
        "User-Agent": "CVVS/std/4.1.7 Android/10",
        "Z-Auth-Token": token
    }
    
    logger.info(f"Fetching agenda for student {student_id} from {begin} to {end}")
    
    try:
        response = http_session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        event_count = len(data.get('agenda', []))
        logger.info(f"Successfully fetched {event_count} agenda items")
        
        if event_count > 0:
            logger.debug(f"Sample event: {data['agenda'][0].get('notes', 'N/A')}")
        
        return data
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while fetching agenda after 30 seconds")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch agenda: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from agenda API: {e}")
        raise

def login(user_id: str, user_pass: str) -> Dict:
    """Login to ClasseViva and get authentication token with retry logic."""
    url = "https://web.spaggiari.eu/rest/v1/auth/login"
    headers = {
        "Content-Type": "application/json",
        "Z-Dev-ApiKey": "Tg1NWEwNGIgIC0K",
        "User-Agent": "CVVS/std/4.1.7 Android/10"
    }
    body = {
        "ident": None,
        "pass": user_pass,
        "uid": user_id
    }
    
    logger.info(f"Attempting login for user {user_id}")
    
    try:
        response = http_session.post(url, headers=headers, data=json.dumps(body), timeout=30)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Login successful for {data.get('firstName', '')} {data.get('lastName', '')}")
        return data
    except requests.exceptions.Timeout:
        logger.error(f"Timeout during login after 30 seconds")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Login request failed: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from login API: {e}")
        raise

def generate_event_id(cvv_event: Dict) -> str:
    """Generate a unique event ID based on ClasseViva event data."""
    # Use evtId if available, otherwise create from event data
    if 'evtId' in cvv_event and cvv_event['evtId']:
        return f"{EVENT_ID_PREFIX}{cvv_event['evtId']}"
    
    # Fallback: create ID from event details
    event_str = f"{cvv_event.get('evtCode', '')}{cvv_event.get('evtDatetimeBegin', '')}{cvv_event.get('notes', '')}"
    return f"{EVENT_ID_PREFIX}{hash(event_str) & 0xFFFFFFFF}"

def sync_to_google_calendar(agenda: Dict, calendar_id: str, credentials_file: str) -> None:
    """Sync ClasseViva agenda to Google Calendar with improved error handling."""
    try: 
        logger.info("Authenticating with Google Calendar API")
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, 
            scopes=["https://www.googleapis.com/auth/calendar"]
        )
        service = build("calendar", "v3", credentials=credentials)
        
        # Get existing events created by this sync (filter by extended property)
        logger.info("Fetching existing synced events from Google Calendar")
        existing_events = []
        page_token = None
        
        try:
            while True:
                events_result = service.events().list(
                    calendarId=calendar_id,
                    privateExtendedProperty=f"{EVENT_ID_PREFIX}source=classeviva",
                    maxResults=250,
                    pageToken=page_token
                ).execute()
                
                existing_events.extend(events_result.get('items', []))
                page_token = events_result.get('nextPageToken')
                if not page_token:
                    break
        except Exception as e:
            logger.error(f"Failed to fetch existing events: {e}")
            raise
        
        logger.info(f"Found {len(existing_events)} existing synced events")
        
        # Create a map of existing events by their CVV event ID
        existing_events_map = {}
        for event in existing_events:
            extended_props = event.get('extendedProperties', {}).get('private', {})
            cvv_id = extended_props.get(f"{EVENT_ID_PREFIX}id")
            if cvv_id:
                existing_events_map[cvv_id] = event
        
        # Track which events we've seen in the current sync
        seen_event_ids = set()
        events_added = 0
        events_updated = 0
        events_skipped = 0
        
        # Process each event from ClasseViva
        for cvv_event in agenda.get("agenda", []):
            # Validate event data
            if not cvv_event.get("evtDatetimeBegin") or not cvv_event.get("evtDatetimeEnd"):
                logger.warning(f"Skipping event with missing datetime: {cvv_event.get('notes', 'Unknown')}")
                continue
            
            if cvv_event["evtDatetimeBegin"] >= cvv_event["evtDatetimeEnd"]:
                logger.warning(f"Skipping event with invalid time range: {cvv_event.get('notes', 'Unknown')}")
                continue
            
            # Generate unique event ID
            event_id = generate_event_id(cvv_event)
            seen_event_ids.add(event_id)
            
            # Prepare event body
            event_body = {
                "summary": cvv_event.get("notes", "ClasseViva Event"),
                "location": "",
                "description": (
                    f"Author: {cvv_event.get('authorName', 'N/A')}\n"
                    f"Class: {cvv_event.get('classDesc', 'N/A')}\n"
                    f"Subject: {cvv_event.get('notes', 'N/A')}\n"
                    f"\nSynced from ClasseViva"
                ),
                "start": {
                    "dateTime": cvv_event["evtDatetimeBegin"],
                    "timeZone": "Europe/Rome",
                },
                "end": {
                    "dateTime": cvv_event["evtDatetimeEnd"],
                    "timeZone": "Europe/Rome",
                },
                "extendedProperties": {
                    "private": {
                        f"{EVENT_ID_PREFIX}id": event_id,
                        f"{EVENT_ID_PREFIX}source": "classeviva"
                    }
                },
                "colorId": "9"  # Blue color for ClasseViva events
            }
            
            # Check if event already exists
            if event_id in existing_events_map:
                existing_event = existing_events_map[event_id]
                
                # Check if event needs updating
                needs_update = (
                    existing_event.get('summary') != event_body['summary'] or
                    existing_event.get('start', {}).get('dateTime') != event_body['start']['dateTime'] or
                    existing_event.get('end', {}).get('dateTime') != event_body['end']['dateTime'] or
                    existing_event.get('description') != event_body['description']
                )
                
                if needs_update:
                    try:
                        logger.info(f"Updating event: {event_body['summary']} ({cvv_event['evtDatetimeBegin']})")
                        service.events().update(
                            calendarId=calendar_id,
                            eventId=existing_event['id'],
                            body=event_body
                        ).execute()
                        events_updated += 1
                    except Exception as e:
                        logger.error(f"Failed to update event '{event_body['summary']}': {e}")
                        continue
                else:
                    logger.debug(f"Event unchanged: {event_body['summary']} ({cvv_event['evtDatetimeBegin']})")
                    events_skipped += 1
            else:
                # Create new event
                try:
                    logger.info(f"Adding new event: {event_body['summary']} ({cvv_event['evtDatetimeBegin']})")
                    service.events().insert(calendarId=calendar_id, body=event_body).execute()
                    events_added += 1
                except Exception as e:
                    logger.error(f"Failed to add event '{event_body['summary']}': {e}")
                    continue
        
        # Remove events that are no longer in ClasseViva
        events_deleted = 0
        for event_id, existing_event in existing_events_map.items():
            if event_id not in seen_event_ids:
                try:
                    logger.info(f"Removing deleted event: {existing_event.get('summary', 'Unknown')} ({existing_event.get('start', {}).get('dateTime', 'Unknown')})")
                    service.events().delete(
                        calendarId=calendar_id,
                        eventId=existing_event['id']
                    ).execute()
                    events_deleted += 1
                except Exception as e:
                    logger.error(f"Failed to delete event '{existing_event.get('summary', 'Unknown')}': {e}")
                    continue
        
        logger.info(f"Sync completed: {events_added} added, {events_updated} updated, {events_deleted} deleted, {events_skipped} unchanged")
        
    except Exception as e:
        logger.error(f"Error during Google Calendar sync: {e}", exc_info=True)
        raise

def get_periods(student_id: str, token: str) -> Dict:
    """Fetch school periods from ClasseViva API with retry logic."""
    url = f"https://web.spaggiari.eu/rest/v1/students/{student_id}/periods"
    headers = {
        "Content-Type": "application/json",
        "Z-Dev-ApiKey": "Tg1NWEwNGIgIC0K",
        "User-Agent": "CVVS/std/4.1.7 Android/10",
        "Z-Auth-Token": token
    }
    
    logger.info(f"Fetching periods for student {student_id}")
    
    try:
        response = http_session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        periods = response.json()
        period_count = len(periods.get('periods', []))
        logger.info(f"Successfully fetched {period_count} periods")
        logger.debug(f"Periods: {json.dumps(periods, indent=2)}")
        return periods
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while fetching periods after 30 seconds")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch periods: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from periods API: {e}")
        raise

def health_check() -> bool:
    """Perform a health check - verify we can reach ClasseViva API."""
    try:
        response = http_session.get("https://web.spaggiari.eu", timeout=10)
        is_healthy = response.status_code == 200
        if is_healthy:
            logger.debug("Health check passed")
        else:
            logger.warning(f"Health check returned status {response.status_code}")
        return is_healthy
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False

def should_sync(state: Dict, agenda_hash: str) -> tuple[bool, str]:
    """Determine if sync is needed based on changes or time elapsed.
    
    Returns:
        tuple: (should_sync, reason)
    """
    current_time = time.time()
    last_force_sync = state.get("last_force_sync", 0)
    last_hash = state.get("agenda_hash")
    
    # Check if agenda has changed
    if last_hash != agenda_hash:
        return (True, f"Agenda changed (old hash: {last_hash[:8] if last_hash else 'none'}, new hash: {agenda_hash[:8]})")
    
    # Check if force sync interval has passed
    time_since_force_sync = current_time - last_force_sync
    if time_since_force_sync >= FORCE_SYNC_INTERVAL:
        return (True, f"Force sync interval reached ({int(time_since_force_sync/60)} minutes since last force sync)")
    
    # No sync needed
    minutes_until_force = int((FORCE_SYNC_INTERVAL - time_since_force_sync) / 60)
    return (False, f"No changes detected, next force sync in {minutes_until_force} minutes")

def perform_sync(config: Dict) -> bool:
    """Perform the actual sync operation.
    
    Returns:
        bool: True if sync was successful, False otherwise
    """
    try:
        # Extract configuration
        user_id = config.get("user_id")
        user_pass = config.get("user_pass")
        calendar_id = config.get("calendar_id")
        credentials_file = config.get("credentials_file")
        
        # Adjust credentials file path for Docker
        if os.path.isdir("/app") and not credentials_file.startswith("/app/"):
            credentials_file = f"/app/{credentials_file}"
        
        student_id = "".join(filter(str.isdigit, user_id))
        logger.info(f"Student ID extracted: {student_id}")

        # Login to ClasseViva
        login_response = login(user_id, user_pass)
        token = login_response.get("token")
        
        if not token:
            logger.error("Invalid token received from login")
            return False
        
        first_name = login_response.get("firstName", "")
        last_name = login_response.get("lastName", "")
        logger.info(f"Logged in as {first_name} {last_name}")
        
        # Get periods
        periods = get_periods(student_id, token)
        
        if not periods.get("periods"):
            logger.error("No periods found")
            return False
        
        period_start = periods["periods"][0]["dateStart"].replace("-", "")
        period_end = periods["periods"][-1]["dateEnd"].replace("-", "")
        logger.info(f"Syncing period: {period_start} to {period_end}")
        
        # Get agenda
        agenda = get_agenda(student_id, period_start, period_end, token)
        
        # Compute hash and check if sync is needed
        agenda_hash = compute_agenda_hash(agenda)
        state = load_state()
        
        should_do_sync, reason = should_sync(state, agenda_hash)
        logger.info(f"Sync decision: {reason}")
        
        if not should_do_sync:
            logger.info("Skipping sync - no changes detected and force interval not reached")
            return True  # Not an error, just no sync needed
        
        # Perform sync
        logger.info("Starting calendar sync...")
        sync_to_google_calendar(agenda, calendar_id, credentials_file)
        
        # Update state
        current_time = time.time()
        state["last_sync_time"] = current_time
        state["agenda_hash"] = agenda_hash
        state["last_force_sync"] = current_time
        save_state(state)
        
        logger.info("Sync completed successfully")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during sync: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Unexpected error during sync: {e}", exc_info=True)
        return False

def main():
    """Main execution function."""
    logger.info("=== CVVCalendarSync Starting ===")
    logger.info(f"Current time: {datetime.datetime.now().isoformat()}")
    
    # Perform health check
    if not health_check():
        logger.error("Health check failed - cannot reach ClasseViva API")
        sys.exit(1)
    
    # Load configuration
    config_file = "/app/config.json" if os.path.isdir("/app") else "config.json"
    
    try:
        with open(config_file) as f:
            config = json.load(f)
        logger.info(f"Configuration loaded from {config_file}")
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {e}")
        sys.exit(1)
    
    # Validate configuration
    required_fields = ["user_id", "user_pass", "calendar_id", "credentials_file"]
    missing_fields = [f for f in required_fields if not config.get(f)]
    if missing_fields:
        logger.error(f"Missing required configuration fields: {', '.join(missing_fields)}")
        sys.exit(1)
    
    credentials_file = config.get("credentials_file")
    if os.path.isdir("/app") and not credentials_file.startswith("/app/"):
        credentials_file = f"/app/{credentials_file}"
    
    # Verify credentials file exists
    if not os.path.isfile(credentials_file):
        logger.error(f"Credentials file not found: {credentials_file}")
        sys.exit(1)
    
    # Perform sync
    success = perform_sync(config)
    
    if success:
        logger.info("=== CVVCalendarSync Completed ===")
        sys.exit(0)
    else:
        logger.error("=== CVVCalendarSync Failed ===")
        sys.exit(1)


if __name__ == "__main__":
    main()