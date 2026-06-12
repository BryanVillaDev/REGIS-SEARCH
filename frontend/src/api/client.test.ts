import { beforeEach, describe, expect, it } from "vitest";

import { getStoredToken, setStoredToken } from "./client";

describe("token storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("stores and clears the auth token", () => {
    setStoredToken("abc123");
    expect(getStoredToken()).toBe("abc123");

    setStoredToken(null);
    expect(getStoredToken()).toBeNull();
  });
});
