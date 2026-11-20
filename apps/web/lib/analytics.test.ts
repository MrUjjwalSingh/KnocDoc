import { describe, it, expect, beforeEach } from "vitest";
import { getSessionId } from "../lib/analytics";

describe("Frontend Analytics & Session", () => {
  beforeEach(() => {
    if (typeof window !== "undefined") {
      sessionStorage.clear();
    }
  });

  it("generates a valid session id", () => {
    const id = getSessionId();
    expect(id).toBeDefined();
    expect(typeof id).toBe("string");
    expect(id.length).toBeGreaterThan(5);
  });
});

