# Migration Guide to v3.0

## Understanding the Situation

Your calendar currently has events created by the previous version (v2.0). The good news: **v3.0 is fully compatible with v2.0 events** because they both use the same event tracking system (`cvv_sync_` extended properties).

## Recommended Migration Path

You have **two options** for migrating:

### Option 1: Clean Migration (Recommended) ✅

**Best for:** Fresh start, guaranteed no duplicates

**Steps:**

```bash
# 1. Stop the current container
docker-compose down

# 2. Clear only the synced events (safe - won't delete your personal events)
docker-compose run --rm classeviva_sync python3 /app/clear_calendar.py --only-synced

# 3. Build and start v3.0
docker-compose up -d --build

# 4. Watch the initial sync
docker-compose logs -f
```

**What happens:**

- Removes all events created by CVVCalendarSync (v2.0)
- v3.0 will recreate all events from ClasseViva
- Takes about 30-60 seconds for initial sync
- Clean slate, no compatibility issues

### Option 2: In-Place Upgrade (Automatic) 🔄

**Best for:** Minimal downtime, trust automatic migration

**Steps:**

```bash
# 1. Simply rebuild and restart
docker-compose down
docker-compose up -d --build

# 2. Watch the logs
docker-compose logs -f
```

**What happens:**

- v3.0 will detect existing events via extended properties
- It will compare them with current ClasseViva data
- Update any changed events
- Add new events
- Remove deleted events
- First sync might take longer as it processes all existing events

## Verification

After migration, verify everything is working:

```bash
# Check the first sync completed
docker-compose logs | grep "Sync completed"

# Should show something like:
# Sync completed: 0 added, 5 updated, 0 deleted, 20 unchanged

# Check state file was created
docker exec cvvcalendarsync-1 cat /app/sync_state.json

# Should show:
# {
#   "last_sync_time": 1738324800,
#   "agenda_hash": "abc123...",
#   "last_force_sync": 1738324800
# }
```

## Troubleshooting

### If you see duplicate events after migration

This shouldn't happen, but if it does:

```bash
# Clear all synced events
docker-compose exec classeviva_sync python3 /app/clear_calendar.py --only-synced

# Restart to trigger fresh sync
docker-compose restart

# Delete state file to force full sync
docker exec cvvcalendarsync-1 rm /app/sync_state.json
docker-compose restart
```

### If events are missing after migration

```bash
# Check ClasseViva connection
docker-compose exec classeviva_sync python3 /app/debug_api.py

# Force a manual sync
docker-compose exec classeviva_sync python3 /app/classevivaSync.py

# Check for errors
docker-compose logs --tail=100
```

### If sync keeps running even when no changes

```bash
# Check the state file
docker exec cvvcalendarsync-1 cat /app/sync_state.json

# If hash keeps changing, check logs for why
docker-compose logs | grep "Sync decision"

# This might indicate API changes or data inconsistency
```

## Expected Behavior After Migration

Once migrated, you should see:

**Every 5 minutes (no changes):**

```
=== CVVCalendarSync Starting ===
Sync decision: No changes detected, next force sync in 54 minutes
Skipping sync - no changes detected and force interval not reached
=== CVVCalendarSync Completed ===
```

**When changes occur:**

```
=== CVVCalendarSync Starting ===
Sync decision: Agenda changed (old hash: abc12345, new hash: def67890)
Starting calendar sync...
Sync completed: 1 added, 0 updated, 0 deleted, 24 unchanged
=== CVVCalendarSync Completed ===
```

**Every hour (force sync):**

```
=== CVVCalendarSync Starting ===
Sync decision: Force sync interval reached (62 minutes since last force sync)
Starting calendar sync...
Sync completed: 0 added, 0 updated, 0 deleted, 25 unchanged
=== CVVCalendarSync Completed ===
```

## My Recommendation

**Go with Option 1 (Clean Migration)** because:

- Guaranteed fresh start
- Only takes 1 minute extra
- Eliminates any potential edge cases
- Easy to verify it worked correctly

The command is simple:

```bash
docker-compose down
docker-compose run --rm classeviva_sync python3 /app/clear_calendar.py --only-synced
docker-compose up -d --build
```

## Rollback Plan

If something goes wrong and you need to rollback:

```bash
# Stop v3.0
docker-compose down

# Checkout previous version
git checkout HEAD~1 classevivaSync.py cronjob Dockerfile

# Rebuild and start
docker-compose up -d --build
```

Your events will still be in the calendar, and v2.0 will manage them again.

## Questions?

- Check logs: `docker-compose logs -f`
- Test sync manually: `docker-compose exec classeviva_sync python3 /app/classevivaSync.py`
- Clear and restart: `docker-compose run --rm classeviva_sync python3 /app/clear_calendar.py --only-synced`
