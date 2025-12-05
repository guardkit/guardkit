# TASK-WS-005: Update NewSession UI

**Status:** pending
**Priority:** medium
**Effort:** 1.5 hrs
**Mode:** task-work

## Objective

Update `src/routes/NewSession.svelte` to display and save new weather fields.

## Changes Required

### 1. Update Form State

Add new fields to form state/store:

```javascript
humidity: null,
pressure: null,
dewPoint: null,
windSpeed: null,
```

### 2. Update Weather Fetch Handler

When weather is fetched, populate all new fields from the API response.

### 3. Display Fetched Weather Data

Show the fetched values to the user (read-only or editable):

```svelte
{#if humidity !== null}
  <div class="weather-detail">
    <span class="label">Humidity:</span>
    <span class="value">{humidity}%</span>
  </div>
{/if}
<!-- Similar for pressure, dewPoint, windSpeed -->
```

### 4. Include in Form Submission

Ensure new fields are included when saving the session.

## UI Considerations

- Weather data section should expand to show all fields
- Consider a compact display format: "22°C | 65% | 1013hPa | 12km/h"
- Make fields editable for manual override if needed

## Acceptance Criteria

- [ ] New weather fields display after fetch
- [ ] Fields are saved to Firestore on submit
- [ ] Manual entry/override works if implemented
- [ ] Graceful display when fields are null
