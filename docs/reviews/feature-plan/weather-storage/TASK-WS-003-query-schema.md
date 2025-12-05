# TASK-WS-003: Update Query SQL Schema

**Status:** pending
**Priority:** high
**Effort:** 30 min

## Objective

Update `src/lib/query.js` to include new weather columns in the sessions table.

## Changes Required

### 1. Update Empty Sessions Table Schema (line ~169-206)

Add new columns to the CREATE TABLE statement:

```javascript
db.exec(`CREATE TABLE sessions (
  // ... existing columns ...
  temperature FLOAT,
  weatherCode INT,
  humidity FLOAT,           // NEW
  pressure FLOAT,           // NEW
  dewPoint FLOAT,           // NEW
  windSpeed FLOAT,          // NEW
  // ... rest of columns ...
)`);
```

### 2. Update reservedKeywordMap (line ~22-31)

Add mappings if needed:

```javascript
const reservedKeywordMap = {
  // ... existing mappings ...
  'dewPoint': 'dew_point',  // optional: for SQL-friendly naming
};
```

Note: The flattenObject function should automatically handle the new fields since they're at the root level of the session object.

## Acceptance Criteria

- [ ] New weather columns appear in sessions table schema
- [ ] Sessions with weather data populate new columns
- [ ] Sessions without weather data have null in new columns
- [ ] AI chat queries can reference new columns
