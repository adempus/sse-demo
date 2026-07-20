/** Job states mirrored from the backend enum. */
export const JOB_STATES = ["Not Ready", "Queued", "In Progress", "Failed", "Success"] as const;

export type JobState = (typeof JOB_STATES)[number];

export interface Job {
  id: number;
  name: string;
  state: JobState;
  created_at: string;
  updated_at: string;
}

export const TERMINAL_STATES: ReadonlySet<JobState> = new Set(["Success", "Failed"]);

export function isTerminal(state: JobState): boolean {
  return TERMINAL_STATES.has(state);
}

/** A job is actively running (server-derived) while transitioning. */
const RUNNING_STATES: ReadonlySet<JobState> = new Set(["Queued", "In Progress"]);

export function isRunning(state: JobState): boolean {
  return RUNNING_STATES.has(state);
}

/** Payload shape for a single job in an SSE `snapshot` or `state` event. */
export interface JobEventData {
  job_id: number;
  name: string;
  state: JobState;
}
