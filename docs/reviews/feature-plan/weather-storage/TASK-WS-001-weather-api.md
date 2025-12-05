# TASK-WS-001: Update Weather API Integration

**Status:** pending
**Priority:** high
**Effort:** 30 min

## Objective

Update `src/lib/weather.js` to fetch additional weather parameters from Open-Meteo API.

## Changes Required

### 1. Update API URL Parameters

Add to the `hourly` parameter:
- `relative_humidity_2m`
- `pressure_msl`
- `dewpoint_2m`
- `wind_speed_10m`

### 2. Historical Weather URL (line ~24)

```javascript
// Before
const url = `...&hourly=weather_code,temperature_2m&timezone=auto`;

// After
const url = `...&hourly=weather_code,temperature_2m,relative_humidity_2m,pressure_msl,dewpoint_2m,wind_speed_10m&timezone=auto`;
```

### 3. Forecast Weather URL (line ~37)

```javascript
// Before
response = await fetch(`...&hourly=weather_code,temperature_2m&timezone=auto`);

// After
response = await fetch(`...&hourly=weather_code,temperature_2m,relative_humidity_2m,pressure_msl,dewpoint_2m,wind_speed_10m&timezone=auto`);
```

### 4. Update Return Object

Extract and return additional fields:

```javascript
return {
  temp: String(Math.round(weatherData.temperature * 10) / 10),
  weatherCode: weatherData.weatherCode,
  humidity: Math.round(weatherData.humidity),
  pressure: Math.round(weatherData.pressure * 10) / 10,
  dewPoint: Math.round(weatherData.dewPoint * 10) / 10,
  windSpeed: Math.round(weatherData.windSpeed * 10) / 10
};
```

## Acceptance Criteria

- [ ] Historical weather API returns all new fields
- [ ] Forecast weather API returns all new fields
- [ ] Values are properly rounded
- [ ] Existing temp and weatherCode behavior unchanged
