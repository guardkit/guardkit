# TASK-WS-006: Update SessionsTable Display

**Status:** pending
**Priority:** medium
**Effort:** 1 hr
**Mode:** task-work

## Objective

Update `src/components/SessionsTable.svelte` to display new weather data.

## Changes Required

### 1. Weather Column Enhancement

Option A: Expand existing weather column with tooltip:
```svelte
<td title="{session.humidity}% humidity, {session.pressure}hPa, {session.windSpeed}km/h wind">
  {weatherCodeEmoji(session.weatherCode)} {session.temp}°C
</td>
```

Option B: Add separate columns (if space permits):
```svelte
<th>Humidity</th>
<th>Pressure</th>
```

### 2. Import New Formatters

```javascript
import {
  formatHumidity,
  formatPressure,
  formatDewPoint,
  formatWindSpeed
} from '$lib/sessionFormat.js';
```

### 3. Responsive Considerations

- On mobile: Keep compact (tooltip approach)
- On desktop: Consider expandable row detail

## UI Options

1. **Tooltip only** - Minimal change, hover to see details
2. **Expandable row** - Click to reveal full weather data
3. **Additional columns** - Most visible but takes space

## Acceptance Criteria

- [ ] Weather data visible in sessions list
- [ ] Tooltip or detail view shows all fields
- [ ] Handles null values gracefully
- [ ] Mobile-responsive
