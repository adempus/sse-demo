import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { JobRow } from "./JobRow";
import type { Job } from "../types";

const baseJob: Job = {
  id: 1,
  name: "Nightly export",
  state: "Not Ready",
  created_at: "2026-07-04T12:00:00Z",
  updated_at: "2026-07-04T12:00:00Z",
};

describe("JobRow", () => {
  it("renders the job name and state", () => {
    render(<JobRow job={baseJob} running={false} onRun={() => {}} />);
    expect(screen.getByText("Nightly export")).toBeInTheDocument();
    expect(screen.getByText("Not Ready")).toBeInTheDocument();
  });

  it("calls onRun with the job id when clicked", async () => {
    const onRun = vi.fn();
    render(<JobRow job={baseJob} running={false} onRun={onRun} />);
    await userEvent.click(screen.getByRole("button", { name: /run nightly export/i }));
    expect(onRun).toHaveBeenCalledWith(1);
  });

  it("disables the button while running", () => {
    render(<JobRow job={baseJob} running={true} onRun={() => {}} />);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
