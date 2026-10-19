export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export function errorMessage(body: unknown): string {
  if (!body || typeof body !== 'object') {
    return 'Something went wrong.'
  }
  const record = body as Record<string, unknown>
  if (typeof record.detail === 'string') {
    return record.detail
  }
  return Object.entries(record)
    .map(([field, value]) => {
      const text = Array.isArray(value) ? value.join(' ') : String(value)
      return field === 'non_field_errors' ? text : `${field}: ${text}`
    })
    .join('\n')
}

export async function unwrap<T>(
  call: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await call
  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(error))
  }
  return data as T
}
