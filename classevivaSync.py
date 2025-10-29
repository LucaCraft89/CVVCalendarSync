import datetime
import os
import requests
import json
import logging
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Event ID prefix to identify events created by this sync
EVENT_ID_PREFIX = "cvv_sync_"

def get_agenda(student_id: str, begin: str, end: str, token: str) -> Dict:
    """Fetch agenda from ClasseViva API."""
    url = f"https://web.spaggiari.eu/rest/v1/students/{student_id}/agenda/all/{begin}/{end}"
    headers = {
        "Content-Type": "application/json",
        "Z-Dev-ApiKey": "Tg1NWEwNGIgIC0K",
        "User-Agent": "CVVS/std/4.1.7 Android/10",
        "Z-Auth-Token": token
    }
    
    logger.info(f"Fetching agenda for student {student_id} from {begin} to {end}")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        logger.info(f"Successfully fetched {len(data.get('agenda', []))} agenda items")
        return data
    else:
        logger.error(f"Failed to fetch agenda: {response.status_code} - {response.text}")
        response.raise_for_status()

def login(user_id: str, user_pass: str) -> Dict:
    """Login to ClasseViva and get authentication token."""
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
    response = requests.post(url, headers=headers, data=json.dumps(body))
    
    if response.status_code == 200:
        logger.info("Login successful")
        return response.json()
    else:
        logger.error(f"Login failed: {response.status_code} - {response.text}")
        response.raise_for_status()

def generate_event_id(cvv_event: Dict) -> str:
    """Generate a unique event ID based on ClasseViva event data."""
    # Use evtId if available, otherwise create from event data
    if 'evtId' in cvv_event and cvv_event['evtId']:
        return f"{EVENT_ID_PREFIX}{cvv_event['evtId']}"
    
    # Fallback: create ID from event details
    event_str = f"{cvv_event.get('evtCode', '')}{cvv_event.get('evtDatetimeBegin', '')}{cvv_event.get('notes', '')}"
    return f"{EVENT_ID_PREFIX}{hash(event_str) & 0xFFFFFFFF}"
def generate_event_id(cvv_event: Dict) -> str:
    """Generate a unique event ID based on ClasseViva event data."""
    # Use evtId if available, otherwise create from event data
    if 'evtId' in cvv_event and cvv_event['evtId']:
        return f"{EVENT_ID_PREFIX}{cvv_event['evtId']}"
    
    # Fallback: create ID from event details
    event_str = f"{cvv_event.get('evtCode', '')}{cvv_event.get('evtDatetimeBegin', '')}{cvv_event.get('notes', '')}"
    return f"{EVENT_ID_PREFIX}{hash(event_str) & 0xFFFFFFFF}"

def sync_to_google_calendar(agenda: Dict, calendar_id: str, credentials_file: str) -> None:
    """Sync ClasseViva agenda to Google Calendar."""
    try: 
        logger.info("Authenticating with Google Calendar")
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, 
            scopes=["https://www.googleapis.com/auth/calendar"]
        )
        service = build("calendar", "v3", credentials=credentials)
        
        # Get existing events created by this sync (filter by extended property)
        logger.info("Fetching existing synced events from Google Calendar")
        existing_events = []
        page_token = None
        
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
                    logger.info(f"Updating event: {event_body['summary']} ({cvv_event['evtDatetimeBegin']})")
                    service.events().update(
                        calendarId=calendar_id,
                        eventId=existing_event['id'],
                        body=event_body
                    ).execute()
                    events_updated += 1
                else:
                    logger.debug(f"Event unchanged: {event_body['summary']} ({cvv_event['evtDatetimeBegin']})")
                    events_skipped += 1
            else:
                # Create new event
                logger.info(f"Adding new event: {event_body['summary']} ({cvv_event['evtDatetimeBegin']})")
                service.events().insert(calendarId=calendar_id, body=event_body).execute()
                events_added += 1
        
        # Remove events that are no longer in ClasseViva
        events_deleted = 0
        for event_id, existing_event in existing_events_map.items():
            if event_id not in seen_event_ids:
                logger.info(f"Removing deleted event: {existing_event.get('summary', 'Unknown')} ({existing_event.get('start', {}).get('dateTime', 'Unknown')})")
                service.events().delete(
                    calendarId=calendar_id,
                    eventId=existing_event['id']
                ).execute()
                events_deleted += 1
        
        logger.info(f"Sync completed: {events_added} added, {events_updated} updated, {events_deleted} deleted, {events_skipped} unchanged")
        
    except Exception as e:
        logger.error(f"Error during Google Calendar sync: {e}", exc_info=True)
        raise
def get_periods(student_id: str, token: str) -> Dict:
    """Fetch school periods from ClasseViva API."""
    url = f"https://web.spaggiari.eu/rest/v1/students/{student_id}/periods"
    headers = {
        "Content-Type": "application/json",
        "Z-Dev-ApiKey": "Tg1NWEwNGIgIC0K",
        "User-Agent": "CVVS/std/4.1.7 Android/10",
        "Z-Auth-Token": token
    }
    
    logger.info(f"Fetching periods for student {student_id}")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        periods = response.json()
        logger.info(f"Successfully fetched {len(periods.get('periods', []))} periods")
        logger.debug(json.dumps(periods, indent=4))
        return periods
    else:
        logger.error(f"Failed to fetch periods: {response.status_code} - {response.text}")
        response.raise_for_status()

def health_check() -> bool:
    """Perform a health check - verify we can reach ClasseViva API."""
    try:
        response = requests.get("https://web.spaggiari.eu", timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False
def health_check() -> bool:
    """Perform a health check - verify we can reach ClasseViva API."""
    try:
        response = requests.get("https://web.spaggiari.eu", timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False

def main():
    """Main execution function."""
    logger.info("=== CVVCalendarSync Starting ===")
    
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
    
    # Extract configuration
    user_id = config.get("user_id")
    user_pass = config.get("user_pass")
    calendar_id = config.get("calendar_id")
    credentials_file = config.get("credentials_file")
    
    # Validate configuration
    if not all([user_id, user_pass, calendar_id, credentials_file]):
        logger.error("Missing required configuration fields")
        sys.exit(1)
    
    # Adjust credentials file path for Docker
    if os.path.isdir("/app"):
        credentials_file = f"/app/{credentials_file}"
    
    # Verify credentials file exists
    if not os.path.isfile(credentials_file):
        logger.error(f"Credentials file not found: {credentials_file}")
        sys.exit(1)
    
    student_id = "".join(filter(str.isdigit, user_id))
    logger.info(f"Student ID extracted: {student_id}")

    try:
        # Login to ClasseViva
        login_response = login(user_id, user_pass)
        token = login_response.get("token")
        
        if not token:
            logger.error("Invalid token received from login")
            sys.exit(1)
        
        first_name = login_response.get("firstName", "")
        last_name = login_response.get("lastName", "")
        logger.info(f"Logged in successfully as {first_name} {last_name}")
        
        # Get periods
        periods = get_periods(student_id, token)
        
        if not periods.get("periods"):
            logger.error("No periods found")
            sys.exit(1)
        
        period_start = periods["periods"][0]["dateStart"].replace("-", "")
        period_end = periods["periods"][-1]["dateEnd"].replace("-", "")
        logger.info(f"Syncing period: {period_start} to {period_end}")
        
        # Get agenda
        agenda = get_agenda(student_id, period_start, period_end, token)
        
        # Sync to Google Calendar
        sync_to_google_calendar(agenda, calendar_id, credentials_file)
        
        logger.info("=== CVVCalendarSync Completed Successfully ===")
        sys.exit(0)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error occurred: {e}", exc_info=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()