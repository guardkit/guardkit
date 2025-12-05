# TASK-WS-007: Update Batch Weather Script

**Status:** pending
**Priority:** low
**Effort:** 30 min

## Objective

Update `upload/update-sessions-weather.js` to fetch and save new weather fields for historical data backfill.

## Changes Required

### 1. Update API Parameters

Add new fields to the hourly parameters in the batch fetch.

### 2. Update Session Update Logic

Save all new weather fields when updating existing sessions.

### 3. Add Backfill Mode

Option to update only sessions missing new fields:

```javascript
// Skip if already has humidity (already backfilled)
if (session.humidity !== null && session.humidity !== undefined) {
  console.log(`Skipping ${session.id} - already has weather data`);
  continue;
}
```

## Usage

```bash
# Backfill all sessions missing new weather data
node upload/update-sessions-weather.js --backfill

# Update specific date range
node upload/update-sessions-weather.js --from 2024-01-01 --to 2024-12-31
```

## Acceptance Criteria

- [ ] Fetches all new weather fields from API
- [ ] Updates sessions in Firestore with new fields
- [ ] Skips sessions that already have data (optional)
- [ ] Logs progress and any errors
