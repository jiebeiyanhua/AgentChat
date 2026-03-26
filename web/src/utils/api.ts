const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'

export const defaultWsUrl = `${protocol}//${window.location.hostname || 'localhost'}:8000/ws/agent-talk`

export function buildHttpUrl(path: string, query?: Record<string, string>) {
  const url = new URL(defaultWsUrl)
  url.protocol = url.protocol === 'wss:' ? 'https:' : 'http:'
  const target = new URL(path, `${url.protocol}//${url.host}`)

  if (query) {
    Object.entries(query).forEach(([key, value]) => target.searchParams.set(key, value))
  }

  return target.toString()
}
