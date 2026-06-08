export function useApi() {
  function getCsrf() {
    return (
      window.__csrf_token__ ||
      document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
      ''
    )
  }

  async function call(method, args = {}) {
    const res = await fetch(`/api/method/${method}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Frappe-CSRF-Token': getCsrf(),
        Accept: 'application/json',
      },
      body: JSON.stringify(args),
    })

    const json = await res.json().catch(() => ({}))

    if (!res.ok) {
      if (res.status === 403 || res.status === 401) {
        window.location.href = `/login?redirect-to=${encodeURIComponent(window.location.pathname)}`
        return
      }
      throw new Error(extractMessage(json) || `HTTP ${res.status}`)
    }

    return json.message !== undefined ? json.message : json
  }

  async function upload(file) {
    const form = new FormData()
    form.append('file', file)
    form.append('is_private', '1')
    form.append('csrf_token', getCsrf())

    const res = await fetch('/api/method/upload_file', {
      method: 'POST',
      headers: { 'X-Frappe-CSRF-Token': getCsrf() },
      body: form,
    })
    const json = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(extractMessage(json) || 'Upload failed')
    return json.message?.file_url || ''
  }

  return { call, upload }
}

function extractMessage(json) {
  if (json._server_messages) {
    try {
      const msgs = JSON.parse(json._server_messages)
      return msgs
        .map((m) => {
          try { return JSON.parse(m).message } catch { return m }
        })
        .join(' ')
    } catch { /* fall through */ }
  }
  const exc = json.exception || json.exc || ''
  if (exc) {
    const last = exc.split('\n').filter(Boolean).pop() || ''
    return last.replace(/^frappe\.exceptions\.\w+:\s*/, '') || exc
  }
  return json.message || null
}
