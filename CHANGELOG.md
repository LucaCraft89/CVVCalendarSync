# Changelog

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
