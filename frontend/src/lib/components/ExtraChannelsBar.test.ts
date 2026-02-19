import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/svelte";
import ExtraChannelsBar from "./ExtraChannelsBar.svelte";

describe("ExtraChannelsBar", () => {
  it("renders nothing when no channels", () => {
    const { container } = render(ExtraChannelsBar, {
      props: { channels: [], values: {} },
    });
    expect(container.querySelector(".extra-channels-bar")).toBeNull();
  });

  it("renders channel names", () => {
    render(ExtraChannelsBar, {
      props: {
        channels: [{ name: "Inlet" }, { name: "Exhaust" }],
        values: { Inlet: 250.5, Exhaust: 180.3 },
      },
    });
    expect(screen.getByText("Inlet")).toBeInTheDocument();
    expect(screen.getByText("Exhaust")).toBeInTheDocument();
  });

  it("renders channel values with one decimal", () => {
    render(ExtraChannelsBar, {
      props: {
        channels: [{ name: "Inlet" }],
        values: { Inlet: 250.55 },
      },
    });
    expect(screen.getByText("250.6")).toBeInTheDocument();
  });

  it("shows --- when value is missing", () => {
    render(ExtraChannelsBar, {
      props: {
        channels: [{ name: "Inlet" }],
        values: {},
      },
    });
    expect(screen.getByText("---")).toBeInTheDocument();
  });

  it("renders correct number of badges", () => {
    const { container } = render(ExtraChannelsBar, {
      props: {
        channels: [{ name: "Inlet" }, { name: "Exhaust" }, { name: "Gas" }],
        values: { Inlet: 250, Exhaust: 180, Gas: 0.5 },
      },
    });
    const badges = container.querySelectorAll(".channel-badge");
    expect(badges).toHaveLength(3);
  });
});
