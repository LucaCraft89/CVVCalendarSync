<p align="center">
  <img src="https://github.com/LucaCraft89/CVVCalendarSync/blob/main/banner.png?raw=truet"/>
</p>
# CVVCalendarSync
A Python script with Docker container to sync Classeviva's Agenda with Google Calendar. Features smart change detection and efficient syncing.

## Features

- **Smart Change Detection**: Checks for changes every 5 minutes using hash-based comparison
- **Efficient Syncing**: Only syncs when changes are detected or every hour (force sync)
- **Robust Error Handling**: Automatic retries with exponential backoff
- **Detailed Logging**: Comprehensive logs with sync decisions and event tracking
- **Dockerized**: Easy deployment with Docker Compose

## How It Works

1. **Every 5 minutes**: Script checks if the agenda has changed
2. **If changed**: Immediately syncs to Google Calendar
3. **If unchanged**: Waits for next check
4. **Every hour**: Force sync regardless of changes (ensures consistency)

This means your calendar updates within 5 minutes of any change while avoiding unnecessary API calls.

## Upgrading from v2.0

If you're upgrading from a previous version, **see [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** for migration instructions.

**Quick migration:**

```bash
# Option 1: Clean migration (recommended)
docker-compose down
docker-compose run --rm classeviva_sync python3 /app/clear_calendar.py --only-synced
docker-compose up -d --build

# Option 2: Automatic in-place upgrade
docker-compose down && docker-compose up -d --build
```

# Installation and Usage

[See wiki](https://github.com/LucaCraft89/CVVCalendarSync/wiki/Installation)

## Common Commands

### View Logs

```bash
# Real-time logs
docker compose logs -f classeviva_sync

# Last 100 lines
docker compose logs --tail 100 classeviva_sync
```

### Force a Sync

```bash
docker compose exec classeviva_sync python3 /app/classevivaSync.py
```

### Clean Up Calendar (Remove Duplicates)

```bash
# Preview what would be deleted
docker compose exec classeviva_sync python3 /app/clear_calendar.py --dry-run

# Delete all events and start fresh (recommended for cleanup)
docker compose exec classeviva_sync python3 /app/clear_calendar.py

# Delete only events created by this sync
docker compose exec classeviva_sync python3 /app/clear_calendar.py --only-synced
```

See [CLEANUP_GUIDE.md](CLEANUP_GUIDE.md) for detailed cleanup instructions.

### Debug API

```bash
docker compose exec classeviva_sync python3 /app/debug_api.py
```

### Check Health

```bash
docker compose ps
```

## References

- [Classeviva-Official-Endpoints](https://github.com/Lioydiano/Classeviva-Official-Endpoints)
