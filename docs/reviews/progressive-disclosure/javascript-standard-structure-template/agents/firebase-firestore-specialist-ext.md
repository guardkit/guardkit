# Firebase Firestore Specialist - Extended Reference

Comprehensive guide for implementing Firebase Firestore operations in karting application context.

## Table of Contents

1. [Code Examples](#code-examples)
2. [Best Practices](#best-practices)
3. [Anti-Patterns](#anti-patterns)
4. [Technology-Specific Guidance](#technology-specific-guidance)
5. [Troubleshooting](#troubleshooting)
6. [Related Templates](#related-templates)

---

## Code Examples

### Category 1: CRUD Operations

#### Example 1.1: Complete CRUD Service for Equipment

```javascript
import { db, auth, collection, addDoc, getDocs, getDoc, doc, updateDoc, deleteDoc, query, where, orderBy } from '../firebase.js';

// CREATE
export const addTyre = async (tyreData) => {
  if (!auth.currentUser) {
    throw new Error('User must be logged in to add tyres');
  }

  const processedData = {
    userId: auth.currentUser.uid,
    manufacturer: tyreData.manufacturer || '',
    model: tyreData.model || '',
    compound: tyreData.compound || '',
    purchaseDate: new Date(tyreData.purchaseDate),
    isRetired: false,
    createdAt: new Date(),
    updatedAt: new Date()
  };

  const docRef = await addDoc(collection(db, 'tyres'), processedData);
  return docRef.id;
};

// READ ALL
export const getUserTyres = async () => {
  if (!auth.currentUser) {
    throw new Error('User must be logged in to view tyres');
  }

  const q = query(
    collection(db, 'tyres'),
    where('userId', '==', auth.currentUser.uid),
    orderBy('purchaseDate', 'desc')
  );

  const querySnapshot = await getDocs(q);
  return querySnapshot.docs.map(doc => ({
    id: doc.id,
    ...doc.data()
  }));
};

// READ ONE
export const getTyre = async (tyreId) => {
  if (!auth.currentUser) {
    throw new Error('User must be logged in');
  }

  const docRef = doc(db, 'tyres', tyreId);
  const docSnap = await getDoc(docRef);

  if (!docSnap.exists()) {
    throw new Error('Tyre not found');
  }

  const data = docSnap.data();
  if (data.userId !== auth.currentUser.uid) {
    throw new Error('Unauthorized access to tyre');
  }

  return { id: docSnap.id, ...data };
};

// UPDATE
export const updateTyre = async (tyreId, updates) => {
  if (!auth.currentUser) {
    throw new Error('User must be logged in');
  }

  // Verify ownership
  const existing = await getTyre(tyreId);

  const processedUpdates = {
    ...updates,
    updatedAt: new Date()
  };

  // Remove fields that shouldn't be updated
  delete processedUpdates.userId;
  delete processedUpdates.createdAt;
  delete processedUpdates.id;

  const docRef = doc(db, 'tyres', tyreId);
  await updateDoc(docRef, processedUpdates);
};

// DELETE (Soft Delete)
export const retireTyre = async (tyreId) => {
  await updateTyre(tyreId, { isRetired: true, retiredAt: new Date() });
};

// DELETE (Hard Delete)
export const deleteTyre = async (tyreId) => {
  if (!auth.currentUser) {
    throw new Error('User must be logged in');
  }

  // Verify ownership
  await getTyre(tyreId);

  const docRef = doc(db, 'tyres', tyreId);
  await deleteDoc(docRef);
};
```

#### Example 1.2: Type Coercion Patterns

```javascript
// Helper function for safe numeric conversion
function toNumber(value, defaultValue = null) {
  if (value === '' || value === undefined || value === null) {
    return defaultValue;
  }
  const num = parseFloat(value);
  return isNaN(num) ? defaultValue : num;
}

// Helper for date conversion
function toDate(value, defaultValue = null) {
  if (!value) return defaultValue;
  const date = new Date(value);
  return isNaN(date.getTime()) ? defaultValue : date;
}

// Apply to session data
export const addSession = async (sessionData) => {
  if (!auth.currentUser) {
    throw new Error('User must be logged in');
  }

  const processedData = {
    userId: auth.currentUser.uid,
    date: toDate(sessionData.date, new Date()),
    temp: toNumber(sessionData.temp),
    humidity: toNumber(sessionData.humidity),
    pressure: toNumber(sessionData.pressure),
    trackId: sessionData.trackId || null,
    tyreId: sessionData.tyreId || null,
    engineId: sessionData.engineId || null,
    chassisId: sessionData.chassisId || null,
    trackCondition: sessionData.trackCondition || 'dry',
    notes: sessionData.notes || '',
    bestLapTime: toNumber(sessionData.bestLapTime),
    createdAt: new Date()
  };

  return await addDoc(collection(db, 'sessions'), processedData);
};
```

### Category 2: Querying Patterns

#### Example 2.1: Complex Queries with Multiple Filters

```javascript
import { query, where, orderBy, limit, startAfter } from 'firebase/firestore';

// Get sessions within date range
export const getSessionsByDateRange = async (startDate, endDate) => {
  if (!auth.currentUser) {
    throw new Error('User must be logged in');
  }

  const q = query(
    collection(db, 'sessions'),
    where('userId', '==', auth.currentUser.uid),
    where('date', '>=', new Date(startDate)),
    where('date', '<=', new Date(endDate)),
    orderBy('date', 'desc')
  );

  const querySnapshot = await getDocs(q);
  return querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
};

// Get sessions for specific equipment
export const getSessionsByTyre = async (tyreId) => {
  if (!auth.currentUser) {
    throw new Error('User must be logged in');
  }

  const q = query(
    collection(db, 'sessions'),
    where('userId', '==', auth.currentUser.uid),
    where('tyreId', '==', tyreId),
    orderBy('date', 'desc')
  );

  const querySnapshot = await getDocs(q);
  return querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
};

// Pagination pattern
export const getSessionsPaginated = async (pageSize = 20, lastDoc = null) => {
  if (!auth.currentUser) {
    throw new Error('User must be logged in');
  }

  let q = query(
    collection(db, 'sessions'),
    where('userId', '==', auth.currentUser.uid),
    orderBy('date', 'desc'),
    limit(pageSize)
  );

  if (lastDoc) {
    q = query(q, startAfter(lastDoc));
  }

  const querySnapshot = await getDocs(q);
  return {
    sessions: querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })),
    lastDoc: querySnapshot.docs[querySnapshot.docs.length - 1]
  };
};
```

#### Example 2.2: Active/Retired Equipment Filtering

```javascript
// Get only active equipment
export const getActiveTyres = async () => {
  if (!auth.currentUser) {
    throw new Error('User must be logged in');
  }

  const q = query(
    collection(db, 'tyres'),
    where('userId', '==', auth.currentUser.uid),
    where('isRetired', '==', false),
    orderBy('purchaseDate', 'desc')
  );

  const querySnapshot = await getDocs(q);
  return querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
};

// Get all equipment (active and retired)
export const getAllTyres = async (includeRetired = false) => {
  if (!auth.currentUser) {
    throw new Error('User must be logged in');
  }

  let q = query(
    collection(db, 'tyres'),
    where('userId', '==', auth.currentUser.uid)
  );

  if (!includeRetired) {
    q = query(q, where('isRetired', '==', false));
  }

  q = query(q, orderBy('purchaseDate', 'desc'));

  const querySnapshot = await getDocs(q);
  return querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
};
```

### Category 3: Joins and Data Transformation

#### Example 3.1: Parallel Fetch with Lookup Maps

```javascript
// Efficient join pattern using Promise.all and Maps
export const getUserSessions = async (join = false) => {
  if (!auth.currentUser) {
    throw new Error('User must be logged in');
  }

  const q = query(
    collection(db, 'sessions'),
    where('userId', '==', auth.currentUser.uid),
    orderBy('date', 'desc')
  );

  const querySnapshot = await getDocs(q);
  const sessions = querySnapshot.docs.map(doc => ({
    id: doc.id,
    ...doc.data()
  }));

  return join ? await joinSessionData(sessions) : sessions;
};

async function joinSessionData(sessions) {
  // Fetch all related collections in parallel
  const [tyres, engines, chassis, tracks] = await Promise.all([
    getUserTyres(),
    getUserEngines(),
    getUserChassis(),
    getUserTracks()
  ]);

  // Create lookup maps for O(1) access
  const tyresMap = new Map(tyres.map(t => [t.id, t]));
  const enginesMap = new Map(engines.map(e => [e.id, e]));
  const chassisMap = new Map(chassis.map(c => [c.id, c]));
  const tracksMap = new Map(tracks.map(t => [t.id, t]));

  // Join data
  return sessions.map(session => ({
    ...session,
    tyre: session.tyreId ? tyresMap.get(session.tyreId) : null,
    engine: session.engineId ? enginesMap.get(session.engineId) : null,
    chassis: session.chassisId ? chassisMap.get(session.chassisId) : null,
    track: session.trackId ? tracksMap.get(session.trackId) : null
  }));
}
```

#### Example 3.2: Selective Join (Only Needed Relations)

```javascript
// Join only specific relations
export const getSessionsWithTyreData = async () => {
  if (!auth.currentUser) {
    throw new Error('User must be logged in');
  }

  const [sessions, tyres] = await Promise.all([
    getBasicSessions(),
    getUserTyres()
  ]);

  const tyresMap = new Map(tyres.map(t => [t.id, t]));

  return sessions.map(session => ({
    ...session,
    tyre: session.tyreId ? tyresMap.get(session.tyreId) : null
  }));
};

// Join with computed fields
export const getSessionsWithEquipmentAge = async () => {
  const sessions = await getUserSessions(true);

  return sessions.map(session => {
    const tyreAge = session.tyre?.purchaseDate
      ? Math.floor((session.date - session.tyre.purchaseDate) / (1000 * 60 * 60 * 24))
      : null;

    return {
      ...session,
      tyreAgeInDays: tyreAge
    };
  });
};
```

### Category 4: Real-Time Listeners

#### Example 4.1: Multiple Collection Listeners

```javascript
import { collection, query, where, onSnapshot, auth, db } from './firebase.js';

let unsubscribeFunctions = [];
let isListening = false;

export function startDatabaseListeners() {
  if (isListening) {
    console.warn('Database listeners already active');
    return;
  }

  const userId = auth.currentUser?.uid;
  if (!userId) {
    console.error('No authenticated user for listeners');
    return;
  }

  // Debounce refresh to avoid excessive calls
  let refreshTimeout = null;
  const debouncedRefresh = () => {
    if (refreshTimeout) clearTimeout(refreshTimeout);
    refreshTimeout = setTimeout(async () => {
      console.log('Refreshing database due to changes');
      await refreshDatabase();
    }, 500);
  };

  // Listen to all user collections
  const collections = ['sessions', 'tyres', 'engines', 'chassis', 'tracks'];

  collections.forEach(collectionName => {
    const q = query(
      collection(db, collectionName),
      where('userId', '==', userId)
    );

    const unsubscribe = onSnapshot(
      q,
      (snapshot) => {
        console.log(`${collectionName} changed: ${snapshot.docChanges().length} changes`);
        debouncedRefresh();
      },
      (error) => {
        console.error(`Error listening to ${collectionName}:`, error);
      }
    );

    unsubscribeFunctions.push(unsubscribe);
  });

  isListening = true;
  console.log('Database listeners started');
}

export function stopDatabaseListeners() {
  console.log('Stopping database listeners');
  unsubscribeFunctions.forEach(unsubscribe => unsubscribe());
  unsubscribeFunctions = [];
  isListening = false;
}
```

#### Example 4.2: Single Document Listener

```javascript
// Listen to specific session changes
export function listenToSession(sessionId, callback) {
  if (!auth.currentUser) {
    throw new Error('User must be logged in');
  }

  const docRef = doc(db, 'sessions', sessionId);

  const unsubscribe = onSnapshot(
    docRef,
    (docSnap) => {
      if (docSnap.exists()) {
        const data = docSnap.data();
        if (data.userId === auth.currentUser.uid) {
          callback({ id: docSnap.id, ...data });
        } else {
          console.error('Unauthorized access attempt');
          unsubscribe();
        }
      } else {
        callback(null);
      }
    },
    (error) => {
      console.error('Listener error:', error);
    }
  );

  return unsubscribe;
}

// Usage
const unsubscribe = listenToSession('session123', (session) => {
  if (session) {
    console.log('Session updated:', session);
  } else {
    console.log('Session deleted');
  }
});

// Cleanup when done
unsubscribe();
```

### Category 5: Batch Operations

#### Example 5.1: CSV Import with Batch Writes

```javascript
import { initializeApp, cert } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import fs from 'fs';
import csv from 'csv-parser';

const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
initializeApp({ credential: cert(serviceAccount) });
const db = getFirestore();

async function importSessionsFromCSV(filePath, userId) {
  const sessions = [];

  // Read CSV
  await new Promise((resolve, reject) => {
    fs.createReadStream(filePath)
      .pipe(csv())
      .on('data', (row) => {
        sessions.push({
          userId,
          date: new Date(row.date),
          temp: parseFloat(row.temp) || null,
          humidity: parseFloat(row.humidity) || null,
          trackCondition: row.trackCondition || 'dry',
          notes: row.notes || '',
          importedAt: new Date(),
          source: 'csv_import'
        });
      })
      .on('end', resolve)
      .on('error', reject);
  });

  console.log(`Importing ${sessions.length} sessions`);

  // Firestore batch limit is 500
  const batchSize = 500;
  let importedCount = 0;

  for (let i = 0; i < sessions.length; i += batchSize) {
    const batch = db.batch();
    const batchSessions = sessions.slice(i, i + batchSize);

    batchSessions.forEach(session => {
      const docRef = db.collection('sessions').doc();
      batch.set(docRef, session);
    });

    await batch.commit();
    importedCount += batchSessions.length;
    console.log(`Imported ${importedCount}/${sessions.length} sessions`);
  }

  console.log('Import complete');
  return importedCount;
}
```

#### Example 5.2: Bulk Update Pattern

```javascript
// Update multiple documents (e.g., retire all tyres of a model)
export async function retireAllTyresOfModel(manufacturer, model) {
  if (!auth.currentUser) {
    throw new Error('User must be logged in');
  }

  // Fetch all matching tyres
  const q = query(
    collection(db, 'tyres'),
    where('userId', '==', auth.currentUser.uid),
    where('manufacturer', '==', manufacturer),
    where('model', '==', model),
    where('isRetired', '==', false)
  );

  const querySnapshot = await getDocs(q);

  // Update in batches
  const batchSize = 500;
  const docs = querySnapshot.docs;

  for (let i = 0; i < docs.length; i += batchSize) {
    const batch = db.batch();
    const batchDocs = docs.slice(i, i + batchSize);

    batchDocs.forEach(docSnap => {
      batch.update(docSnap.ref, {
        isRetired: true,
        retiredAt: new Date(),
        retiredReason: 'Bulk retirement'
      });
    });

    await batch.commit();
  }

  return docs.length;
}
```

### Category 6: Timestamp and Date Handling

#### Example 6.1: Firestore Timestamp Conversion

```javascript
import { Timestamp } from 'firebase/firestore';

// Convert Firestore Timestamp to JavaScript Date
function timestampToDate(timestamp) {
  if (!timestamp) return null;
  if (timestamp instanceof Date) return timestamp;
  if (typeof timestamp === 'object' && timestamp.seconds !== undefined) {
    return new Date(timestamp.seconds * 1000);
  }
  return new Date(timestamp);
}

// Convert JavaScript Date to Firestore Timestamp
function dateToTimestamp(date) {
  if (!date) return null;
  if (date instanceof Timestamp) return date;
  return Timestamp.fromDate(new Date(date));
}

// Flatten object with Timestamp conversion
function flattenObject(obj, prefix = '') {
  const flattened = {};

  for (const [key, value] of Object.entries(obj)) {
    const newKey = prefix ? `${prefix}.${key}` : key;

    // Handle Firestore Timestamp
    if (typeof value === 'object' && value !== null && value.seconds !== undefined) {
      flattened[newKey] = new Date(value.seconds * 1000).toISOString();
    } else if (value instanceof Date) {
      flattened[newKey] = value.toISOString();
    } else if (Array.isArray(value)) {
      flattened[newKey] = JSON.stringify(value);
    } else if (typeof value === 'object' && value !== null) {
      Object.assign(flattened, flattenObject(value, newKey));
    } else {
      flattened[newKey] = value;
    }
  }

  return flattened;
}
```

#### Example 6.2: Date Range Queries

```javascript
// Get sessions from last 30 days
export async function getRecentSessions(days = 30) {
  if (!auth.currentUser) {
    throw new Error('User must be logged in');
  }

  const endDate = new Date();
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - days);

  const q = query(
    collection(db, 'sessions'),
    where('userId', '==', auth.currentUser.uid),
    where('date', '>=', startDate),
    where('date', '<=', endDate),
    orderBy('date', 'desc')
  );

  const querySnapshot = await getDocs(q);
  return querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
}

// Get sessions grouped by month
export async function getSessionsByMonth(year) {
  if (!auth.currentUser) {
    throw new Error('User must be logged in');
  }

  const startDate = new Date(year, 0, 1);
  const endDate = new Date(year, 11, 31, 23, 59, 59);

  const q = query(
    collection(db, 'sessions'),
    where('userId', '==', auth.currentUser.uid),
    where('date', '>=', startDate),
    where('date', '<=', endDate),
    orderBy('date', 'asc')
  );

  const querySnapshot = await getDocs(q);
  const sessions = querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));

  // Group by month
  const byMonth = {};
  sessions.forEach(session => {
    const month = session.date.toDate().getMonth();
    if (!byMonth[month]) byMonth[month] = [];
    byMonth[month].push(session);
  });

  return byMonth;
}
```

### Category 7: Mock/Real Firebase Switching

#### Example 7.1: Central Firebase Module

```javascript
// firebase.js - Central export point
const useMock = import.meta.env.VITE_USE_MOCK_FIRESTORE === 'true';

let auth, db, collection, addDoc, getDocs, getDoc, doc, updateDoc, deleteDoc;
let query, where, orderBy, limit, startAfter, Timestamp, onSnapshot;

if (useMock) {
  console.log('Using MOCK Firebase');
  const firebaseModule = await import('./firestore-mock/firebase.js');
  auth = firebaseModule.auth;
  db = firebaseModule.db;
  collection = firebaseModule.collection;
  addDoc = firebaseModule.addDoc;
  getDocs = firebaseModule.getDocs;
  getDoc = firebaseModule.getDoc;
  doc = firebaseModule.doc;
  updateDoc = firebaseModule.updateDoc;
  deleteDoc = firebaseModule.deleteDoc;
  query = firebaseModule.query;
  where = firebaseModule.where;
  orderBy = firebaseModule.orderBy;
  limit = firebaseModule.limit;
  startAfter = firebaseModule.startAfter;
  Timestamp = firebaseModule.Timestamp;
  onSnapshot = firebaseModule.onSnapshot;
} else {
  console.log('Using REAL Firebase');
  const firebaseModule = await import('./firestore/firebase.js');
  const firestoreModule = await import('firebase/firestore');
  auth = firebaseModule.auth;
  db = firebaseModule.db;
  collection = firestoreModule.collection;
  addDoc = firestoreModule.addDoc;
  getDocs = firestoreModule.getDocs;
  getDoc = firestoreModule.getDoc;
  doc = firestoreModule.doc;
  updateDoc = firestoreModule.updateDoc;
  deleteDoc = firestoreModule.deleteDoc;
  query = firestoreModule.query;
  where = firestoreModule.where;
  orderBy = firestoreModule.orderBy;
  limit = firestoreModule.limit;
  startAfter = firestoreModule.startAfter;
  Timestamp = firestoreModule.Timestamp;
  onSnapshot = firestoreModule.onSnapshot;
}

export {
  auth, db, collection, addDoc, getDocs, getDoc, doc, updateDoc, deleteDoc,
  query, where, orderBy, limit, startAfter, Timestamp, onSnapshot
};
```

#### Example 7.2: Environment Configuration

```bash
# .env.development
VITE_USE_MOCK_FIRESTORE=true
VITE_FIREBASE_API_KEY=mock-api-key

# .env.production
VITE_USE_MOCK_FIRESTORE=false
VITE_FIREBASE_API_KEY=actual-api-key
VITE_FIREBASE_AUTH_DOMAIN=kartlog.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=kartlog
```

### Category 8: Error Handling

#### Example 8.1: Comprehensive Error Handling

```javascript
import { FirebaseError } from 'firebase/app';

export async function addSessionWithErrorHandling(sessionData) {
  try {
    if (!auth.currentUser) {
      throw new Error('UNAUTHENTICATED: User must be logged in');
    }

    // Validate required fields
    if (!sessionData.date) {
      throw new Error('VALIDATION_ERROR: Session date is required');
    }

    const processedData = {
      userId: auth.currentUser.uid,
      date: new Date(sessionData.date),
      // ... other fields
      createdAt: new Date()
    };

    const docRef = await addDoc(collection(db, 'sessions'), processedData);
    return { success: true, id: docRef.id };

  } catch (error) {
    console.error('Error adding session:', error);

    if (error instanceof FirebaseError) {
      switch (error.code) {
        case 'permission-denied':
          return { success: false, error: 'Permission denied. Check security rules.' };
        case 'unavailable':
          return { success: false, error: 'Firestore is temporarily unavailable. Try again.' };
        case 'quota-exceeded':
          return { success: false, error: 'Storage quota exceeded.' };
        default:
          return { success: false, error: `Firestore error: ${error.code}` };
      }
    }

    if (error.message.startsWith('VALIDATION_ERROR')) {
      return { success: false, error: error.message.replace('VALIDATION_ERROR: ', '') };
    }

    if (error.message.startsWith('UNAUTHENTICATED')) {
      return { success: false, error: 'Please log in to continue.' };
    }

    return { success: false, error: 'An unexpected error occurred.' };
  }
}
```

#### Example 8.2: Retry Logic

```javascript
// Retry helper for transient failures
async function retryOperation(operation, maxRetries = 3, delay = 1000) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      if (attempt === maxRetries) throw error;

      // Only retry on transient errors
      if (error instanceof FirebaseError &&
          (error.code === 'unavailable' || error.code === 'deadline-exceeded')) {
        console.log(`Retry attempt ${attempt}/${maxRetries} after ${delay}ms`);
        await new Promise(resolve => setTimeout(resolve, delay));
        delay *= 2; // Exponential backoff
      } else {
        throw error; // Don't retry non-transient errors
      }
    }
  }
}

// Usage
export async function getUserSessionsWithRetry() {
  return await retryOperation(async () => {
    return await getUserSessions();
  });
}
```

---

## Best Practices

### 1. Always Guard with Authentication

**Why**: Prevent unauthorized data access and ensure data isolation between users.

```javascript
// GOOD: Check authentication before any operation
export const getUserData = async () => {
  if (!auth.currentUser) {
    throw new Error('User must be logged in');
  }
  // ... proceed with operation
};

// BAD: No authentication check
export const getUserData = async () => {
  const q = query(collection(db, 'data'));
  // Exposes all users' data!
};
```

### 2. Always Filter by User ID

**Why**: Security rules may allow read, but client should never fetch all users' data.

```javascript
// GOOD: User-scoped query
const q = query(
  collection(db, 'sessions'),
  where('userId', '==', auth.currentUser.uid)
);

// BAD: Fetches all documents
const q = query(collection(db, 'sessions'));
```

### 3. Coerce All Numeric Input

**Why**: Prevent type inconsistencies that break charts and calculations.

```javascript
// GOOD: Safe numeric conversion
const temp = parseFloat(sessionData.temp) || null;

// BAD: Direct assignment can store strings
const temp = sessionData.temp; // Could be "25" instead of 25
```

### 4. Return Document ID with Data

**Why**: Enable updates and deletes without re-querying.

```javascript
// GOOD: Include document ID
return querySnapshot.docs.map(doc => ({
  id: doc.id,
  ...doc.data()
}));

// BAD: Only return data
return querySnapshot.docs.map(doc => doc.data());
```

### 5. Use Lookup Maps for Joins

**Why**: O(1) lookups are far more efficient than nested loops.

```javascript
// GOOD: O(n + m) complexity with Map
const tyresMap = new Map(tyres.map(t => [t.id, t]));
return sessions.map(s => ({
  ...s,
  tyre: tyresMap.get(s.tyreId)
}));

// BAD: O(n * m) complexity with find
return sessions.map(s => ({
  ...s,
  tyre: tyres.find(t => t.id === s.tyreId)
}));
```

### 6. Debounce Listener Refreshes

**Why**: Prevent UI flicker and excessive re-renders from rapid changes.

```javascript
// GOOD: Debounced refresh
let refreshTimeout = null;
const debouncedRefresh = () => {
  if (refreshTimeout) clearTimeout(refreshTimeout);
  refreshTimeout = setTimeout(() => refreshDatabase(), 500);
};

// BAD: Immediate refresh on every change
onSnapshot(q, () => refreshDatabase());
```

### 7. Clean Up Listeners

**Why**: Prevent memory leaks and orphaned listeners.

```javascript
// GOOD: Track and clean up
const unsubscribe = onSnapshot(q, callback);
return () => unsubscribe(); // Cleanup function

// BAD: No cleanup
onSnapshot(q, callback);
```

### 8. Respect Batch Limits

**Why**: Firestore batch operations have a hard limit of 500 documents.

```javascript
// GOOD: Chunk into batches of 500
const batchSize = 500;
for (let i = 0; i < docs.length; i += batchSize) {
  const batch = db.batch();
  docs.slice(i, i + batchSize).forEach(doc => batch.set(doc.ref, doc.data));
  await batch.commit();
}

// BAD: Attempt to batch 1000 documents
const batch = db.batch();
docs.forEach(doc => batch.set(doc.ref, doc.data)); // Will fail!
await batch.commit();
```

### 9. Validate Ownership on Read

**Why**: Security rules may allow read, but client should verify ownership.

```javascript
// GOOD: Verify userId matches
const docSnap = await getDoc(docRef);
if (docSnap.data().userId !== auth.currentUser.uid) {
  throw new Error('Unauthorized access');
}

// BAD: Assume document belongs to user
const docSnap = await getDoc(docRef);
return docSnap.data();
```

### 10. Use Soft Deletes for Equipment

**Why**: Preserve historical session data that references deleted equipment.

```javascript
// GOOD: Soft delete with flag
export const retireTyre = async (tyreId) => {
  await updateDoc(doc(db, 'tyres', tyreId), {
    isRetired: true,
    retiredAt: new Date()
  });
};

// BAD: Hard delete breaks session joins
export const deleteTyre = async (tyreId) => {
  await deleteDoc(doc(db, 'tyres', tyreId));
  // Now session.tyreId references non-existent document!
};
```

---

## Anti-Patterns

### Anti-Pattern 1: Fetching All Documents

```javascript
// WRONG: Fetches all users' data
const querySnapshot = await getDocs(collection(db, 'sessions'));

// CORRECT: User-scoped query
const q = query(
  collection(db, 'sessions'),
  where('userId', '==', auth.currentUser.uid)
);
const querySnapshot = await getDocs(q);
```

### Anti-Pattern 2: No Type Coercion

```javascript
// WRONG: Stores mixed types
const session = {
  temp: sessionData.temp, // Could be "25" or 25
  humidity: sessionData.humidity // Could be "60" or 60
};

// CORRECT: Consistent types
const session = {
  temp: parseFloat(sessionData.temp) || null,
  humidity: parseFloat(sessionData.humidity) || null
};
```

### Anti-Pattern 3: Nested Loop Joins

```javascript
// WRONG: O(n * m) complexity
sessions.map(session => ({
  ...session,
  tyre: tyres.find(t => t.id === session.tyreId)
}));

// CORRECT: O(n + m) with Map
const tyresMap = new Map(tyres.map(t => [t.id, t]));
sessions.map(session => ({
  ...session,
  tyre: tyresMap.get(session.tyreId)
}));
```

### Anti-Pattern 4: Ignoring Listener Cleanup

```javascript
// WRONG: Memory leak
function MyComponent() {
  useEffect(() => {
    onSnapshot(q, (snapshot) => {
      setData(snapshot.docs);
    });
  }, []); // No cleanup!
}

// CORRECT: Return cleanup function
function MyComponent() {
  useEffect(() => {
    const unsubscribe = onSnapshot(q, (snapshot) => {
      setData(snapshot.docs);
    });
    return () => unsubscribe();
  }, []);
}
```

### Anti-Pattern 5: Hardcoding Collection Names

```javascript
// WRONG: Repeated hardcoded strings
await addDoc(collection(db, 'sessions'), data);
await getDocs(query(collection(db, 'sessions'), ...));

// CORRECT: Constants
const COLLECTIONS = {
  SESSIONS: 'sessions',
  TYRES: 'tyres',
  ENGINES: 'engines'
};

await addDoc(collection(db, COLLECTIONS.SESSIONS), data);
```

### Anti-Pattern 6: Updating Immutable Fields

```javascript
// WRONG: Allows changing userId and createdAt
export const updateSession = async (sessionId, updates) => {
  await updateDoc(doc(db, 'sessions', sessionId), updates);
};

// CORRECT: Remove immutable fields
export const updateSession = async (sessionId, updates) => {
  const cleanUpdates = { ...updates };
  delete cleanUpdates.userId;
  delete cleanUpdates.createdAt;
  delete cleanUpdates.id;
  cleanUpdates.updatedAt = new Date();

  await updateDoc(doc(db, 'sessions', sessionId), cleanUpdates);
};
```

### Anti-Pattern 7: No Error Handling

```javascript
// WRONG: Unhandled promise rejection
export const addSession = async (data) => {
  return await addDoc(collection(db, 'sessions'), data);
};

// CORRECT: Comprehensive error handling
export const addSession = async (data) => {
  try {
    if (!auth.currentUser) {
      throw new Error('User must be logged in');
    }
    return await addDoc(collection(db, 'sessions'), data);
  } catch (error) {
    console.error('Error adding session:', error);
    throw error;
  }
};
```

### Anti-Pattern 8: Firestore Query Joins

```javascript
// WRONG: Firestore doesn't support SQL-like joins
const q = query(
  collection(db, 'sessions'),
  where('userId', '==', userId),
  // Can't join to tyres collection here!
);

// CORRECT: Client-side joins
const sessions = await getUserSessions();
const tyres = await getUserTyres();
const joined = sessions.map(s => ({
  ...s,
  tyre: tyres.find(t => t.id === s.tyreId)
}));
```

---

## Technology-Specific Guidance

### Firestore Query Limitations

1. **Inequality filters**: Can only use inequality (<, <=, >, >=) on one field
2. **OR queries**: Not supported (must make multiple queries)
3. **Array membership**: Use `array-contains` for single value, `array-contains-any` for multiple
4. **Case-insensitive search**: Not supported (denormalize to lowercase field)
5. **Full-text search**: Not supported (use Algolia or similar)

### Firestore Indexing

**Composite indexes required for**:
- Queries with multiple orderBy clauses
- Queries with inequality and orderBy on different fields
- Queries with multiple array-contains filters

Firestore will show error with index creation link on first attempt.

### Security Rules Patterns

```javascript
// firestore.rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Helper functions
    function isAuthenticated() {
      return request.auth != null;
    }

    function isOwner(userId) {
      return request.auth.uid == userId;
    }

    // Sessions collection
    match /sessions/{sessionId} {
      allow read: if isAuthenticated() && isOwner(resource.data.userId);
      allow create: if isAuthenticated() && isOwner(request.resource.data.userId);
      allow update, delete: if isAuthenticated() && isOwner(resource.data.userId);
    }

    // Equipment collections (tyres, engines, chassis)
    match /{equipment}/{equipmentId} {
      allow read: if isAuthenticated() && isOwner(resource.data.userId);
      allow create: if isAuthenticated() && isOwner(request.resource.data.userId);
      allow update, delete: if isAuthenticated() && isOwner(resource.data.userId);
    }
  }
}
```

### Firebase Admin SDK vs Client SDK

**Use Admin SDK when**:
- Running server-side code (Node.js)
- Need elevated privileges (bypassing security rules)
- Batch operations > 500 documents
- Bulk import/export operations

**Use Client SDK when**:
- Running in browser/mobile app
- User-scoped operations
- Real-time listeners
- Authentication integration

### Pagination Best Practices

```javascript
// Cursor-based pagination (recommended)
export const getSessionsPage = async (pageSize = 20, lastVisible = null) => {
  let q = query(
    collection(db, 'sessions'),
    where('userId', '==', auth.currentUser.uid),
    orderBy('date', 'desc'),
    limit(pageSize)
  );

  if (lastVisible) {
    q = query(q, startAfter(lastVisible));
  }

  const snapshot = await getDocs(q);
  return {
    sessions: snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })),
    lastVisible: snapshot.docs[snapshot.docs.length - 1]
  };
};

// Offset-based pagination (NOT recommended - inefficient)
// Firestore charges for all skipped documents!
```

---

## Troubleshooting

### Issue 1: Permission Denied Errors

**Symptoms**: `FirebaseError: Missing or insufficient permissions`

**Causes**:
1. Security rules don't allow operation
2. User not authenticated
3. Document userId doesn't match auth.currentUser.uid

**Solutions**:
```javascript
// Check authentication
if (!auth.currentUser) {
  console.error('User not authenticated');
  return;
}

// Verify security rules
// firestore.rules should have:
match /sessions/{sessionId} {
  allow read, write: if request.auth.uid == resource.data.userId;
}

// Check userId on document
const docSnap = await getDoc(docRef);
console.log('Document userId:', docSnap.data().userId);
console.log('Current user:', auth.currentUser.uid);
```

### Issue 2: Query Requires Index

**Symptoms**: `FirebaseError: The query requires an index`

**Solution**: Click the link in error message to create index in Firebase Console, or add to firestore.indexes.json:

```json
{
  "indexes": [
    {
      "collectionGroup": "sessions",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "userId", "order": "ASCENDING" },
        { "fieldPath": "date", "order": "DESCENDING" }
      ]
    }
  ]
}
```

### Issue 3: Listener Not Triggering

**Symptoms**: onSnapshot callback never fires on changes

**Causes**:
1. Security rules deny read access
2. Query filters exclude changed documents
3. Listener was unsubscribed

**Debug**:
```javascript
const unsubscribe = onSnapshot(
  q,
  (snapshot) => {
    console.log('Snapshot received:', snapshot.size);
    snapshot.docChanges().forEach(change => {
      console.log(`${change.type}:`, change.doc.id);
    });
  },
  (error) => {
    console.error('Listener error:', error);
  }
);
```

### Issue 4: Slow Queries

**Symptoms**: Queries taking multiple seconds

**Causes**:
1. Missing indexes
2. Fetching too many documents
3. Not using where clause to filter

**Solutions**:
```javascript
// Add indexes for compound queries
// Limit result size
const q = query(
  collection(db, 'sessions'),
  where('userId', '==', auth.currentUser.uid),
  orderBy('date', 'desc'),
  limit(50) // Don't fetch everything!
);

// Use pagination for large datasets
```

### Issue 5: Timestamp Serialization Errors

**Symptoms**: `Cannot stringify Firestore Timestamp`

**Solution**: Convert to Date before JSON.stringify:
```javascript
function serializeDoc(doc) {
  const data = doc.data();
  Object.keys(data).forEach(key => {
    if (data[key] && typeof data[key] === 'object' && data[key].seconds) {
      data[key] = new Date(data[key].seconds * 1000);
    }
  });
  return data;
}
```

### Issue 6: Mock/Real Switching Not Working

**Symptoms**: Using real Firebase when VITE_USE_MOCK_FIRESTORE=true

**Causes**:
1. Environment variable not loaded
2. Vite server not restarted after .env change

**Solutions**:
```javascript
// Debug environment loading
console.log('Mock env var:', import.meta.env.VITE_USE_MOCK_FIRESTORE);
console.log('All env:', import.meta.env);

// Restart Vite dev server
// npm run dev
```

---

## Related Templates

### Primary Templates

1. **sessions.js.template**
   - Path: `templates/firebase/sessions.js.template`
   - Purpose: Complete CRUD service for karting sessions
   - Key Patterns: Auth guards, type coercion, optional joins, date handling
   - Technologies: Firebase Firestore, JavaScript

2. **firebase.js.template**
   - Path: `templates/firebase/firebase.js.template`
   - Purpose: Centralized Firebase module with mock/real switching
   - Key Patterns: Environment-based imports, unified exports
   - Technologies: Firebase, Vite environment variables

3. **databaseListeners.js.template**
   - Path: `templates/firebase/databaseListeners.js.template`
   - Purpose: Real-time Firestore listeners with lifecycle management
   - Key Patterns: onSnapshot, debouncing, cleanup
   - Technologies: Firebase Firestore real-time updates

### Secondary Templates

4. **upload-sessions.js.template**
   - Path: `templates/firebase/upload-sessions.js.template`
   - Purpose: Batch import using Firebase Admin SDK
   - Key Patterns: CSV parsing, batch writes, progress tracking
   - Technologies: Firebase Admin SDK, Node.js

5. **query.js.template**
   - Path: `templates/firebase/query.js.template`
   - Purpose: Firestore to SQL bridge for analytics
   - Key Patterns: Timestamp flattening, data export
   - Technologies: Firebase Firestore, SQL databases

6. **tyres.js.template, engines.js.template, chassis.js.template**
   - Path: `templates/firebase/equipment/*.js.template`
   - Purpose: Equipment-specific CRUD services
   - Key Patterns: Soft deletes (isRetired flag), purchase date tracking
   - Technologies: Firebase Firestore

### Integration Examples

**React Hook Integration**:
```javascript
import { getUserSessions } from '../services/firebase/sessions.js';
import { useEffect, useState } from 'react';

export function useSessions(join = false) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getUserSessions(join)
      .then(setSessions)
      .finally(() => setLoading(false));
  }, [join]);

  return { sessions, loading };
}
```

**Authentication Integration**:
```javascript
import { auth } from '../services/firebase/firebase.js';
import { onAuthStateChanged } from 'firebase/auth';

onAuthStateChanged(auth, (user) => {
  if (user) {
    startDatabaseListeners();
  } else {
    stopDatabaseListeners();
  }
});
```

---

## Appendix: Firestore Data Model

### Collections Structure

```
firestore/
├── sessions/
│   └── {sessionId}
│       ├── userId: string
│       ├── date: Timestamp
│       ├── temp: number | null
│       ├── humidity: number | null
│       ├── pressure: number | null
│       ├── trackCondition: string
│       ├── tyreId: string | null
│       ├── engineId: string | null
│       ├── chassisId: string | null
│       ├── trackId: string | null
│       ├── notes: string
│       ├── bestLapTime: number | null
│       ├── createdAt: Timestamp
│       └── updatedAt: Timestamp
│
├── tyres/
│   └── {tyreId}
│       ├── userId: string
│       ├── manufacturer: string
│       ├── model: string
│       ├── compound: string
│       ├── purchaseDate: Timestamp
│       ├── isRetired: boolean
│       ├── retiredAt: Timestamp | null
│       ├── createdAt: Timestamp
│       └── updatedAt: Timestamp
│
├── engines/
│   └── {engineId}
│       ├── userId: string
│       ├── manufacturer: string
│       ├── model: string
│       ├── purchaseDate: Timestamp
│       ├── isRetired: boolean
│       └── ...
│
├── chassis/
│   └── {chassisId}
│       ├── userId: string
│       ├── manufacturer: string
│       ├── model: string
│       └── ...
│
└── tracks/
    └── {trackId}
        ├── userId: string
        ├── name: string
        ├── location: string
        └── ...
```

### Field Type Reference

- `userId`: string (auth.currentUser.uid)
- `date`, `createdAt`, `updatedAt`: Firestore Timestamp
- `temp`, `humidity`, `pressure`, `bestLapTime`: number | null
- `trackCondition`: string enum ('dry', 'wet', 'damp')
- `isRetired`: boolean
- `notes`: string
- Foreign keys (`tyreId`, `engineId`, etc.): string | null

---

**End of Extended Reference**
