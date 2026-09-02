export type HealthStatus = {
  status: 'ok'
  environment: string
}

export async function getHealth(signal?: AbortSignal): Promise<HealthStatus> {
  const response = await fetch('/api/v1/health', { signal })

  if (!response.ok) {
    throw new Error(`Health request failed with status ${response.status}`)
  }

  return (await response.json()) as HealthStatus
}
