# form-validation-specialist - Extended Reference

This file contains detailed documentation for the `form-validation-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/form-validation-specialist-ext.md
```


## Code Patterns

### Schema Definition
```typescript
import { z } from 'zod';

export const createEntityInputSchema = z.object({
  title: z.string().min(1, 'Required'),
  body: z.string().min(1, 'Required'),
  email: z.string().email('Invalid email'),
  age: z.number().min(18, 'Must be 18 or older'),
});

export type CreateEntityInput = z.infer<typeof createEntityInputSchema>;
```

### Form with React Hook Form
```typescript
import { Form, Input, Textarea } from '@/components/ui/form';
import { createEntityInputSchema, useCreateEntity } from '../api/create-entity';

export const CreateEntity = () => {
  const createMutation = useCreateEntity();

  return (
    <Form
      id="create-entity"
      onSubmit={(values) => {
        createMutation.mutate({ data: values });
      }}
      schema={createEntityInputSchema}
    >
      {({ register, formState }) => (
        <>
          <Input
            label="Title"
            error={formState.errors['title']}
            registration={register('title')}
          />
          <Textarea
            label="Body"
            error={formState.errors['body']}
            registration={register('body')}
          />
        </>
      )}
    </Form>
  );
};
```

### Form with Default Values
```typescript
<Form
  id="update-entity"
  onSubmit={(values) => {
    updateMutation.mutate({ data: values, id });
  }}
  options={{
    defaultValues: {
      title: entity?.title ?? '',
      body: entity?.body ?? '',
    },
  }}
  schema={updateEntityInputSchema}
>
  {({ register, formState }) => (
    // Form fields...
  )}
</Form>
```

### Form in Drawer/Modal
```typescript
import { FormDrawer } from '@/components/ui/form';
import { Button } from '@/components/ui/button';

<FormDrawer
  isDone={createMutation.isSuccess}
  triggerButton={
    <Button size="sm" icon={<Plus className="size-4" />}>
      Create Entity
    </Button>
  }
  title="Create Entity"
  submitButton={
    <Button
      form="create-entity"
      type="submit"
      size="sm"
      isLoading={createMutation.isPending}
    >
      Submit
    </Button>
  }
>
  <Form id="create-entity" {...formProps}>
    {/* Form fields */}
  </Form>
</FormDrawer>
```

### 1. Schema Organization
- Define schemas in API layer (co-located with mutations)
- Export schema and inferred type
- Keep schemas focused (one per operation)
- Use descriptive error messages

### 2. Validation Rules
- **Required fields**: Use `.min(1, 'Required')` for strings
- **Email**: Use `.email('Invalid email')`
- **Numbers**: Use `.number()` with `.min()` / `.max()`
- **Custom**: Use `.refine()` for complex validation
- **Optional**: Use `.optional()` for optional fields

### 3. Error Display
- Always pass `error` prop to form components
- Error messages should be user-friendly
- Show errors inline with fields
- Use proper ARIA attributes for accessibility

### 4. Form Submission
- Disable submit button during submission (isLoading)
- Show success notification after successful submission
- Handle errors with user-friendly messages
- Reset form or close drawer/modal on success

### 5. Type Safety
- Always infer types from schemas using `z.infer<typeof schema>`
- Don't duplicate type definitions
- Leverage TypeScript for autocomplete and type checking


## Anti-Patterns to Avoid

1. ❌ Duplicating validation in schema and component
2. ❌ Not handling loading states during submission
3. ❌ Not showing error messages to users
4. ❌ Manually managing form state (let React Hook Form handle it)
5. ❌ Not using type inference from Zod schemas
6. ❌ Forgetting to reset form or close modal on success


## Advanced Patterns

### Conditional Validation
```typescript
const schema = z.object({
  type: z.enum(['personal', 'business']),
  companyName: z.string(),
}).refine(
  (data) => {
    if (data.type === 'business') {
      return data.companyName.length > 0;
    }
    return true;
  },
  {
    message: 'Company name is required for business accounts',
    path: ['companyName'],
  }
);
```

### Async Validation
```typescript
const schema = z.object({
  username: z.string().refine(
    async (username) => {
      const available = await checkUsernameAvailability(username);
      return available;
    },
    { message: 'Username is already taken' }
  ),
});
```

### Nested Objects
```typescript
const schema = z.object({
  user: z.object({
    name: z.string().min(1, 'Required'),
    email: z.string().email('Invalid email'),
  }),
  address: z.object({
    street: z.string().min(1, 'Required'),
    city: z.string().min(1, 'Required'),
  }),
});
```


## Technology Stack Context
- React Hook Form v7.51+
- Zod v3.23+
- TypeScript 5.4+ (for type inference)
- Custom Form components (@/components/ui/form)


## Example Implementation

See template files:
- `templates/api/create-entity.ts.template` - Schema + mutation
- `templates/api/update-entity.ts.template` - Schema + mutation
- `templates/components/create-entity.tsx.template` - Form implementation
- `templates/components/update-entity.tsx.template` - Form with defaults


## Related Templates

### Primary Templates
- **templates/api/create-entity.ts.template** - Zod schema definition + mutation with type inference pattern
- **templates/components/create-entity.tsx.template** - Complete form component with FormDrawer, validation, and error handling
- **templates/components/update-entity.tsx.template** - Update form with `defaultValues` pattern for pre-populated fields

### Supporting Templates
- **templates/api/update-entity.ts.template** - Update schema pattern with entity ID handling


## Code Examples from Templates

### Example 1: Schema Definition with Type Inference

```typescript
// ✅ DO: Define schema with validation, infer types
import { z } from 'zod';

export const createTaskSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string().optional(),
  dueDate: z.date().optional(),
  priority: z.enum(['low', 'medium', 'high']),
});

export type CreateTaskInput = z.infer<typeof createTaskSchema>;

// ❌ DON'T: Duplicate type definitions
interface CreateTaskInput {  // ← Duplicate! Use z.infer instead
  title: string;
  description?: string;
  dueDate?: Date;
  priority: 'low' | 'medium' | 'high';
}
```

**Pattern**: Schema-first approach where types are derived from validation rules, not vice versa.

### Example 2: Form Component with Validation

```typescript
// ✅ DO: Complete form with validation integration
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

export function CreateTaskForm({ onSuccess }: { onSuccess?: () => void }) {
  const { register, handleSubmit, formState: { errors } } = useForm<CreateTaskInput>({
    resolver: zodResolver(createTaskSchema),
  });

  const mutation = useCreateTask();

  const onSubmit = (data: CreateTaskInput) => {
    mutation.mutate(data, {
      onSuccess: () => {
        toast.success('Task created successfully');
        onSuccess?.();
      },
    });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div>
        <Input {...register('title')} placeholder="Task title" />
        {errors.title && (
          <span className="text-red-500 text-sm">{errors.title.message}</span>
        )}
      </div>

      <div>
        <Select {...register('priority')}>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </Select>
        {errors.priority && (
          <span className="text-red-500 text-sm">{errors.priority.message}</span>
        )}
      </div>

      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? 'Creating...' : 'Create Task'}
      </Button>
    </form>
  );
}

// ❌ DON'T: Skip error display or loading states
export function BadForm() {
  const { register, handleSubmit } = useForm();  // ← No zodResolver
  const mutation = useCreateTask();

  return (
    <form onSubmit={handleSubmit((data) => mutation.mutate(data))}>
      <Input {...register('title')} />  {/* ← No error display */}
      <Button type="submit">Create</Button>  {/* ← No loading state */}
    </form>
  );
}
```

**Pattern**: `zodResolver` connects schema validation to React Hook Form, `formState.errors` provides field-level error messages.

### Example 3: Update Form with Default Values

```typescript
// ✅ DO: Pre-populate form with existing data
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

export function UpdateTaskForm({ taskId }: { taskId: string }) {
  const { data: task } = useGetTask(taskId);

  const { register, handleSubmit, formState: { errors } } = useForm<UpdateTaskInput>({
    resolver: zodResolver(updateTaskSchema),
    defaultValues: {
      title: task?.title ?? '',
      description: task?.description ?? '',
      priority: task?.priority ?? 'medium',
    },
  });

  const mutation = useUpdateTask();

  return (
    <form onSubmit={handleSubmit((data) => mutation.mutate({ id: taskId, ...data }))}>
      <Input {...register('title')} />
      {errors.title && <span className="text-red-500">{errors.title.message}</span>}

      <Button type="submit" disabled={mutation.isPending}>Update Task</Button>
    </form>
  );
}

// ❌ DON'T: Forget to set default values for update forms
export function BadUpdateForm({ taskId }: { taskId: string }) {
  const { register, handleSubmit } = useForm();  // ← No defaultValues
  // User sees empty form even though editing existing task
}
```

**Pattern**: Use `defaultValues` option in `useForm()` to pre-fill fields when editing existing entities.

### Example 4: FormDrawer Modal Pattern

```typescript
// ✅ DO: Wrap form in modal with proper state management
import { FormDrawer } from '@/components/ui/form-drawer';

export function CreateTaskDrawer() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setOpen(true)}>Create Task</Button>

      <FormDrawer
        open={open}
        onOpenChange={setOpen}
        title="Create New Task"
        description="Add a new task to your project"
      >
        <CreateTaskForm onSuccess={() => setOpen(false)} />
      </FormDrawer>
    </>
  );
}

// ❌ DON'T: Forget to close modal on success
export function BadDrawer() {
  const [open, setOpen] = useState(false);

  return (
    <FormDrawer open={open} onOpenChange={setOpen} title="Create Task">
      <CreateTaskForm />  {/* ← No onSuccess callback to close modal */}
    </FormDrawer>
  );
}
```

**Pattern**: FormDrawer manages modal state, form calls `onSuccess` callback to close drawer after successful submission.


## Additional Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: Manual Validation Logic

```typescript
// ❌ DON'T: Write custom validation in component
function BadForm() {
  const [errors, setErrors] = useState({});

  const handleSubmit = (e) => {
    e.preventDefault();
    const data = new FormData(e.target);
    const title = data.get('title');

    // Manual validation - loses type safety and centralizes poorly
    if (!title || title.length < 1) {
      setErrors({ title: 'Required' });
      return;
    }

    // Submit logic...
  };
}

// ✅ DO: Use Zod schema + zodResolver
function GoodForm() {
  const schema = z.object({ title: z.string().min(1, 'Required') });
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
  });
}
```

### ❌ Anti-Pattern 2: Missing Type Coercion

```typescript
// ❌ DON'T: Let numeric inputs remain strings
<Input type="number" {...register('price')} />
// Result: data.price is "42" (string), not 42 (number)

// ✅ DO: Use valueAsNumber for numeric inputs
<Input type="number" {...register('price', { valueAsNumber: true })} />
// Result: data.price is 42 (number)
```

### ❌ Anti-Pattern 3: No Loading States

```typescript
// ❌ DON'T: Allow form interaction during submission
<Button type="submit">Submit</Button>

// ✅ DO: Disable during async operations
<Button type="submit" disabled={mutation.isPending}>
  {mutation.isPending ? 'Submitting...' : 'Submit'}
</Button>
```

### ❌ Anti-Pattern 4: Ignoring Error Messages

```typescript
// ❌ DON'T: Register fields without displaying errors
<Input {...register('email')} />

// ✅ DO: Always display validation errors
<Input {...register('email')} />
{errors.email && <span className="text-red-500">{errors.email.message}</span>}
```


## Performance Optimization

### Validation Mode

```typescript
// Default: validate on submit
useForm({ mode: 'onSubmit' })

// Validate on blur (after first submit)
useForm({ mode: 'onBlur' })

// Validate on change (after first submit)
useForm({ mode: 'onChange' })

// Validate on change immediately
useForm({ mode: 'all' })
```

### Avoiding Re-renders

```typescript
// ❌ DON'T: Watch all fields unnecessarily
const { watch } = useForm();
const allValues = watch();  // ← Triggers re-render on ANY field change

// ✅ DO: Watch specific fields only
const emailValue = watch('email');  // Only re-renders when email changes
```


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat form-validation-specialist-ext.md
```

Or in Claude Code:
```
Please read form-validation-specialist-ext.md for detailed examples.
```


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat form-validation-specialist-ext.md
```

Or in Claude Code:
```
Please read form-validation-specialist-ext.md for detailed examples.
```
