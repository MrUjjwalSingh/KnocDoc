import { AppConfig, ProviderDetail, SearchResponse } from "./types";
import { getSessionId } from "./analytics";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_INTERNAL_BASE = process.env.API_INTERNAL_URL || API_BASE;

export async function fetchConfig(): Promise<AppConfig> {
  const apiBase = typeof window === "undefined" ? API_INTERNAL_BASE : API_BASE;
  const res = await fetch(`${apiBase}/config`, { next: { revalidate: 60 } });
  if (!res.ok) {
    // Fallback config if API is temporarily unavailable
    return {
      city_name: "Goa, India",
      city_center_lat: 15.4909,
      city_center_lng: 73.8278,
      city_currency: "INR",
      city_emergency_number: "112",
      is_demo_data: true,
      supported_languages: [
        { code: "en", name: "English" },
        { code: "hi", name: "Hindi" },
        { code: "ru", name: "Russian" },
        { code: "ar", name: "Arabic" },
        { code: "fr", name: "French" },
        { code: "de", name: "German" },
        { code: "kok", name: "Konkani" },
      ],
      need_categories: [
        { key: "fever", label: "Fever / Flu", icon: "🤒" },
        { key: "stomach_issue", label: "Stomach Issue", icon: "🤢" },
        { key: "injury", label: "Injury / Wound", icon: "🩹" },
        { key: "dental_pain", label: "Dental Pain", icon: "🦷" },
        { key: "skin_problem", label: "Skin Problem", icon: "🩺" },
        { key: "ear_nose_throat", label: "Ear, Nose & Throat", icon: "👂" },
        { key: "child_health", label: "Child Health", icon: "👶" },
        { key: "other", label: "General / Other", icon: "➕" },
      ],
    };
  }
  return res.json();
}

export async function searchProviders(
  lat: number,
  lng: number,
  language_code: string,
  need_category: string
): Promise<SearchResponse> {
  const sessionId = getSessionId();
  const res = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      lat,
      lng,
      language_code,
      need_category,
      session_id: sessionId,
    }),
  });

  if (!res.ok) {
    throw new Error(`Search failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchProvider(id: string): Promise<ProviderDetail> {
  const res = await fetch(`${API_BASE}/providers/${id}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to load provider profile (${res.status})`);
  }
  return res.json();
}

export async function submitReview(data: {
  provider_id: string;
  search_request_id?: string;
  rating: number;
  actual_amount_paid?: number;
  comment?: string;
}) {
  const res = await fetch(`${API_BASE}/reviews`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`Failed to submit review: ${res.statusText}`);
  }
  return res.json();
}

