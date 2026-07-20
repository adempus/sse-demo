import { type Job } from "../types";
import { StateBadge } from "./StateBadge";

interface JobRowProps {
  job: Job;
  running: boolean;
  onRun: (id: number) => void;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function JobRow({ job, running, onRun }: JobRowProps) {
  return (
    <li className="job-row">
      <div className="job-meta">
        <span className="job-name">{job.name}</span>
        <span className="job-updated">updated {formatTime(job.updated_at)}</span>
      </div>
      <StateBadge state={job.state} />
      <button
        className="run run--sm"
        onClick={() => onRun(job.id)}
        disabled={running}
        aria-label={`Run ${job.name}`}
      >
        {running ? "Running…" : "Run"}
      </button>
    </li>
  );
}
