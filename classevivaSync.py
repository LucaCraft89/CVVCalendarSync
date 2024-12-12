# To obtain the 

# calendar_id

#  and 

# credentials_file

#  for integrating with Google Calendar API, follow these steps:

# ### 1. Getting the 

# calendar_id



# 1. **Go to Google Calendar**: Open [Google Calendar](https://calendar.google.com/).
# 2. **Create a New Calendar** (if you don't have one): 
#    - Click on the gear icon (Settings) in the top right corner.
#    - Select "Settings".
#    - On the left sidebar, click on "Add calendar" and then "Create new calendar".
#    - Fill in the details and click "Create calendar".
# 3. **Find the Calendar ID**:
#    - In the settings, click on the name of the calendar you want to use under "Settings for my calendars".
#    - Scroll down to the "Integrate calendar" section.
#    - The `Calendar ID` will be listed there. It usually looks like `your_calendar_id@group.calendar.google.com`.

# ### 2. Getting the 

# credentials_file



# 1. **Go to Google Cloud Console**: Open [Google Cloud Console](https://console.cloud.google.com/).
# 2. **Create a New Project** (if you don't have one):
#    - Click on the project dropdown at the top and select "New Project".
#    - Fill in the project details and click "Create".
# 3. **Enable Google Calendar API**:
#    - In the left sidebar, go to "APIs & Services" > "Library".
#    - Search for "Google Calendar API" and click on it.
#    - Click "Enable".
# 4. **Create Service Account Credentials**:
#    - Go to "APIs & Services" > "Credentials".
#    - Click "Create Credentials" and select "Service account".
#    - Fill in the service account details and click "Create".
#    - In the "Service account permissions" step, you can skip it or assign roles as needed.
#    - In the "Grant users access to this service account" step, click "Done".
# 5. **Generate Key File**:
#    - After creating the service account, click on it in the "Service accounts" list.
#    - Go to the "Keys" tab.
#    - Click "Add Key" > "Create new key".
#    - Select "JSON" and click "Create".
#    - A JSON file will be downloaded. This is your 

# credentials_file

# .

# ### Using the Values in Your Code

# Replace the placeholders in your code with the actual values:

# ```python
# calendar_id = "your_actual_calendar_id@group.calendar.google.com"
# credentials_file = "path_to_your_downloaded_service_account_credentials.json"
# ```

# Make sure to keep your credentials file secure and do not share it publicly.
import datetime
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
    # Authenticate and construct service
    try: 
        credentials = service_account.Credentials.from_service_account_file(credentials_file, scopes=["https://www.googleapis.com/auth/calendar"])
        service = build("calendar", "v3", credentials=credentials)
        
        # Get existing events from the calendar
        existing_events = service.events().list(calendarId=calendar_id).execute().get('items', [])
        
        for event in agenda["agenda"]:
            if not event["evtDatetimeBegin"] or not event["evtDatetimeEnd"] or event["evtDatetimeBegin"] >= event["evtDatetimeEnd"]:
                continue
            
            # Check if the event is already present
            event_exists = any(
                existing_event['summary'] == event["notes"] and
                existing_event['start']['dateTime'] == event["evtDatetimeBegin"] and
                existing_event['end']['dateTime'] == event["evtDatetimeEnd"]
                for existing_event in existing_events
            )
            
            if event_exists:
                print(f"Event already exists: {event['notes']} - {event['evtDatetimeBegin']} to {event['evtDatetimeEnd']}")
                continue
            
            print(f"Adding event: {event['notes']} - {event['evtDatetimeBegin']} to {event['evtDatetimeEnd']}")
            event_body = {
                "summary": event["notes"],
                "location": "",
                "description": f"Author: {event['authorName']}\nClass: {event['classDesc']}\nSubject: {event['notes']}",
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
                print(f"Removing event: {existing_event['summary']} - {existing_event['start'].get('dateTime', existing_event['start'].get('date'))} to {existing_event['end'].get('dateTime', existing_event['end'].get('date'))}")
                service.events().delete(calendarId=calendar_id, eventId=existing_event['id']).execute()
    except Exception as e:
        print(f"An error occurred while syncing to Google Calendar: {e}")
        
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
        return response.json()
    else:
        response.raise_for_status()


# Example usage
# Example usage
if __name__ == "__main__":
    config_file=".\\config.json"
    with open(config_file) as f:
        config = json.load(f)
    user_id = config["user_id"]
    user_pass = config["user_pass"]
    calendar_id = config["calendar_id"]
    credentials_file = config["credentials_file"]
    
    stuent_id = "".join(filter(str.isdigit, user_id))

    try:
        login_response = login(user_id, user_pass)
        token = login_response["token"]
        if token is None or token == "":
            raise ValueError("Invalid token")
        # print(json.dumps(login_response, indent=4))
        # print(f"Token: {token}")
        print("Logged in successfully " + login_response["firstName"] + " " + login_response["lastName"])
        periods = get_periods(stuent_id, token)
        for period in periods["periods"]:
            if period["dateEnd"] :
                current_date = datetime.datetime.now().strftime("%Y-%m-%d")
                if period["dateStart"] <= current_date <= period["dateEnd"]:
                    periodStart = period["dateStart"]
                    periodEnd = period["dateEnd"]
                break
        periodStart = periodStart.replace("-", "")
        periodEnd = periodEnd.replace("-", "")
        agenda = get_agenda(stuent_id, periodStart, periodEnd, token)

        # print(json.dumps(agenda, indent=4))

        sync_to_google_calendar(agenda, calendar_id, credentials_file)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")