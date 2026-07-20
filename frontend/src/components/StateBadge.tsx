import { type JobState } from "../types";

const CLASS_MAP: Record<JobState, string> = {
  "Not Ready": "badge--not-ready",
  Queued: "badge--queued",
  "In Progress": "badge--in-progress",
  Success: "badge--success",
  Failed: "badge--failed",
};

const PULSE_STATES: ReadonlySet<JobState> = new Set(["Queued", "In Progress"]);

export function StateBadge({ state }: { state: JobState }) {
  const pulse = PULSE_STATES.has(state) ? " pulse" : "";
  return (
    <span className={`badge ${CLASS_MAP[state]}${pulse}`} role="status" aria-live="polite">
      <span className="dot" />
      {state}
    </span>
  );
}
