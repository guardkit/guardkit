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

### Best Practices
- **Schemas**: Define in API layer, export schema + inferred type, one per operation
- **Required fields**: `.min(1, 'Required')` for strings
- **Error display**: Always pass `error` prop, inline with fields, ARIA attributes
- **Submission**: Disable button during submit (isLoading), show success notification
- **Type safety**: Always use `z.infer<typeof schema>`, never duplicate types


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


## Related Templates
- **templates/api/create-entity.ts.template** - Schema + mutation
- **templates/api/update-entity.ts.template** - Schema + mutation
- **templates/components/create-entity.tsx.template** - Form implementation
- **templates/components/update-entity.tsx.template** - Form with defaults


## Anti-Patterns to Avoid

### 1. Manual Validation Logic
```typescript
// DON'T: Write custom validation in component
const [errors, setErrors] = useState({});
if (!title || title.length < 1) { setErrors({ title: 'Required' }); }

// DO: Use Zod schema + zodResolver
const { register, handleSubmit, formState: { errors } } = useForm({
  resolver: zodResolver(schema),
});
```

### 2. Duplicating Validation in Schema and Component
Keep validation in Zod schemas only. Don't add manual checks alongside zodResolver.

### 3. Missing Type Coercion
```typescript
// DON'T: numeric inputs remain strings
<Input type="number" {...register('price')} />

// DO: use valueAsNumber
<Input type="number" {...register('price', { valueAsNumber: true })} />
```

### 4. No Loading States
```typescript
// DON'T: allow interaction during submission
<Button type="submit">Submit</Button>

// DO: disable during async operations
<Button type="submit" disabled={mutation.isPending}>
  {mutation.isPending ? 'Submitting...' : 'Submit'}
</Button>
```

### 5. Not Handling Error Display
```typescript
// DON'T: register fields without displaying errors
<Input {...register('email')} />

// DO: always display validation errors
<Input {...register('email')} />
{errors.email && <span className="text-red-500">{errors.email.message}</span>}
```


## Performance Optimization

### Validation Mode
```typescript
useForm({ mode: 'onSubmit' })   // Default: validate on submit
useForm({ mode: 'onBlur' })    // Validate on blur (after first submit)
useForm({ mode: 'onChange' })   // Validate on change (after first submit)
```

### Avoiding Re-renders
```typescript
// DON'T: watch all fields
const allValues = watch();  // Re-renders on ANY change

// DO: watch specific fields only
const emailValue = watch('email');  // Only re-renders when email changes
```
