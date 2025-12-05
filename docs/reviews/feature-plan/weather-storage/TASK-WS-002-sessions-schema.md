# TASK-WS-002: Update Sessions Firestore Schema

**Status:** pending
**Priority:** high
**Effort:** 30 min

## Objective

Update `src/lib/firestore/sessions.js` to store new weather fields.

## Changes Required

### 1. Update addSession processedData (line ~15-53)

Add after `weatherCode`:

```javascript
humidity: sessionData.humidity !== undefined ? parseFloat(sessionData.humidity) : null,
pressure: sessionData.pressure !== undefined ? parseFloat(sessionData.pressure) : null,
dewPoint: sessionData.dewPoint !== undefined ? parseFloat(sessionData.dewPoint) : null,
windSpeed: sessionData.windSpeed !== undefined ? parseFloat(sessionData.windSpeed) : null,
```

### 2. Update updateSession processedData (line ~159-196)

Add same fields:

```javascript
humidity: sessionData.humidity !== undefined ? parseFloat(sessionData.humidity) : null,
pressure: sessionData.pressure !== undefined ? parseFloat(sessionData.pressure) : null,
dewPoint: sessionData.dewPoint !== undefined ? parseFloat(sessionData.dewPoint) : null,
windSpeed: sessionData.windSpeed !== undefined ? parseFloat(sessionData.windSpeed) : null,
```

## Acceptance Criteria

- [ ] New sessions save all weather fields to Firestore
- [ ] Updated sessions save all weather fields
- [ ] Null handling for missing/undefined values
- [ ] Existing sessions without new fields continue to work
