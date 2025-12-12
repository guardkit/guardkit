---
paths: **/prisma/**, **/lib/db.ts
---

# Prisma ORM Integration

## Database Client Singleton

```typescript
// lib/db.ts
import { PrismaClient } from '@prisma/client'

const globalForPrisma = global as unknown as { prisma: PrismaClient }

export const db = globalForPrisma.prisma || new PrismaClient()

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = db
```

## Schema Definition

```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "sqlite"
  url      = env("DATABASE_URL")
}

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  password  String?
  image     String?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  posts     Post[]
}

model Post {
  id        String   @id @default(cuid())
  title     String
  content   String?
  published Boolean  @default(false)
  authorId  String
  author    User     @relation(fields: [authorId], references: [id], onDelete: Cascade)
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}
```

## Common Queries

### Find Many
```typescript
const users = await db.user.findMany({
  include: {
    posts: {
      take: 5
    }
  },
  orderBy: {
    createdAt: 'desc'
  }
})
```

### Find Unique
```typescript
const user = await db.user.findUnique({
  where: { id: userId },
  include: { posts: true }
})
```

### Create
```typescript
const user = await db.user.create({
  data: {
    email: 'user@example.com',
    name: 'John Doe'
  }
})
```

### Update
```typescript
const user = await db.user.update({
  where: { id: userId },
  data: { name: 'Jane Doe' }
})
```

### Delete
```typescript
await db.user.delete({
  where: { id: userId }
})
```

## Migrations

```bash
# Generate Prisma Client
npx prisma generate

# Create migration
npx prisma migrate dev --name add_user_table

# Apply migrations (production)
npx prisma migrate deploy

# Open Prisma Studio
npx prisma studio
```

## Environment Setup

```bash
# .env
DATABASE_URL="file:./dev.db"  # SQLite for dev
# DATABASE_URL="postgresql://..." # PostgreSQL for prod
```

## Best Practices

- Use database client singleton pattern
- Always include `updatedAt` for audit trails
- Use `@relation` with `onDelete: Cascade` for foreign keys
- Generate Prisma Client after schema changes
- Use migrations for schema version control
