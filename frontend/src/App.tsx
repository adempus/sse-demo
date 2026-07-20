import { useState } from "react";
import { JobRow } from "./components/JobRow";
import { isRunning } from "./types";
import { useJobs } from "./useJobs";

export default function App() {
  const { jobs, connected, error, create, run } = useJobs();
  const [name, setName] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    await create(trimmed);
    setName("");
  };

  return (
    <main className="app">
      <div className="header">
        <h1>SSE State Demo</h1>
        <span className={`conn ${connected ? "conn--on" : "conn--off"}`}>
          <span className="dot" />
          {connected ? "Live" : "Reconnecting…"}
        </span>
      </div>
      <p className="subtitle">
        Create named jobs and watch every device stay in sync in real time. Job state is broadcast
        from FastAPI over a single Server-Sent Events stream — open this page on another device and
        run a job here to see it update there too.
      </p>

      <form className="create-form" onSubmit={submit}>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Job name (e.g. Nightly export)"
          maxLength={120}
          aria-label="Job name"
        />
        <button className="run" type="submit" disabled={!name.trim()}>
          Create &amp; Run
        </button>
      </form>

      {error && <p className="error">⚠ {error}</p>}

      {jobs.length === 0 ? (
        <p className="muted">No jobs yet. Create one above to get started.</p>
      ) : (
        <ul className="job-list">
          {jobs.map((job) => (
            <JobRow key={job.id} job={job} running={isRunning(job.state)} onRun={run} />
          ))}
        </ul>
      )}
    </main>
  );
}
