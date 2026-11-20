export interface Specialty {
  id: string;
  slug: string;
  name: string;
}

export interface Language {
  code: string;
  name: string;
}

export interface DoctorLanguage {
  language: Language;
  proficiency: "basic" | "fluent" | "native";
}

export interface Doctor {
  id: string;
  full_name: string;
  qualifications?: string;
  specialty?: Specialty;
  languages: DoctorLanguage[];
}

export interface Service {
  id: string;
  name: string;
  price_min?: number;
  price_max?: number;
  currency: string;
  last_verified_at?: string;
}

export interface ProviderSummary {
  id: string;
  name: string;
  type: "clinic" | "hospital" | "independent_doctor";
  address: string;
  distance_km: number;
  score: number;
  is_open_now: boolean;
  walk_in_available: boolean;
  verification_status: "verified" | "pending" | "rejected";
  languages: string[];
  language_names: string[];
  price_range?: string;
  average_rating?: number;
  review_count: number;
  match_reasons: string[];
  lat: number;
  lng: number;
}

export interface ProviderDetail {
  id: string;
  name: string;
  type: "clinic" | "hospital" | "independent_doctor";
  address: string;
  city: string;
  phone?: string;
  whatsapp?: string;
  opening_hours: Record<string, any>;
  timezone: string;
  verification_status: "verified" | "pending" | "rejected";
  last_verified_at?: string;
  walk_in_available: boolean;
  is_dummy: boolean;
  average_rating?: number;
  review_count: number;
  doctors: Doctor[];
  services: Service[];
  lat: number;
  lng: number;
}

export interface NeedCategory {
  key: string;
  label: string;
  icon: string;
}

export interface AppConfig {
  city_name: string;
  city_center_lat: number;
  city_center_lng: number;
  city_currency: string;
  city_emergency_number: string;
  is_demo_data: boolean;
  supported_languages: Language[];
  need_categories: NeedCategory[];
}

export interface SearchResponse {
  search_request_id: string;
  results: ProviderSummary[];
  total: number;
}

