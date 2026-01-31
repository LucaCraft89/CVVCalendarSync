# CVVCalendarSync v3.0 Improvements

## ⚠️ Upgrading from v2.0?

**See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** for complete migration instructions.

**Quick start:** The new version is compatible with old events. For best results, clear old synced events first:

```bash
docker-compose run --rm classeviva_sync python3 /app/clear_calendar.py --only-synced
docker-compose up -d --build
```

---

## Changes Made

### 1. Smart Change Detection

- **Hash-based change detection**: The script now computes a SHA-256 hash of the agenda data
- **State tracking**: Maintains a `sync_state.json` file to track previous sync state
- **Efficient syncing**: Only syncs when changes are detected OR when force sync interval is reached

### 2. Improved Sync Schedule

- **Check interval**: Runs every 5 minutes to check for changes
- **Force sync interval**: Forces a full sync every 1 hour regardless of changes
- **Smart logic**: Skips unnecessary syncs when no changes detected and force interval not reached

### 3. Enhanced Stability

- **Retry logic**: Automatic retries with exponential backoff (2, 4, 8 seconds)
- **Connection pooling**: Reuses HTTP connections for better performance
- **Timeout handling**: All API calls have 30-second timeouts
- **Individual error handling**: Failed event updates/deletes don't stop the entire sync

### 4. Better Logging

- **Detailed format**: Includes function name and line number in logs
- **More context**: Logs sync decisions, hash changes, and timing information
- **Error details**: Full stack traces for debugging
- **Progress tracking**: Shows counts of added/updated/deleted/skipped events

## How It Works

### Smart Sync Logic

1. Script runs every 5 minutes (via cron)
2. Fetches current agenda from ClasseViva
3. Computes hash of agenda data
4. Compares with previous hash from state file
5. **If changed**: Performs full sync
6. **If unchanged but 1 hour passed**: Performs force sync
7. **If unchanged and < 1 hour**: Skips sync, logs next sync time

### State File

Location: `/app/sync_state.json` (in container) or `sync_state.json` (local)

Structure:

```json
{
  "last_sync_time": 1706745600,
  "agenda_hash": "abc123...",
  "last_force_sync": 1706745600
}
```

## Benefits

1. **Faster updates**: Changes are detected within 5 minutes instead of 1 hour
2. **Reduced load**: Skips unnecessary syncs when nothing changed
3. **More reliable**: Retry logic handles temporary network issues
4. **Better visibility**: Detailed logs show exactly what's happening
5. **Guaranteed consistency**: Force sync every hour ensures calendars stay in sync

## Deployment

### Docker (Recommended)

```bash
# Rebuild the container
docker-compose down
docker-compose up -d --build

# View logs
docker-compose logs -f
```

## Monitoring

### Check Sync Status

```bash
# View recent logs
docker-compose logs --tail=50 -f

# Check state file
docker exec cvvcalendarsync-1 cat /app/sync_state.json
```

### What to Look For

- `Sync decision: Agenda changed` - Changes detected, syncing
- `Sync decision: Force sync interval reached` - Hourly force sync
- `Skipping sync - no changes detected` - No sync needed
- `Sync completed: X added, Y updated, Z deleted` - Sync summary

## Compatibility with v2.0

The new version (v3.0) is **fully compatible** with events created by v2.0 because:

- Both versions use the same `EVENT_ID_PREFIX = "cvv_sync_"`
- Both versions use the same extended properties format
- The new version can read, update, and delete v2.0 events

### Automatic Migration

When you first run v3.0, it will:

1. Detect existing events via extended properties
2. Compare them with current ClasseViva data
3. Update changed events
4. Add new events
5. Remove deleted events

### Clean Migration (Recommended)

For a fresh start without potential edge cases:

```bash
# Clear only synced events (safe)
docker-compose run --rm classeviva_sync python3 /app/clear_calendar.py --only-synced

# Let v3.0 recreate everything
docker-compose up -d
```

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed migration instructions.
