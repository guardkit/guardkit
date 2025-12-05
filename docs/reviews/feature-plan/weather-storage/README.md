# Feature: Enhanced Weather Data Storage

**Parent Task:** TASK-REV-WEATHER-STORAGE
**Status:** In Progress
**Created:** 2025-12-05

## Overview

Add comprehensive weather data storage to sessions for jetting calculations and performance analysis.

## New Fields

| Field | Type | Unit | Purpose |
|-------|------|------|---------|
| `humidity` | float | % | Relative humidity (air density) |
| `pressure` | float | hPa | Sea-level barometric pressure |
| `dewPoint` | float | °C | Moisture saturation temperature |
| `windSpeed` | float | km/h | Wind conditions |

## Subtasks

| ID | Task | Status | Mode |
|----|------|--------|------|
| WS-001 | Update weather.js API integration | pending | direct |
| WS-002 | Update sessions.js Firestore schema | pending | direct |
| WS-003 | Update query.js SQL schema | pending | direct |
| WS-004 | Add formatters to sessionFormat.js | pending | direct |
| WS-005 | Update NewSession.svelte UI | pending | task-work |
| WS-006 | Update SessionsTable.svelte display | pending | task-work |
| WS-007 | Update batch weather update script | pending | direct |

## Execution Strategy

**Wave 1 (Parallel - Backend):**
- WS-001, WS-002, WS-003, WS-004

**Wave 2 (Sequential - UI):**
- WS-005, WS-006

**Wave 3 (Cleanup):**
- WS-007

## Files Modified

- `src/lib/weather.js`
- `src/lib/firestore/sessions.js`
- `src/lib/query.js`
- `src/lib/sessionFormat.js`
- `src/routes/NewSession.svelte`
- `src/components/SessionsTable.svelte`
- `upload/update-sessions-weather.js`
