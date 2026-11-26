"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { MapPin, Navigation, Languages, Stethoscope, Search, RefreshCw } from "lucide-react";
import { NeedChips } from "@/components/NeedChips";
import { fetchConfig } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";
import { AppConfig, NeedCategory } from "@/lib/types";

// Seeded popular areas in Lucknow for manual fallback
const POPULAR_AREAS = [
  { name: "Hazratganj (Central Lucknow)", lat: 26.8555, lng: 80.9430 },
  { name: "Gomti Nagar (East Hub)", lat: 26.8505, lng: 81.0095 },
  { name: "Alambagh (South / Kanpur Rd)", lat: 26.8015, lng: 80.8950 },
  { name: "Aliganj (North)", lat: 26.9052, lng: 80.9480 },
  { name: "Indira Nagar", lat: 26.8833, lng: 80.9833 },
  { name: "Mahanagar / Nirala Nagar", lat: 26.8775, lng: 80.9562 },
  { name: "Chowk / KGMU (Old City)", lat: 26.8633, lng: 80.9033 },
  { name: "Aminabad", lat: 26.8463, lng: 80.9263 },
  { name: "Golf City / Shaheed Path (Medanta)", lat: 26.7773, lng: 80.9857 },
  { name: "Raebareli Road (SGPGI)", lat: 26.7464, lng: 80.9361 },
];

export default function SearchPage() {
  const router = useRouter();

  const [config, setConfig] = useState<AppConfig | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<string>("en");
  const [selectedNeed, setSelectedNeed] = useState<string>("fever");

  // Location state
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [locationLabel, setLocationLabel] = useState<string>("Detecting your location...");
  const [isDetecting, setIsDetecting] = useState<boolean>(false);
  const [manualAreaIndex, setManualAreaIndex] = useState<number>(0);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  useEffect(() => {
    // Load config
    fetchConfig().then((cfg) => {
      setConfig(cfg);
      // Fallback default coordinates from config
      setCoords({ lat: cfg.city_center_lat, lng: cfg.city_center_lng });
      setLocationLabel(`${cfg.city_name} (Center default)`);
    });

    // Restore saved language preference
    const savedLang = localStorage.getItem("traveldoc_lang");
    if (savedLang) {
      setSelectedLanguage(savedLang);
    }

    // Try geolocation
    detectLocation();
  }, []);

  function handleLanguageChange(code: string) {
    setSelectedLanguage(code);
    localStorage.setItem("traveldoc_lang", code);
  }

  function detectLocation() {
    if (!navigator.geolocation) {
      setLocationLabel("Geolocation not supported. Select area below.");
      return;
    }

    setIsDetecting(true);
    setLocationLabel("Locating you...");

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setLocationLabel("Current location (GPS detected)");
        setIsDetecting(false);
      },
      (err) => {
        console.warn("Geolocation error/denied:", err.message);
        // Fallback to Panaji default
        const fallback = POPULAR_AREAS[0];
        setCoords({ lat: fallback.lat, lng: fallback.lng });
        setLocationLabel(`${fallback.name} (Fallback)`);
        setIsDetecting(false);
      },
      { timeout: 8000, enableHighAccuracy: true }
    );
  }

  function handleAreaSelect(idx: number) {
    setManualAreaIndex(idx);
    const area = POPULAR_AREAS[idx];
    setCoords({ lat: area.lat, lng: area.lng });
    setLocationLabel(area.name);
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!coords) return;

    setIsSubmitting(true);

    trackEvent("search_submitted", {
      lat: coords.lat,
      lng: coords.lng,
      language_code: selectedLanguage,
      need_category: selectedNeed,
    });

    const params = new URLSearchParams({
      lat: coords.lat.toString(),
      lng: coords.lng.toString(),
      lang: selectedLanguage,
      need: selectedNeed,
      label: locationLabel,
    });

    router.push(`/results?${params.toString()}`);
  }

  const needCategories = config?.need_categories || [
    { key: "fever", label: "Fever / Flu", icon: "🤒" },
    { key: "stomach_issue", label: "Stomach Issue", icon: "🤢" },
    { key: "injury", label: "Injury / Wound", icon: "🩹" },
    { key: "dental_pain", label: "Dental Pain", icon: "🦷" },
    { key: "skin_problem", label: "Skin Problem", icon: "🩺" },
    { key: "ear_nose_throat", label: "Ear, Nose & Throat", icon: "👂" },
    { key: "child_health", label: "Child Health", icon: "👶" },
    { key: "other", label: "General / Other", icon: "➕" },
  ];

  const languages = config?.supported_languages || [
    { code: "en", name: "English" },
    { code: "hi", name: "Hindi" },
    { code: "ru", name: "Russian" },
    { code: "ar", name: "Arabic" },
    { code: "fr", name: "French" },
    { code: "de", name: "German" },
    { code: "kok", name: "Konkani" },
  ];

  return (
    <div className="space-y-6">
      {/* Brand Header */}
      <div className="flex items-center justify-between pt-1">
        <div className="flex items-center space-x-2">
          <div className="bg-emerald-600 text-white p-2 rounded-xl shadow-sm">
            <Stethoscope className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-extrabold tracking-tight text-slate-900">
              Travel<span className="text-emerald-600">Doc</span>
            </h1>
            <p className="text-xs text-slate-500 font-medium">Healthcare abroad made simple</p>
          </div>
        </div>

        {/* Language selector */}
        <div className="flex items-center space-x-1 bg-slate-100 rounded-xl px-2.5 py-1.5 border border-slate-200">
          <Languages className="h-4 w-4 text-slate-500" />
          <select
            value={selectedLanguage}
            onChange={(e) => handleLanguageChange(e.target.value)}
            className="bg-transparent text-xs font-semibold text-slate-800 focus:outline-none cursor-pointer"
            aria-label="Select your spoken language"
          >
            {languages.map((l) => (
              <option key={l.code} value={l.code}>
                {l.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Search Form */}
      <form onSubmit={handleSearch} className="space-y-6">
        {/* Step 1: Location Box */}
        <section className="bg-slate-50 rounded-2xl p-4 border border-slate-200 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Your Location in {config?.city_name?.split(",")[0] || "Lucknow"}
            </span>
            <button
              type="button"
              onClick={detectLocation}
              disabled={isDetecting}
              className="inline-flex items-center gap-1 text-xs text-emerald-700 hover:text-emerald-800 font-semibold focus:outline-none"
            >
              <RefreshCw className={`h-3 w-3 ${isDetecting ? "animate-spin" : ""}`} />
              Auto-detect GPS
            </button>
          </div>

          <div className="flex items-center gap-2 bg-white rounded-xl border border-slate-200 p-2.5 shadow-sm">
            <MapPin className="h-4 w-4 text-emerald-600 flex-shrink-0" />
            <span className="text-sm font-medium text-slate-800 truncate flex-1">
              {locationLabel}
            </span>
          </div>

          {/* Quick manual picker */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">
              Or pick an area:
            </label>
            <select
              value={manualAreaIndex}
              onChange={(e) => handleAreaSelect(Number(e.target.value))}
              className="w-full text-xs bg-white rounded-xl border border-slate-200 p-2 text-slate-700 focus:border-emerald-500 focus:outline-none"
            >
              {POPULAR_AREAS.map((a, i) => (
                <option key={i} value={i}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>
        </section>

        {/* Step 2: Need selector */}
        <section className="space-y-2.5">
          <label className="block text-sm font-bold text-slate-900">
            What do you need care for?
          </label>
          <NeedChips
            categories={needCategories}
            selectedKey={selectedNeed}
            onSelect={setSelectedNeed}
          />
        </section>

        {/* Step 3: CTA Button */}
        <button
          type="submit"
          disabled={isSubmitting || !coords}
          className="w-full bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white font-extrabold py-4 px-6 rounded-2xl shadow-lg shadow-emerald-600/20 text-base transition-all duration-150 flex items-center justify-center space-x-2 disabled:opacity-50 select-none cursor-pointer"
        >
          <Search className="h-5 w-5" />
          <span>{isSubmitting ? "Finding doctors..." : "Find doctors near me"}</span>
        </button>
      </form>
    </div>
  );
}

