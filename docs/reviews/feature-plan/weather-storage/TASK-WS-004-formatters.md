# TASK-WS-004: Add Weather Formatters

**Status:** pending
**Priority:** high
**Effort:** 45 min

## Objective

Add formatting functions to `src/lib/sessionFormat.js` for new weather fields.

## Changes Required

### 1. Add formatHumidity Function

```javascript
export function formatHumidity(session) {
  const h = session.humidity;
  if (h === undefined || h === null || h === '') return '-';
  return `${h}%`;
}
```

### 2. Add formatPressure Function

```javascript
export function formatPressure(session) {
  const p = session.pressure;
  if (p === undefined || p === null || p === '') return '-';
  return `${p} hPa`;
}
```

### 3. Add formatDewPoint Function

```javascript
export function formatDewPoint(session) {
  const d = session.dewPoint;
  if (d === undefined || d === null || d === '') return '-';
  return `${d}°C`;
}
```

### 4. Add formatWindSpeed Function

```javascript
export function formatWindSpeed(session) {
  const w = session.windSpeed;
  if (w === undefined || w === null || w === '') return '-';
  return `${w} km/h`;
}
```

### 5. Add formatWeatherSummary Function (Optional)

```javascript
export function formatWeatherSummary(session) {
  const parts = [];
  if (session.temp) parts.push(`${session.temp}°C`);
  if (session.humidity) parts.push(`${session.humidity}%`);
  if (session.pressure) parts.push(`${session.pressure}hPa`);
  return parts.join(' | ') || '-';
}
```

## Acceptance Criteria

- [ ] All formatters handle null/undefined gracefully
- [ ] Units are correctly appended
- [ ] Consistent format with existing formatWeather function
