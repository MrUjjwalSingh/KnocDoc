import { describe, it, expect, vi, afterEach } from "vitest";
import { searchProviders } from "./api";

describe("searchProviders API client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("includes natural-language query when provided", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        search_request_id: "00000000-0000-0000-0000-000000000001",
        results: [],
        total: 0,
        applied_profile: "budget_focused",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await searchProviders(
      15.49,
      73.82,
      "en",
      "other",
      "Affordable English-speaking doctor"
    );

    expect(res.applied_profile).toBe("budget_focused");
    const [, init] = fetchMock.mock.calls[0];
    const body = JSON.parse(init.body);
    expect(body.query).toBe("Affordable English-speaking doctor");
  });

  it("surfaces structured API error messages", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      statusText: "Service Unavailable",
      json: async () => ({
        detail: { error: "openrouter_unavailable", message: "Natural-language search is temporarily unavailable." },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      searchProviders(15.49, 73.82, "en", "other", "Find a doctor")
    ).rejects.toThrow("Natural-language search is temporarily unavailable.");
  });
});
