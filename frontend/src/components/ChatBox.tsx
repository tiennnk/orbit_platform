import { useMutation } from '@tanstack/react-query'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import { unwrap } from '../api/errors'
import { ErrorText } from './ErrorText'
import { DEFAULT_CENTER } from './mapDefaults'

type Turn = { role: 'user' | 'assistant'; content: string }

const MAX_TURNS = 20
const GREETING = 'Hi! Ask me about restaurants and dishes near you, or about your food orders.'

function useCurrentPosition(enabled: boolean): [number, number] {
  const [position, setPosition] = useState<[number, number]>(DEFAULT_CENTER)

  useEffect(() => {
    if (!enabled || !('geolocation' in navigator)) {
      return
    }
    navigator.geolocation.getCurrentPosition(
      (p) => setPosition([p.coords.latitude, p.coords.longitude]),
      () => undefined,
      { maximumAge: 60_000, timeout: 5_000 },
    )
  }, [enabled])

  return position
}

export function ChatBox() {
  const [open, setOpen] = useState(false)
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const position = useCurrentPosition(open)
  const listRef = useRef<HTMLDivElement>(null)

  const send = useMutation({
    mutationFn: (history: Turn[]) =>
      unwrap(
        api.POST('/api/v1/assistant/chat/', {
          body: { messages: history.slice(-MAX_TURNS + 1), latitude: position[0], longitude: position[1] },
        }),
      ),
    onSuccess: ({ reply }) => setTurns((current) => [...current, { role: 'assistant', content: reply }]),
    onError: (_, history) => {
      setTurns(history.slice(0, -1))
      setDraft(history[history.length - 1].content)
    },
  })

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
  }, [turns, send.isPending])

  function submit(event: FormEvent) {
    event.preventDefault()
    const content = draft.trim()
    if (!content || send.isPending) {
      return
    }
    const history: Turn[] = [...turns, { role: 'user', content }]
    setTurns(history)
    setDraft('')
    send.mutate(history)
  }

  if (!open) {
    return (
      <button className="chat-launcher" onClick={() => setOpen(true)}>
        Ask Orbit
      </button>
    )
  }

  return (
    <section className="chat-box card" aria-label="Orbit assistant">
      <div className="row between">
        <strong>Orbit assistant</strong>
        <div className="row">
          {turns.length > 0 && (
            <button className="link" disabled={send.isPending} onClick={() => setTurns([])}>
              Clear
            </button>
          )}
          <button className="close" aria-label="Close chat" onClick={() => setOpen(false)}>
            ×
          </button>
        </div>
      </div>
      <div className="chat-log" ref={listRef}>
        <p className="chat-turn assistant">{GREETING}</p>
        {turns.map((turn, index) => (
          <p key={index} className={`chat-turn ${turn.role}`}>
            {turn.content}
          </p>
        ))}
        {send.isPending && <p className="chat-turn assistant muted">Thinking...</p>}
      </div>
      <ErrorText error={send.error} />
      <form className="row chat-form" onSubmit={submit}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Pho under 50k nearby?"
          maxLength={1000}
          autoFocus
        />
        <button disabled={!draft.trim() || send.isPending}>Send</button>
      </form>
    </section>
  )
}
