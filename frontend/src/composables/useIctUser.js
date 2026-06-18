export function useIctUser() {
  const fullName = (window.__frappe_full_name__ || '').trim()
  const email = window.__frappe_user__ || ''
  const display = fullName || email.split('@')[0] || 'there'
  const firstName = display.split(' ')[0] || display
  const initial = (display[0] || 'U').toUpperCase()
  return { fullName, email, display, firstName, initial }
}
