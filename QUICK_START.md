# Quick Decision Guide: Migrating to v3.0

## The Question

**What to do with old events in the calendar?**

## The Answer: Option 1 (Clean Migration) ✅

### Why Clean Migration?

- ✅ **100% guaranteed no duplicates**
- ✅ **Fresh start with v3.0**
- ✅ **Takes only 30-60 seconds extra**
- ✅ **Easy to verify everything works**
- ✅ **Recommended by the developer**

### How to Do It

```bash
# Step 1: Stop current container
docker-compose down

# Step 2: Clear ONLY synced events (your personal events are safe!)
docker-compose run --rm classeviva_sync python3 /app/clear_calendar.py --only-synced

# Step 3: Start v3.0
docker-compose up -d --build

# Step 4: Watch it work
docker-compose logs -f
```

**What happens:**

1. Removes ~25-50 old ClasseViva events (takes 10 seconds)
2. Container starts with v3.0
3. Initial sync recreates all events from ClasseViva (takes 20-40 seconds)
4. Done! From now on, it checks every 5 minutes for changes

### First Sync You'll See

```
=== CVVCalendarSync Starting ===
Current time: 2026-01-31T10:45:00
Health check passed
Fetching agenda for student 12345...
Successfully fetched 25 agenda items
Sync decision: Agenda changed (old hash: none, new hash: abc12345)
Starting calendar sync...
Adding new event: Matematica (2026-02-01T08:00:00)
Adding new event: Italiano (2026-02-01T09:00:00)
...
Sync completed: 25 added, 0 updated, 0 deleted, 0 unchanged
=== CVVCalendarSync Completed ===
```

---

## Alternative: Option 2 (Automatic Upgrade)

### If You Want Zero Downtime

```bash
docker-compose down && docker-compose up -d --build
```

**What happens:**

- v3.0 automatically detects old events
- Compares with ClasseViva
- Updates/adds/removes as needed
- Might take longer on first sync
- Small risk of edge cases with event matching

---

## Verification Checklist

After migration, verify:

```bash
# ✓ Check first sync completed
docker-compose logs | grep "Sync completed"

# ✓ Check state file exists
docker exec cvvcalendarsync-1 cat /app/sync_state.json

# ✓ Check calendar has events
# (Open Google Calendar and look for events)

# ✓ Wait 5 minutes, check it runs again
docker-compose logs --tail=20
```

---

## My Recommendation

**Go with Clean Migration (Option 1)**

It's safer, cleaner, and only takes 1 minute. The command is simple and you can watch it happen in real-time.

---

## Need Help?

Check these files:

- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Detailed migration instructions
- **[IMPROVEMENTS.md](IMPROVEMENTS.md)** - What changed in v3.0
- **[README.md](README.md)** - General usage

Run these commands:

```bash
# Preview what would be deleted (safe, no changes)
docker-compose run --rm classeviva_sync python3 /app/clear_calendar.py --dry-run --only-synced

# View current logs
docker-compose logs -f

# Force a manual sync
docker-compose exec classeviva_sync python3 /app/classevivaSync.py
```
