// Anonymous session analytics

export function getSessionId(): string {
  if (typeof window === "undefined") return "ssr-session";
  let sessionId = sessionStorage.getItem("traveldoc_session_id");
  if (!sessionId) {
    sessionId = "sess_" + Math.random().toString(36).substring(2, 15) + "_" + Date.now();
    sessionStorage.setItem("traveldoc_session_id", sessionId);
  }
  return sessionId;
}

export async function trackEvent(eventName: string, properties: Record<string, any> = {}) {
  try {
    const sessionId = getSessionId();
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    await fetch(`${apiUrl}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        event_name: eventName,
        properties,
      }),
    });
  } catch (err) {
    // Analytics logging should never break user interaction
    console.debug("Failed to log event:", err);
  }
}

