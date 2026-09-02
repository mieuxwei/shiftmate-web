import { useCallback, useEffect, useState } from 'react'

import type { AuthGateway, AuthSession } from './session'

export type AuthState =
  | { kind: 'unconfigured' }
  | { kind: 'loading' }
  | { kind: 'signed-out' }
  | { kind: 'signed-in'; session: AuthSession }

function stateFor(session: AuthSession | null): AuthState {
  return session ? { kind: 'signed-in', session } : { kind: 'signed-out' }
}

export function useAuthSession(gateway: AuthGateway | null) {
  const [state, setState] = useState<AuthState>(() =>
    gateway ? { kind: 'loading' } : { kind: 'unconfigured' },
  )
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  useEffect(() => {
    if (!gateway) return

    let active = true
    let revision = 0

    const unsubscribe = gateway.subscribe((session) => {
      revision += 1
      if (active) setState(stateFor(session))
    })
    const initialRevision = revision

    void gateway
      .getSession()
      .then((session) => {
        if (active && revision === initialRevision) setState(stateFor(session))
      })
      .catch(() => {
        if (active && revision === initialRevision) {
          setState({ kind: 'signed-out' })
          setActionError('無法確認登入狀態，請稍後再試。')
        }
      })

    return () => {
      active = false
      unsubscribe()
    }
  }, [gateway])

  const signIn = useCallback(
    async (email: string, password: string) => {
      if (!gateway) return
      setIsSubmitting(true)
      setActionError(null)
      try {
        const session = await gateway.signIn(email, password)
        setState({ kind: 'signed-in', session })
      } catch {
        setActionError('登入失敗，請檢查電子郵件與密碼。')
      } finally {
        setIsSubmitting(false)
      }
    },
    [gateway],
  )

  const signOut = useCallback(async () => {
    if (!gateway) return
    setIsSubmitting(true)
    setActionError(null)
    try {
      await gateway.signOut()
      setState({ kind: 'signed-out' })
    } catch {
      setActionError('登出失敗，請稍後再試。')
    } finally {
      setIsSubmitting(false)
    }
  }, [gateway])

  return { state, isSubmitting, actionError, signIn, signOut }
}
