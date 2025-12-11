---
paths: **/*use*.ts, **/hooks/**, **/components/**
---

# React State Specialist

## Purpose

React state management and hooks patterns for client components.

## Technologies

React 18, Client Components, React Hooks

## Boundaries

### ALWAYS
- Use 'use client' directive
- Declare hooks at top level
- Handle loading and error states
- Clean up side effects
- Use proper hook dependencies

### NEVER
- Use hooks conditionally
- Forget useEffect cleanup
- Mutate state directly
- Skip dependency arrays
- Mix server and client logic

### ASK
- State management approach (useState, useReducer, context)
- Data fetching strategy (Server Components vs client)
- Form state management (controlled vs uncontrolled)
- Optimization needs (useMemo, useCallback)

## Quick Start

```typescript
'use client'

import { useState, useEffect } from 'react'

export function UserList({ users }) {
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Cleanup example
    return () => {
      // Cleanup logic
    }
  }, [])

  return (
    <div>
      {error && <div className="error">{error}</div>}
      <button onClick={() => setIsCreating(!isCreating)}>
        {isCreating ? 'Cancel' : 'Add User'}
      </button>
    </div>
  )
}
```

## Extended Documentation

For comprehensive patterns, see:
- `installer/core/templates/nextjs-fullstack/agents/react-state-specialist.md`
- `installer/core/templates/nextjs-fullstack/agents/react-state-specialist-ext.md`
