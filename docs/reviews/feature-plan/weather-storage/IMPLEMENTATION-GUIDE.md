# Implementation Guide: Enhanced Weather Storage

## Architecture Notes

### Data Flow
```
Open-Meteo API → weather.js → NewSession.svelte → sessions.js → Firestore
                                                        ↓
                              SessionsTable.svelte ← query.js ← Firestore
```

### New Fields Schema

```javascript
// Firestore document structure
{
  // Existing weather fields
  temp: 22.5,              // float, Celsius
  weatherCode: 2,          // int, WMO code

  // NEW weather fields
  humidity: 65,            // float, % relative humidity
  pressure: 1013.2,        // float, hPa (sea level)
  dewPoint: 14.8,          // float, Celsius
  windSpeed: 12.5          // float, km/h
}
```

### Open-Meteo API Parameters

```
Historical: archive-api.open-meteo.com/v1/archive
Forecast:   api.open-meteo.com/v1/forecast

hourly=weather_code,temperature_2m,relative_humidity_2m,pressure_msl,dewpoint_2m,wind_speed_10m
```

### Response Mapping

| API Field | Storage Field | Type |
|-----------|---------------|------|
| `temperature_2m` | `temp` | float |
| `weather_code` | `weatherCode` | int |
| `relative_humidity_2m` | `humidity` | float |
| `pressure_msl` | `pressure` | float |
| `dewpoint_2m` | `dewPoint` | float |
| `wind_speed_10m` | `windSpeed` | float |

## Execution Order

### Wave 1: Backend (Parallel)
These tasks modify independent files and can be done simultaneously:

1. **WS-001** - weather.js API
2. **WS-002** - sessions.js schema
3. **WS-003** - query.js SQL
4. **WS-004** - sessionFormat.js formatters

### Wave 2: UI (After Wave 1)
These depend on the backend changes:

5. **WS-005** - NewSession.svelte
6. **WS-006** - SessionsTable.svelte

### Wave 3: Cleanup
7. **WS-007** - Batch updater for historical data

## Testing Strategy

### Manual Testing
1. Create new session → Fetch weather → Verify all fields populated
2. Check Firestore document has new fields
3. Verify sessions list displays new data
4. Test AI chat query: "Show sessions sorted by humidity"

### Edge Cases
- Session with no track location (weather fetch fails)
- Historical date with no API data available
- Existing sessions with null new fields

## Migration Notes

- **No schema migration required** - Firestore is schemaless
- **Backwards compatible** - New fields default to null
- **Backfill optional** - Run batch script to populate historical data

## Jetting Use Cases

With this data, users can:
1. Correlate jet settings with air density (temp + humidity + pressure)
2. Compare performance across similar weather conditions
3. Ask AI: "What jet size did I use when humidity was above 70%?"
4. Track if wet conditions (weatherCode) affect lap times
