// @vitest-environment jsdom

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Toast, ToastManager } from "./toast";

describe("Toast", () => {
  it("renders success message", () => {
    render(<Toast type="success" message="已保存" onClose={() => {}} />);
    expect(screen.getByText("已保存")).toBeDefined();
  });
  it("renders error message", () => {
    render(<Toast type="error" message="失败" onClose={() => {}} />);
    expect(screen.getByText("失败")).toBeDefined();
  });
  it("calls onClose on dismiss click", () => {
    const cb = vi.fn();
    render(<Toast type="info" message="提示" onClose={cb} />);
    fireEvent.click(screen.getByRole("button"));
    expect(cb).toHaveBeenCalledOnce();
  });
});

describe("ToastManager", () => {
  it("renders multiple toasts", () => {
    render(<ToastManager toasts={[{ id: "1", type: "success", message: "A" }, { id: "2", type: "error", message: "B" }]} onDismiss={() => {}} />);
    expect(screen.getByText("A")).toBeDefined();
    expect(screen.getByText("B")).toBeDefined();
  });
});
