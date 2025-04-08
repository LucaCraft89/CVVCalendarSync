import datetime
import os
import requests
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_agenda(student_id, begin, end, token):
    url = f"https://web.spaggiari.eu/rest/v1/students/{student_id}/agenda/all/{begin}/{end}"
    headers = {
        "Content-Type": "application/json",
        "Z-Dev-ApiKey": "Tg1NWEwNGIgIC0K",
        "User-Agent": "CVVS/std/4.1.7 Android/10",
        "Z-Auth-Token": token
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

def login(user_id, user_pass):
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
    
    response = requests.post(url, headers=headers, data=json.dumps(body))
    
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

def sync_to_google_calendar(agenda, calendar_id, credentials_file):
    try: 
        credentials = service_account.Credentials.from_service_account_file(credentials_file, scopes=["https://www.googleapis.com/auth/calendar"])
        service = build("calendar", "v3", credentials=credentials)
        
        # Get existing events from the calendar with pagination support
        existing_events = []
        page_token = None
        while True:
            events = service.events().list(calendarId=calendar_id, pageToken=page_token).execute()
            existing_events.extend(events.get('items', []))
            page_token = events.get('nextPageToken')
            if not page_token:
                break
        
        for event in agenda["agenda"]:
            if not event["evtDatetimeBegin"] or not event["evtDatetimeEnd"] or event["evtDatetimeBegin"] >= event["evtDatetimeEnd"]:
                continue

            # Remove all existing events with the same title and same date
            for existing_event in existing_events:
                if existing_event['summary'] == event["notes"]:
                    existing_event_start = existing_event['start'].get('dateTime', existing_event['start'].get('date'))
                    existing_event_end = existing_event['end'].get('dateTime', existing_event['end'].get('date'))
                    
                    # Compare just the date part (YYYY-MM-DD)
                    if existing_event_start[:10] == event["evtDatetimeBegin"][:10]:  
                        print(f"Rimuovo vecchio evento: {existing_event['summary']} - {existing_event_start} to {existing_event_end}")
                        service.events().delete(calendarId=calendar_id, eventId=existing_event['id']).execute()

            # Add new event
            print(f"Aggiungo evento: {event['notes']} - {event['evtDatetimeBegin']} to {event['evtDatetimeEnd']}")
            event_body = {
                "summary": event["notes"],
                "location": "",
                "description": f"Prof: {event['authorName']}\nDescrizione: {event['notes']}",
                "start": {
                    "dateTime": event["evtDatetimeBegin"],
                    "timeZone": "Europe/Rome",
                },
                "end": {
                    "dateTime": event["evtDatetimeEnd"],
                    "timeZone": "Europe/Rome",
                },
            }
            service.events().insert(calendarId=calendar_id, body=event_body).execute()

        # Check for events that have been removed from ClasseViva
        for existing_event in existing_events:
            event_in_agenda = any(
                existing_event['summary'] == event["notes"] and
                existing_event['start'].get('dateTime', existing_event['start'].get('date')) == event["evtDatetimeBegin"] and
                existing_event['end'].get('dateTime', existing_event['end'].get('date')) == event["evtDatetimeEnd"]
                for event in agenda["agenda"]
            )
            
            if not event_in_agenda:
                print(f"Rimuovo evento eliminato da ClasseViva: {existing_event['summary']} - {existing_event['start'].get('dateTime', existing_event['start'].get('date'))} to {existing_event['end'].get('dateTime', existing_event['end'].get('date'))}")
                service.events().delete(calendarId=calendar_id, eventId=existing_event['id']).execute()
    except Exception as e:
        print(f"Si è verificato un errore nel sincronizzare gli eventi con Google Calendar: {e}")

def get_periods(student_id, token):
    url = f"https://web.spaggiari.eu/rest/v1/students/{student_id}/periods"
    headers = {
        "Content-Type": "application/json",
        "Z-Dev-ApiKey": "Tg1NWEwNGIgIC0K",
        "User-Agent": "CVVS/std/4.1.7 Android/10",
        "Z-Auth-Token": token
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=4))
        return response.json()
    else:
        response.raise_for_status()

if __name__ == "__main__":
    # check if /app directory exists
    if os.path.isdir("/app"):
        config_file="/app/config.json"
    else:
        config_file="config.json"
    with open(config_file) as f:
        config = json.load(f)
    user_id = config["user_id"]
    user_pass = config["user_pass"]
    calendar_id = config["calendar_id"]
    credentials_file = config["credentials_file"]
    if os.path.isdir("/app"):
        credentials_file="/app/"+credentials_file
    else:
        credentials_file = config["credentials_file"]

    student_id = "".join(filter(str.isdigit, user_id))

    try:
        login_response = login(user_id, user_pass)
        token = login_response["token"]
        if token is None or token == "":
            raise ValueError("Token invalido!")
        # print(json.dumps(login_response, indent=4))
        # print(f"Token: {token}")
        print("Effettuato il login con il profilo " + login_response["firstName"] + " " + login_response["lastName"])
        periods = get_periods(student_id, token)
        periodStart = periods["periods"][0]["dateStart"]
        periodEnd = periods["periods"][-1]["dateEnd"]
        periodStart = periodStart.replace("-", "")
        periodEnd = periodEnd.replace("-", "")
        agenda = get_agenda(student_id, periodStart, periodEnd, token)

        # print(json.dumps(agenda, indent=4))

        sync_to_google_calendar(agenda, calendar_id, credentials_file)
    except requests.exceptions.RequestException as e:
        print(f"Si è verificato un errore: {e}")
    except Exception as e:
        print(f"Si è verificato un errore: {e}")
