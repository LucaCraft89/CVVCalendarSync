<p align="center">
  <img src="https://github.com/LucaCraft89/CVVCalendarSync/blob/main/banner.png?raw=truet"/>
</p>
# CVVCalendarSync
A Python script with docker container to sync Classeviva's Agenda with Google Calendar, Dockerized with cron to run every hour not to exced API rate limits

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
