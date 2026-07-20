import type { Job } from "./types";

export async function createJob(name: string): Promise<Job> {
  const resp = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!resp.ok) throw new Error(`Failed to create job (${resp.status})`);
  return (await resp.json()) as Job;
}

export async function rerunJob(jobId: number): Promise<void> {
  const resp = await fetch(`/api/jobs/${jobId}/rerun`, { method: "POST" });
  // 409 = already running; harmless, the firehose already reflects that.
  if (!resp.ok && resp.status !== 409) {
    throw new Error(`Failed to rerun job (${resp.status})`);
  }
}
