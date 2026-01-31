# Changelog

## Version 3.0 - Smart Sync & Stability (January 2026)

### Major Features

- **Smart Change Detection**: Hash-based detection checks for changes every 5 minutes
- **Efficient Syncing**: Only syncs when agenda changes or every hour (force sync)
- **Retry Logic**: Automatic retries with exponential backoff (2, 4, 8 seconds)
- **Connection Pooling**: Reuses HTTP connections for better performance and reliability

### Sync Improvements

- **Check Frequency**: Now checks every 5 minutes (was 1 hour)
- **Smart Logic**: Skips sync if no changes detected and force interval not reached
- **Force Sync**: Guarantees full sync every 1 hour regardless of changes
- **State Tracking**: Maintains `sync_state.json` to track sync history and hashes

### Stability Enhancements

- **HTTP Session**: Connection pooling with automatic retries
- **Timeout Handling**: All API calls have 30-second timeouts
- **Individual Error Handling**: Failed event operations don't stop entire sync
- **Better Exception Handling**: Detailed error messages with stack traces

### Logging Improvements

- **Detailed Format**: Includes function name, line number, and timestamp
- **Sync Decisions**: Logs why sync happened or was skipped
- **Hash Tracking**: Shows old vs new hash when changes detected
- **Event Counts**: Detailed counts of added/updated/deleted/skipped events
- **Progress Updates**: Better visibility into what's happening

### Technical Details

- Added: `load_state()`, `save_state()`, `compute_agenda_hash()`
- Added: `should_sync()`, `perform_sync()`, `get_requests_session()`
- Enhanced: All API functions with retry logic and better error handling
- Enhanced: All logging with more context and detail
- Updated: Cronjob to run every 5 minutes
- Updated: Dockerfile to handle state file

### Migration

No configuration changes needed! Simply rebuild:

```bash
docker-compose down
docker-compose up -d --build
```

See [UPGRADE_SUMMARY.md](UPGRADE_SUMMARY.md) for detailed changes.

## Version 2.0 - Major Improvements

### Fixed

- **Duplicate Events**: Events are now tracked using unique IDs with extended properties, preventing duplicates
- **Event Deletion**: Only removes events created by this sync, won't delete other calendar events
- **Event Updates**: Properly updates existing events when details change instead of creating duplicates

### Added

- **Proper Logging**: Replaced print statements with structured logging (compatible with `docker compose logs`)
- **Health Check**: Added health check endpoint for Docker monitoring
- **Better Error Handling**: More specific error messages and proper exit codes
- **Event Tracking**: Uses ClasseViva event IDs and extended properties to track synced events
- **Update Detection**: Updates events when they change instead of just adding/deleting
- **Type Hints**: Added type hints for better code clarity
- **Validation**: Better validation of configuration and event data

### Improved

- **Docker Logging**: Logs now properly stream to Docker stdout/stderr
- **Docker Compose**: Added proper logging configuration with rotation
- **Health Monitoring**: Container health can be monitored with `docker compose ps`
- **Restart Policy**: Changed to `unless-stopped` for better control
- **Security**: Config files mounted as read-only
- **Python Version**: Updated to Python 3.11

### Usage

```bash
# View logs in real-time
docker compose logs -f classeviva_sync

# Check health status
docker compose ps

# View recent logs (last 100 lines)
docker compose logs --tail 100 classeviva_sync

# Rebuild and restart
docker compose up -d --build
```
