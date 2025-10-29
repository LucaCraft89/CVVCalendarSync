#!/usr/bin/env python3
"""
Clear all events from Google Calendar.
WARNING: This will DELETE ALL events from the specified calendar!
Use with caution.

Usage: python3 clear_calendar.py [--dry-run] [--only-synced]
  --dry-run: Show what would be deleted without actually deleting
  --only-synced: Only delete events created by CVVCalendarSync (safer)
"""

import json
import os
import sys
import argparse
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

EVENT_ID_PREFIX = "cvv_sync_"


def clear_calendar(calendar_id: str, credentials_file: str, dry_run: bool = False, only_synced: bool = False):
    """
    Clear all events from the specified Google Calendar.
    
    Args:
        calendar_id: Google Calendar ID
        credentials_file: Path to Google service account credentials
        dry_run: If True, only show what would be deleted
        only_synced: If True, only delete events created by CVVCalendarSync
    """
    try:
        logger.info("Authenticating with Google Calendar...")
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=["https://www.googleapis.com/auth/calendar"]
        )
        service = build("calendar", "v3", credentials=credentials)
        
        # Fetch events
        logger.info(f"Fetching events from calendar{' (only synced events)' if only_synced else ''}...")
        all_events = []
        page_token = None
        
        while True:
            if only_synced:
                # Only fetch events created by CVVCalendarSync
                events_result = service.events().list(
                    calendarId=calendar_id,
                    privateExtendedProperty=f"{EVENT_ID_PREFIX}source=classeviva",
                    maxResults=250,
                    pageToken=page_token
                ).execute()
            else:
                # Fetch ALL events
                events_result = service.events().list(
                    calendarId=calendar_id,
                    maxResults=250,
                    pageToken=page_token
                ).execute()
            
            all_events.extend(events_result.get('items', []))
            page_token = events_result.get('nextPageToken')
            if not page_token:
                break
        
        total_events = len(all_events)
        logger.info(f"Found {total_events} events to process")
        
        if total_events == 0:
            logger.info("No events to delete. Calendar is already empty.")
            return
        
        # Show summary
        logger.info("\n" + "=" * 60)
        logger.info("EVENTS TO BE DELETED:")
        logger.info("=" * 60)
        
        for i, event in enumerate(all_events[:10], 1):  # Show first 10
            summary = event.get('summary', 'No title')
            start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date', 'Unknown'))
            logger.info(f"{i}. {summary} - {start}")
        
        if total_events > 10:
            logger.info(f"... and {total_events - 10} more events")
        
        logger.info("=" * 60)
        
        if dry_run:
            logger.warning(f"\n🔍 DRY RUN MODE: Would delete {total_events} events")
            logger.info("Run without --dry-run to actually delete these events")
            return
        
        # Confirm deletion
        logger.warning(f"\n⚠️  WARNING: About to delete {total_events} events!")
        if only_synced:
            logger.info("(Only events created by CVVCalendarSync will be deleted)")
        else:
            logger.warning("(ALL events in the calendar will be deleted)")
        
        response = input("\nType 'DELETE' to confirm: ")
        if response != "DELETE":
            logger.info("Deletion cancelled.")
            return
        
        # Delete events
        logger.info(f"\nDeleting {total_events} events...")
        deleted_count = 0
        failed_count = 0
        
        for i, event in enumerate(all_events, 1):
            try:
                summary = event.get('summary', 'No title')
                event_id = event.get('id')
                
                service.events().delete(
                    calendarId=calendar_id,
                    eventId=event_id
                ).execute()
                
                deleted_count += 1
                
                # Log progress every 10 events
                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{total_events} ({(i/total_events)*100:.1f}%)")
                
            except Exception as e:
                logger.error(f"Failed to delete event '{summary}': {e}")
                failed_count += 1
        
        logger.info("\n" + "=" * 60)
        logger.info("DELETION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"✅ Successfully deleted: {deleted_count} events")
        if failed_count > 0:
            logger.warning(f"❌ Failed to delete: {failed_count} events")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error during calendar cleanup: {e}", exc_info=True)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Clear events from Google Calendar',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what would be deleted (all events)
  python3 clear_calendar.py --dry-run
  
  # Preview only synced events
  python3 clear_calendar.py --dry-run --only-synced
  
  # Delete only events created by CVVCalendarSync (safer)
  python3 clear_calendar.py --only-synced
  
  # Delete ALL events (dangerous!)
  python3 clear_calendar.py
        """
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    parser.add_argument(
        '--only-synced',
        action='store_true',
        help='Only delete events created by CVVCalendarSync (safer option)'
    )
    
    args = parser.parse_args()
    
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
    
    calendar_id = config.get("calendar_id")
    credentials_file = config.get("credentials_file")
    
    if not calendar_id or not credentials_file:
        logger.error("Missing calendar_id or credentials_file in config")
        sys.exit(1)
    
    # Adjust credentials file path for Docker
    if os.path.isdir("/app"):
        credentials_file = f"/app/{credentials_file}"
    
    if not os.path.isfile(credentials_file):
        logger.error(f"Credentials file not found: {credentials_file}")
        sys.exit(1)
    
    logger.info("\n" + "=" * 60)
    logger.info("Google Calendar Cleanup Tool")
    logger.info("=" * 60)
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE DELETION'}")
    logger.info(f"Scope: {'Only CVVCalendarSync events' if args.only_synced else 'ALL events'}")
    logger.info("=" * 60 + "\n")
    
    if not args.dry_run and not args.only_synced:
        logger.warning("⚠️  WARNING: You are about to delete ALL events from the calendar!")
        logger.info("Consider using --only-synced to delete only CVVCalendarSync events")
        logger.info("Or use --dry-run first to preview what will be deleted\n")
    
    clear_calendar(calendar_id, credentials_file, args.dry_run, args.only_synced)


if __name__ == "__main__":
    main()
