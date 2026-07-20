import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StateBadge } from "./StateBadge";

describe("StateBadge", () => {
  it("renders the state label", () => {
    render(<StateBadge state="In Progress" />);
    expect(screen.getByText("In Progress")).toBeInTheDocument();
  });

  it("applies the state-specific class", () => {
    const { container } = render(<StateBadge state="Success" />);
    expect(container.querySelector(".badge--success")).not.toBeNull();
  });

  it("pulses for transient states", () => {
    const { container } = render(<StateBadge state="Queued" />);
    expect(container.querySelector(".badge.pulse")).not.toBeNull();
  });

  it("does not pulse for terminal states", () => {
    const { container } = render(<StateBadge state="Failed" />);
    expect(container.querySelector(".badge.pulse")).toBeNull();
  });
});
