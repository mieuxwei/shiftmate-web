import { createClient, type Session } from '@supabase/supabase-js'

export type AuthSession = {
  accessToken: string
  email: string
}

export interface AuthGateway {
  getSession(): Promise<AuthSession | null>
  subscribe(listener: (session: AuthSession | null) => void): () => void
  signIn(email: string, password: string): Promise<AuthSession>
  signOut(): Promise<void>
}

function toAuthSession(session: Session | null): AuthSession | null {
  if (!session) return null

  return {
    accessToken: session.access_token,
    email: session.user.email ?? '已登入使用者',
  }
}

export class SupabaseAuthGateway implements AuthGateway {
  constructor(private readonly client: ReturnType<typeof createClient>) {}

  async getSession(): Promise<AuthSession | null> {
    const { data, error } = await this.client.auth.getSession()
    if (error) throw error
    return toAuthSession(data.session)
  }

  subscribe(listener: (session: AuthSession | null) => void): () => void {
    const { data } = this.client.auth.onAuthStateChange((_event, session) => {
      listener(toAuthSession(session))
    })

    return () => data.subscription.unsubscribe()
  }

  async signIn(email: string, password: string): Promise<AuthSession> {
    const { data, error } = await this.client.auth.signInWithPassword({
      email,
      password,
    })
    if (error) throw error

    const session = toAuthSession(data.session)
    if (!session) throw new Error('Supabase did not return a session')
    return session
  }

  async signOut(): Promise<void> {
    const { error } = await this.client.auth.signOut()
    if (error) throw error
  }
}

export function createConfiguredAuthGateway(
  env: ImportMetaEnv = import.meta.env,
): AuthGateway | null {
  const url = env.VITE_SUPABASE_URL?.trim()
  const anonKey = env.VITE_SUPABASE_ANON_KEY?.trim()

  if (!url || !anonKey) return null
  return new SupabaseAuthGateway(createClient(url, anonKey))
}

export const configuredAuthGateway = createConfiguredAuthGateway()
