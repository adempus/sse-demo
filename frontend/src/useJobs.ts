import { useCallback, useEffect, useRef, useState } from "react";
import { createJob, rerunJob } from "./api";
import { type Job, type JobEventData, type JobState } from "./types";

export interface UseJobsResult {
  jobs: Job[];
  connected: boolean;
  error: string | null;
  create: (name: string) => Promise<void>;
  run: (jobId: number) => Promise<void>;
}

/**
 * Subscribes to the single global SSE firehose (`/api/events`) so this device
 * sees *every* job state change from *any* device in real time.
 *
 * - On connect the server sends a `snapshot` of all jobs.
 * - Each subsequent `state` event is upserted into the list by job_id.
 *
 * `create`/`run` are fire-and-forget POSTs — the resulting transitions arrive
 * back over the firehose, so the UI updates identically no matter which device
 * triggered the action.
 */
export function useJobs(): UseJobsResult {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sourceRef = useRef<EventSource | null>(null);

  const upsert = useCallback((data: JobEventData) => {
    const now = new Date().toISOString();
    setJobs((prev) => {
      const idx = prev.findIndex((j) => j.id === data.job_id);
      if (idx === -1) {
        const created: Job = {
          id: data.job_id,
          name: data.name,
          state: data.state as JobState,
          created_at: now,
          updated_at: now,
        };
        return [created, ...prev];
      }
      const next = [...prev];
      next[idx] = { ...next[idx], state: data.state as JobState, updated_at: now };
      return next;
    });
  }, []);

  useEffect(() => {
    const source = new EventSource("/api/events");
    sourceRef.current = source;

    source.addEventListener("snapshot", (ev) => {
      const items = JSON.parse((ev as MessageEvent).data) as JobEventData[];
      const now = new Date().toISOString();
      setJobs(
        items.map((d) => ({
          id: d.job_id,
          name: d.name,
          state: d.state as JobState,
          created_at: now,
          updated_at: now,
        })),
      );
      setConnected(true);
      setError(null);
    });

    source.addEventListener("state", (ev) => {
      upsert(JSON.parse((ev as MessageEvent).data) as JobEventData);
    });

    source.onopen = () => {
      setConnected(true);
      setError(null);
    };

    source.onerror = () => {
      // EventSource auto-reconnects; surface a soft "reconnecting" hint.
      setConnected(false);
      setError("Reconnecting…");
    };

    return () => {
      source.close();
      sourceRef.current = null;
    };
  }, [upsert]);

  const create = useCallback(async (name: string) => {
    try {
      await createJob(name);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create job");
    }
  }, []);

  const run = useCallback(async (jobId: number) => {
    try {
      await rerunJob(jobId);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to run job");
    }
  }, []);

  return { jobs, connected, error, create, run };
}
