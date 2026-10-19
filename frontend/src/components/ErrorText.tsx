export function ErrorText({ error }: { error: unknown }) {
  if (!error) {
    return null
  }
  const message = error instanceof Error ? error.message : String(error)
  return <p className="error">{message}</p>
}
