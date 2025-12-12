---
paths: ["**/*form*", "**/*validation*", "**/*schema*"]
---

# Form Validation Patterns

Form management and validation using React Hook Form and Zod for type-safe, performant forms.

## Form Validation with Zod

Define schemas co-located with API mutations:

```typescript
// API layer
export const createDiscussionInputSchema = z.object({
  title: z.string().min(1, 'Required'),
  body: z.string().min(1, 'Required'),
});

export type CreateDiscussionInput = z.infer<typeof createDiscussionInputSchema>;

// Component layer
<Form
  id="create-discussion"
  onSubmit={(values) => createMutation.mutate({ data: values })}
  schema={createDiscussionInputSchema}
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
```

## Schema Definition Best Practices

### Co-locate with API Mutations
Define schemas where they're used in mutations:

```typescript
// features/discussions/api/create-discussion.ts
export const createDiscussionInputSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  body: z.string().min(1, 'Body is required'),
  tags: z.array(z.string()).optional(),
});

export type CreateDiscussionInput = z.infer<typeof createDiscussionInputSchema>;

export const createDiscussion = (data: CreateDiscussionInput) => {
  return api.post('/discussions', data);
};
```

### Validation Rules
Use Zod's rich validation API:

```typescript
export const userSchema = z.object({
  // Required string with min length
  name: z.string().min(1, 'Name is required'),

  // Email validation
  email: z.string().email('Invalid email address'),

  // Number with min/max
  age: z.number().min(18, 'Must be 18+').max(120),

  // Optional field
  bio: z.string().optional(),

  // Enum
  role: z.enum(['admin', 'user', 'moderator']),

  // Custom validation
  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain uppercase')
    .regex(/[0-9]/, 'Password must contain number'),

  // Conditional validation
  otherField: z.string().optional(),
}).refine(
  (data) => {
    if (data.role === 'admin') {
      return !!data.otherField;
    }
    return true;
  },
  {
    message: 'Other field required for admins',
    path: ['otherField'],
  }
);
```

## Form Component Patterns

### Basic Form
```typescript
import { Form } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export const CreateDiscussionForm = () => {
  const createMutation = useCreateDiscussion();

  return (
    <Form
      id="create-discussion"
      schema={createDiscussionInputSchema}
      onSubmit={(values) => {
        createMutation.mutate({ data: values });
      }}
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
          <Button
            type="submit"
            disabled={createMutation.isPending}
          >
            Create Discussion
          </Button>
        </>
      )}
    </Form>
  );
};
```

### Form with Default Values
```typescript
export const EditDiscussionForm = ({ discussion }: Props) => {
  const updateMutation = useUpdateDiscussion();

  return (
    <Form
      id="edit-discussion"
      schema={updateDiscussionInputSchema}
      options={{
        defaultValues: {
          title: discussion.title,
          body: discussion.body,
        },
      }}
      onSubmit={(values) => {
        updateMutation.mutate({
          discussionId: discussion.id,
          data: values,
        });
      }}
    >
      {/* ... */}
    </Form>
  );
};
```

### Form with Custom Validation
```typescript
export const PasswordChangeForm = () => {
  const changeMutation = useChangePassword();

  const schema = z.object({
    currentPassword: z.string().min(1, 'Required'),
    newPassword: z.string().min(8, 'Min 8 characters'),
    confirmPassword: z.string(),
  }).refine(
    (data) => data.newPassword === data.confirmPassword,
    {
      message: 'Passwords must match',
      path: ['confirmPassword'],
    }
  );

  return (
    <Form
      id="change-password"
      schema={schema}
      onSubmit={(values) => changeMutation.mutate(values)}
    >
      {/* ... */}
    </Form>
  );
};
```

## Error Handling

### Field-Level Errors
Display errors next to form fields:

```typescript
<Input
  label="Email"
  type="email"
  error={formState.errors['email']}
  registration={register('email')}
/>
```

### Form-Level Errors
Display server errors at form level:

```typescript
export const CreateForm = () => {
  const createMutation = useCreate();

  return (
    <Form
      id="create"
      schema={schema}
      onSubmit={(values) => createMutation.mutate({ data: values })}
    >
      {({ register, formState }) => (
        <>
          {createMutation.error && (
            <Alert variant="destructive">
              {createMutation.error.message}
            </Alert>
          )}
          {/* Form fields */}
        </>
      )}
    </Form>
  );
};
```

## Advanced Patterns

### Dynamic Fields
```typescript
const schema = z.object({
  items: z.array(
    z.object({
      name: z.string(),
      quantity: z.number(),
    })
  ),
});

export const DynamicForm = () => {
  return (
    <Form id="dynamic" schema={schema} onSubmit={handleSubmit}>
      {({ register, watch }) => {
        const items = watch('items') || [];

        return (
          <>
            {items.map((item, index) => (
              <div key={index}>
                <Input registration={register(`items.${index}.name`)} />
                <Input registration={register(`items.${index}.quantity`)} />
              </div>
            ))}
            <Button onClick={() => append({ name: '', quantity: 0 })}>
              Add Item
            </Button>
          </>
        );
      }}
    </Form>
  );
};
```

### File Upload
```typescript
const schema = z.object({
  file: z.instanceof(File),
  description: z.string(),
});

export const FileUploadForm = () => {
  return (
    <Form id="upload" schema={schema} onSubmit={handleUpload}>
      {({ register, setValue }) => (
        <>
          <input
            type="file"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) setValue('file', file);
            }}
          />
          <Input registration={register('description')} />
        </>
      )}
    </Form>
  );
};
```

### Dependent Fields
```typescript
const schema = z.object({
  hasAddress: z.boolean(),
  address: z.string().optional(),
}).refine(
  (data) => {
    if (data.hasAddress) {
      return !!data.address && data.address.length > 0;
    }
    return true;
  },
  {
    message: 'Address required when checkbox is selected',
    path: ['address'],
  }
);
```

## Best Practices

1. **Co-locate schemas**: Define Zod schemas next to API mutations
2. **Type inference**: Use `z.infer` to derive TypeScript types
3. **Meaningful errors**: Provide clear, user-friendly error messages
4. **Default values**: Pre-fill forms when editing existing data
5. **Loading states**: Disable submit button during mutation
6. **Server errors**: Display API errors clearly
7. **Reset after success**: Clear form after successful submission
