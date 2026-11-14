// Client for Hql/Apiserver (FastAPI, :8080). Contract quirks worth knowing
// (all verified against the backend source, Hql/Apiserver/__init__.py):
// - run dicts key their id as `run_id`, not `id`
// - POST /api/detections takes a RAW TEXT body, not JSON
// - failed runs put the Python traceback in `str_out`
// - num_results is 0 for plain (non-detection) runs even when rows exist
import type { DetectionDetail, DetectionMeta, HqlRun, TimeRange } from '../types'
import { DEFAULT_TIME_RANGE, timeRangeParams } from '../lib/timeRange'

const BASE = '/api'

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      // non-JSON error body, keep statusText
    }
    throw new ApiError(detail, res.status)
  }
  return (await res.json()) as T
}

function postJson<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
}

// The time range bounds HaC and Sigma runs; the backend 400s a bad one with
// a readable detail, which surfaces as the run's failure message
export function startRun(
  hql: string,
  timeRange: TimeRange = DEFAULT_TIME_RANGE,
  signal?: AbortSignal,
): Promise<{ id: string }> {
  return postJson(
    '/hql/runs',
    { hql, run: true, save: false, plan: false, ...timeRangeParams(timeRange) },
    signal,
  )
}

export function getRun(id: string, signal?: AbortSignal): Promise<HqlRun> {
  return request(`/hql/runs/${encodeURIComponent(id)}`, { signal })
}

const POLL_INTERVAL_MS = 1000
// Soft ceiling, not a UX timeout: the Stop button (AbortSignal) is the
// user-facing exit. The old UI's 60s cap broke legitimate long retro hunts.
const POLL_CEILING_MS = 10 * 60 * 1000

/** Poll a run until completed/failed. Aborting the signal stops waiting. */
export async function pollRun(id: string, signal: AbortSignal): Promise<HqlRun> {
  const deadline = Date.now() + POLL_CEILING_MS
  for (;;) {
    const run = await getRun(id, signal)
    if (run.completed || run.failed) return run
    if (Date.now() > deadline) throw new ApiError('Timed out waiting for run after 10 minutes')
    await new Promise((resolve, reject) => {
      const t = setTimeout(resolve, POLL_INTERVAL_MS)
      signal.addEventListener(
        'abort',
        () => {
          clearTimeout(t)
          reject(new DOMException('Aborted', 'AbortError'))
        },
        { once: true },
      )
    })
  }
}

export function getDetections(): Promise<DetectionMeta[]> {
  return request('/detections')
}

export function getDetection(id: string): Promise<DetectionDetail> {
  return request(`/detections/${encodeURIComponent(id)}`)
}

// The backend reads the raw body, so this is not JSON
export function saveDetection(text: string): Promise<{ id: string }> {
  return request('/detections', {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: text,
  })
}

export function initHac(hql: string): Promise<{ hql: string }> {
  return postJson('/hql/init_hac', { hql, run: false })
}

export function convertSigma(hql: string): Promise<{ hql: string }> {
  return postJson('/sigma/convert', { hql, run: false })
}

export function retroHunt(hql: string, start: string, end: string): Promise<{ ids: string[] }> {
  return postJson('/detections/retro', { hql, run: true, retro: true, start, end })
}
