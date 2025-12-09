# Svelte5 Component Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **svelte5-component-specialist** agent.

**Core documentation**: See [svelte5-component-specialist.md](./svelte5-component-specialist.md)

---

## Related Templates

### Primary Component Templates

- **`templates/presentation layer/routes/NewSession.svelte.template`** - Demonstrates form handling, SMUI integration, async data loading, validation patterns, and router navigation for creating new entities

- **`templates/presentation layer/routes/Sessions.svelte.template`** - Shows data table rendering, reactive filtering, keyed each blocks, conditional rendering, and row interaction patterns

- **`templates/presentation layer/routes/Dashboard.svelte.template`** - Illustrates complex state management, Promise.all async patterns, derived reactive statements, and multi-component composition

- **`templates/presentation layer/components/Navigation.svelte.template`** - Demonstrates global navigation patterns, router link integration, responsive design, and mobile menu handling

- **`templates/presentation layer/routes/EditSession.svelte.template`** - Shows entity loading by ID, pre-population of forms, update operations, and error handling for edit workflows

### Supporting Templates

- **`templates/presentation layer/components/SessionsTable.svelte.template`** - Reusable data table component with props, event handling, and SMUI DataTable integration

- **`templates/presentation layer/src/App.svelte.template`** - Root application structure, router configuration, and global layout patterns

## Code Examples

### Example 1: Component Structure with Reactive State

**DO**: Use the standard SFC structure with script, template, and scoped styles

```svelte
<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import Button from '@smui/button';
  import Textfield from '@smui/textfield';
  import Select, { Option } from '@smui/select';
  
  // Props using export let
  export let params = {};
  
  // Component state with let bindings
  let sessionName = '';
  let circuitId = '';
  let loading = false;
  let error = '';
  let tracks = [];
  
  // Derived state using reactive statements
  $: isFormValid = sessionName.trim() && circuitId;
  $: sortedTracks = [...tracks].sort((a, b) => a.name.localeCompare(b.name));
  
  const loadTracks = async () => {
    try {
      loading = true;
      tracks = await getUserTracks();
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  };
  
  onMount(loadTracks);
</script>

<div class="container">
  <Select bind:value={circuitId} label="Circuit" required style="width: 100%;">
    {#each sortedTracks as track (track.id)}
      <Option value={track.id}>{track.name}</Option>
    {/each}
  </Select>
</div>

<style>
  .container {
    padding: 20px;
    max-width: 800px;
  }
</style>
```

**DON'T**: Mix concerns or use inline event handlers without proper binding

```svelte
<!-- WRONG: No script/style separation, missing reactivity -->
<select value={circuitId}>
  <option>Track 1</option>
</select>
<script>
let circuitId;
// No reactive updates, no SMUI components
</script>
```

### Example 2: Form Handling with Validation

**DO**: Use two-way binding, prevent default, and handle async submission

```svelte
<script>
  import Textfield from '@smui/textfield';
  import Checkbox from '@smui/checkbox';
  import FormField from '@smui/form-field';
  import Button from '@smui/button';
  import { push } from 'svelte-spa-router';
  
  let session = '';
  let date = '';
  let isRace = false;
  let racePosition = '';
  let submitting = false;
  let error = '';
  
  // Conditional validation
  $: isValid = session.trim() && date && (!isRace || racePosition);
  
  const handleSubmit = async () => {
    if (!isValid) return;
    
    try {
      submitting = true;
      error = '';
      
      await createSession({
        session,
        date: new Date(date),
        isRace,
        ...(isRace && { racePosition: parseInt(racePosition) })
      });
      
      push('/sessions');
    } catch (err) {
      error = err.message;
    } finally {
      submitting = false;
    }
  };
</script>

<form on:submit|preventDefault={handleSubmit}>
  <Textfield bind:value={session} label="Session Name" required style="width: 100%;" />
  
  <FormField>
    <Checkbox bind:checked={isRace} />
    {#snippet label()}
      Race Session
    {/snippet}
  </FormField>
  
  {#if isRace}
    <Textfield bind:value={racePosition} label="Position" type="number" style="width: 100%;" />
  {/if}
  
  {#if error}
    <div class="error">{error}</div>
  {/if}
  
  <Button type="submit" variant="raised" disabled={!isValid || submitting}>
    {submitting ? 'Saving...' : 'Create Session'}
  </Button>
</form>
```

**DON'T**: Use uncontrolled inputs or skip validation

```svelte
<!-- WRONG: No binding, no validation, no error handling -->
<form onsubmit="createSession()">
  <input type="text" name="session" />
  <button type="submit">Submit</button>
</form>
```

### Example 3: Data Table with Sorting and Navigation

**DO**: Use keyed each blocks, reactive sorting, and accessible row actions

```svelte
<script>
  import DataTable, { Head, Body, Row, Cell } from '@smui/data-table';
  import { push } from 'svelte-spa-router';
  
  export let sessions = [];
  
  let sortColumn = 'date';
  let sortDirection = 'desc';
  
  $: sortedSessions = sessions.length > 0
    ? [...sessions].sort((a, b) => {
        const dateA = a.date.toDate ? a.date.toDate() : new Date(a.date);
        const dateB = b.date.toDate ? b.date.toDate() : new Date(b.date);
        return sortDirection === 'desc' ? dateB - dateA : dateA - dateB;
      })
    : [];
  
  const handleRowClick = (sessionId) => {
    push(`/sessions/${sessionId}`);
  };
</script>

<DataTable style="width: 100%;">
  <Head>
    <Row>
      <Cell>Date</Cell>
      <Cell>Circuit</Cell>
      <Cell>Session</Cell>
    </Row>
  </Head>
  <Body>
    {#each sortedSessions as session (session.id)}
      <Row 
        on:click={() => handleRowClick(session.id)}
        on:keydown={(e) => e.key === 'Enter' && handleRowClick(session.id)}
        tabindex="0"
        role="button"
        class="clickable-row"
      >
        <Cell>{session.date}</Cell>
        <Cell>{session.circuitName}</Cell>
        <Cell>{session.session}</Cell>
      </Row>
    {/each}
  </Body>
</DataTable>

<style>
  :global(.clickable-row) {
    cursor: pointer;
  }
  :global(.clickable-row:hover) {
    background-color: rgba(0, 0, 0, 0.04);
  }
</style>
```

**DON'T**: Use index as key or ignore accessibility

```svelte
<!-- WRONG: Index key, no keyboard support, inline sorting -->
{#each sessions as session, i}
  <div onclick="goto(session.id)">{session.name}</div>
{/each}
```

### Example 4: Async Data Loading Pattern

**DO**: Use Promise.all for parallel loading, proper error handling, and loading states

```svelte
<script>
  import { onMount } from 'svelte';
  import CircularProgress from '@smui/circular-progress';
  
  let tyres = [];
  let tracks = [];
  let engines = [];
  let loading = false;
  let error = '';
  
  $: activeTyres = tyres.filter(t => !t.retired).length;
  $: totalMileage = tracks.reduce((sum, t) => sum + (t.mileage || 0), 0);
  
  const loadData = async () => {
    try {
      loading = true;
      error = '';
      
      const [tyresData, tracksData, enginesData] = await Promise.all([
        getUserTyres(),
        getUserTracks(),
        getUserEngines()
      ]);
      
      tyres = tyresData;
      tracks = tracksData;
      engines = enginesData;
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  };
  
  onMount(loadData);
</script>

{#if loading}
  <div class="loading-container">
    <CircularProgress indeterminate />
  </div>
{:else if error}
  <div class="error">{error}</div>
{:else}
  <div class="dashboard">
    <p>Active Tyres: {activeTyres}</p>
    <p>Total Mileage: {totalMileage} km</p>
  </div>
{/if}
```

**DON'T**: Load sequentially or skip error states

```svelte
<!-- WRONG: Sequential loading, no error handling -->
<script>
  onMount(async () => {
    tyres = await getUserTyres();
    tracks = await getUserTracks(); // Waits for tyres unnecessarily
  });
</script>
```

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
