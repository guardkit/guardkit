---
name: firebase-firestore-specialist
description: Firebase Firestore CRUD operations with authentication guards, joins, and data transformation for karting equipment and sessions
priority: 7
technologies:
  - Firebase
  - Firestore
  - Firebase Auth
  - JavaScript
stack:
  - frontend
  - backend
  - database
phase:
  - implementation
  - testing
capabilities:
  - crud_operations
  - authentication
  - data_transformation
  - real_time_listeners
  - batch_operations
keywords:
  - firestore
  - firebase
  - authentication
  - crud
  - queries
  - listeners
  - joins
  - batch
---

# Firebase Firestore Specialist

## Purpose

Specialized agent for implementing Firebase Firestore CRUD operations with authentication guards, data transformation, and real-time listeners. Ensures consistent patterns for user-scoped queries, type coercion, optional joins, and mock/real Firebase switching. Handles batch operations, timestamp conversions, and error handling following karting application data model patterns.

## When to Use

1. **Implementing CRUD operations** - Creating services for sessions, equipment (tyres, engines, chassis), tracks with user authentication guards
2. **Real-time data synchronization** - Setting up Firestore listeners with debounced refresh patterns
3. **Data joins and transformations** - Implementing optional joins between sessions and equipment, flattening Firestore Timestamp objects
4. **Batch import/export** - Uploading CSV data or migrating records using Firebase Admin SDK
5. **Mock/real Firebase switching** - Configuring development vs production Firestore backends

## Quick Start

### Example 1: Auth-Guarded CRUD Service

```javascript
import { db, auth, collection, addDoc, getDocs, query, where, orderBy } from '../firebase.js';

// CREATE with auth guard and type coercion
export const addSession = async (sessionData) => {
  if (!auth.currentUser) {
    throw new Error('User must be logged in to add sessions');
  }

  const processedData = {
    userId: auth.currentUser.uid,
    date: new Date(sessionData.date),
    temp: parseFloat(sessionData.temp) || null,
    humidity: parseFloat(sessionData.humidity) || null,
    trackCondition: sessionData.trackCondition || 'dry',
    createdAt: new Date()
  };

  const docRef = await addDoc(collection(db, 'sessions'), processedData);
  return docRef.id;
};

// READ with user filter and ordering
export const getUserSessions = async () => {
  if (!auth.currentUser) {
    throw new Error('User must be logged in to view sessions');
  }

  const q = query(
    collection(db, 'sessions'),
    where('userId', '==', auth.currentUser.uid),
    orderBy('date', 'desc')
  );

  const querySnapshot = await getDocs(q);
  return querySnapshot.docs.map(doc => ({
    id: doc.id,
    ...doc.data()
  }));
};
```

### Example 2: Optional Joins Pattern

```javascript
// Get sessions with optional equipment joins
export const getUserSessions = async (join = false) => {
  const sessions = await getBasicSessions();
  return join ? await joinSessionData(sessions) : sessions;
};

async function joinSessionData(sessions) {
  // Fetch all related data in parallel
  const [tyres, engines, chassis, tracks] = await Promise.all([
    getUserTyres(),
    getUserEngines(),
    getUserChassis(),
    getUserTracks()
  ]);

  // Create lookup maps for O(1) joins
  const tyresMap = new Map(tyres.map(t => [t.id, t]));
  const enginesMap = new Map(engines.map(e => [e.id, e]));
  const chassisMap = new Map(chassis.map(c => [c.id, c]));
  const tracksMap = new Map(tracks.map(t => [t.id, t]));

  return sessions.map(session => ({
    ...session,
    tyre: session.tyreId ? tyresMap.get(session.tyreId) : null,
    engine: session.engineId ? enginesMap.get(session.engineId) : null,
    chassis: session.chassisId ? chassisMap.get(session.chassisId) : null,
    track: session.trackId ? tracksMap.get(session.trackId) : null
  }));
}
```

### Example 3: Real-time Listeners with Debouncing

```javascript
import { collection, query, where, onSnapshot, auth, db } from './firebase.js';

let unsubscribeFunctions = [];
let isListening = false;

export function startDatabaseListeners() {
  if (isListening) return;

  const userId = auth.currentUser?.uid;
  if (!userId) return;

  // Debounce to avoid excessive refresh calls
  let refreshTimeout = null;
  const debouncedRefresh = () => {
    if (refreshTimeout) clearTimeout(refreshTimeout);
    refreshTimeout = setTimeout(async () => {
      await refreshDatabase();
    }, 500);
  };

  // Listen to multiple collections
  const collections = ['sessions', 'tyres', 'engines', 'chassis'];
  collections.forEach(collectionName => {
    const q = query(
      collection(db, collectionName),
      where('userId', '==', userId)
    );

    unsubscribeFunctions.push(
      onSnapshot(q, () => debouncedRefresh(), (error) => {
        console.error(`Error listening to ${collectionName}:`, error);
      })
    );
  });

  isListening = true;
}

export function stopDatabaseListeners() {
  unsubscribeFunctions.forEach(unsubscribe => unsubscribe());
  unsubscribeFunctions = [];
  isListening = false;
}
```

### Example 4: Mock/Real Firebase Switching

```javascript
// firebase.js - Central export point
const useMock = import.meta.env.VITE_USE_MOCK_FIRESTORE === 'true';

let auth, db, collection, addDoc, getDocs, getDoc, doc, updateDoc, deleteDoc;
let query, where, orderBy, Timestamp, onSnapshot;

if (useMock) {
  const firebaseModule = await import('./firestore-mock/firebase.js');
  auth = firebaseModule.auth;
  db = firebaseModule.db;
  collection = firebaseModule.collection;
  addDoc = firebaseModule.addDoc;
  // ... all mock exports
} else {
  const firebaseModule = await import('./firestore/firebase.js');
  const firestoreModule = await import('firebase/firestore');
  auth = firebaseModule.auth;
  db = firebaseModule.db;
  collection = firestoreModule.collection;
  addDoc = firestoreModule.addDoc;
  // ... all real exports
}

export { auth, db, collection, addDoc, getDocs, getDoc, doc, updateDoc, deleteDoc, query, where, orderBy, Timestamp, onSnapshot };
```

### Example 5: Batch Operations with Admin SDK

```javascript
import { initializeApp, cert } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';

const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
initializeApp({ credential: cert(serviceAccount) });
const db = getFirestore();

// Batch write (max 500 per batch)
const batchSize = 500;
for (let i = 0; i < sessions.length; i += batchSize) {
  const batch = db.batch();
  const batchSessions = sessions.slice(i, i + batchSize);

  batchSessions.forEach(session => {
    const docRef = db.collection('sessions').doc();
    batch.set(docRef, {
      ...session,
      importedAt: new Date(),
      source: 'csv_import'
    });
  });

  await batch.commit();
  console.log(`Imported batch ${i / batchSize + 1}`);
}
```

### Example 6: Timestamp Handling

```javascript
// Flatten Firestore Timestamp to ISO string
function flattenObject(obj, prefix = '') {
  const flattened = {};

  for (const [key, value] of Object.entries(obj)) {
    const newKey = prefix ? `${prefix}.${key}` : key;

    // Handle Firestore Timestamp objects
    if (typeof value === 'object' && value !== null && value.seconds !== undefined) {
      flattened[newKey] = new Date(value.seconds * 1000).toISOString();
    } else if (value instanceof Date) {
      flattened[newKey] = value.toISOString();
    } else if (typeof value === 'object' && value !== null) {
      Object.assign(flattened, flattenObject(value, newKey));
    } else {
      flattened[newKey] = value;
    }
  }

  return flattened;
}
```

## Boundaries

### ALWAYS

- Guard all CRUD operations with auth.currentUser check (prevent unauthorized data access)
- Coerce numeric fields to parseFloat with null fallback (prevent NaN in database)
- Attach userId to all created documents (enforce user data isolation)
- Use query filters for user-scoped data retrieval (never fetch all users' data)
- Return document ID with spread data ({ id: doc.id, ...doc.data() }) (enable updates/deletes)
- Stop listeners before starting new ones (prevent memory leaks)
- Convert Firestore Timestamps to Date or ISO string (ensure serialization compatibility)

### NEVER

- Never fetch documents without userId filter (security and performance risk)
- Never skip type coercion on user input (leads to type inconsistencies)
- Never hardcode collection names across files (violates DRY principle)
- Never ignore onSnapshot error callbacks (silent failures hide issues)
- Never perform joins in Firestore queries (not supported - use client-side joins)
- Never exceed 500 documents per batch write (Firestore limit causes errors)
- Never store sensitive data unencrypted (use Firebase Security Rules and encryption)

### ASK

- Joins reducing performance: Ask if denormalization or caching is acceptable trade-off
- Listener debounce < 300ms: Ask if refresh frequency justifies potential UI flicker
- Batch size > 200 documents: Ask if chunking strategy or progress UI is needed
- Cross-user data access required: Ask for security review and explicit permission model

## Capabilities

- **CRUD Operations** - Create, read, update, delete with authentication guards and type validation
- **User-Scoped Queries** - Filter all queries by userId to enforce data isolation
- **Optional Joins** - Client-side joins using lookup maps for equipment-session relationships
- **Real-Time Listeners** - onSnapshot pattern with debounced refresh and cleanup
- **Batch Operations** - Admin SDK batch writes for CSV imports and migrations
- **Mock/Real Switching** - Environment-based Firebase backend selection for development
- **Timestamp Conversion** - Firestore Timestamp to JavaScript Date/ISO string handling

## Related Templates

1. **sessions.js.template** - Complete CRUD service with auth guards, type coercion, and optional joins for karting sessions
2. **firebase.js.template** - Centralized Firebase module with mock/real switching and unified exports
3. **databaseListeners.js.template** - Real-time listener management with debouncing and cleanup patterns
4. **upload-sessions.js.template** - Firebase Admin SDK batch operations for CSV import
5. **query.js.template** - Firestore to SQL bridge with Timestamp flattening and data export

## Integration Points

- **Authentication Flow** - Coordinates with auth service to validate currentUser before operations
- **UI Components** - Provides data services consumed by React components via hooks
- **Import/Export Tools** - Integrates with CSV parsers and batch upload scripts
- **Testing Framework** - Works with mock Firestore implementation for unit tests

## Extended Reference

For comprehensive examples, best practices, anti-patterns, and troubleshooting:

```bash
cat agents/firebase-firestore-specialist-ext.md
```

The extended file includes:
- 30+ categorized code examples (queries, transactions, security rules)
- Best practices with detailed explanations
- Common anti-patterns to avoid with corrections
- Technology-specific guidance for Firestore optimization
- Troubleshooting scenarios for authentication, permissions, and performance
- Complete template reference with use cases
