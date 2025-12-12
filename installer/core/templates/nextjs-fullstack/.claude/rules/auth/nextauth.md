---
paths: **/auth/**, **/api/auth/**
---

# NextAuth Authentication

## Configuration

```typescript
// lib/auth.ts
import { NextAuthOptions } from 'next-auth'
import GitHubProvider from 'next-auth/providers/github'
import CredentialsProvider from 'next-auth/providers/credentials'

export const authOptions: NextAuthOptions = {
  providers: [
    GitHubProvider({
      clientId: process.env.GITHUB_ID!,
      clientSecret: process.env.GITHUB_SECRET!,
    }),
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        email: { label: "Email", type: "text" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        // Implement your auth logic
        const user = await db.user.findUnique({
          where: { email: credentials?.email }
        })

        if (user && verifyPassword(credentials?.password, user.password)) {
          return { id: user.id, email: user.email, name: user.name }
        }

        return null
      }
    })
  ],
  session: {
    strategy: 'jwt'
  },
  pages: {
    signIn: '/auth/signin',
  }
}
```

## API Route

```typescript
// app/api/auth/[...nextauth]/route.ts
import NextAuth from 'next-auth'
import { authOptions } from '@/lib/auth'

const handler = NextAuth(authOptions)

export { handler as GET, handler as POST }
```

## Protecting Pages (Server Component)

```typescript
// app/(dashboard)/users/page.tsx
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { redirect } from 'next/navigation'

export default async function UsersPage() {
  const session = await getServerSession(authOptions)

  if (!session) {
    redirect('/auth/signin')
  }

  return <div>Protected content</div>
}
```

## Protecting API Routes

```typescript
// app/api/users/route.ts
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions)

  if (!session) {
    return NextResponse.json(
      { error: 'Unauthorized' },
      { status: 401 }
    )
  }

  // ... authenticated logic
}
```

## Client-Side Session

```typescript
// components/UserMenu.tsx
'use client'

import { useSession, signIn, signOut } from 'next-auth/react'

export function UserMenu() {
  const { data: session, status } = useSession()

  if (status === 'loading') {
    return <div>Loading...</div>
  }

  if (!session) {
    return <button onClick={() => signIn()}>Sign In</button>
  }

  return (
    <div>
      <p>Welcome, {session.user?.name}</p>
      <button onClick={() => signOut()}>Sign Out</button>
    </div>
  )
}
```

## Environment Variables

```bash
# .env
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-secret-key"
GITHUB_ID="your-github-oauth-app-id"
GITHUB_SECRET="your-github-oauth-app-secret"
```

## Session Provider

```typescript
// app/layout.tsx
import { SessionProvider } from 'next-auth/react'

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <SessionProvider>
          {children}
        </SessionProvider>
      </body>
    </html>
  )
}
```
