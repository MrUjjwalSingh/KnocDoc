"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, List, Map as MapIcon, SlidersHorizontal, AlertCircle, Sparkles, HelpCircle } from "lucide-react";
import { ProviderCard } from "@/components/ProviderCard";
import { MapView } from "@/components/MapView";
import { searchProviders } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";
import { ParsedSearchPreferences, ProviderSummary, SearchResponse } from "@/lib/types";

function ResultsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const latStr = searchParams.get("lat") || "15.4909";
  const lngStr = searchParams.get("lng") || "73.8278";
  const lang = searchParams.get("lang") || "en";
  const need = searchParams.get("need") || "fever";
  const nlQuery = searchParams.get("q") || "";
  const locationLabel = searchParams.get("label") || "Goa";

  const lat = parseFloat(latStr);
  const lng = parseFloat(lngStr);

  const [results, setResults] = useState<ProviderSummary[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [parsedPrefs, setParsedPrefs] = useState<ParsedSearchPreferences | null>(null);
  const [appliedProfile, setAppliedProfile] = useState<string>("balanced");
  const [limitingConstraints, setLimitingConstraints] = useState<string[]>([]);
  const [clarificationMessage, setClarificationMessage] = useState<string | null>(null);
  const [unanswerableMessage, setUnanswerableMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"list" | "map">("list");

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    setClarificationMessage(null);
    setUnanswerableMessage(null);
    setLimitingConstraints([]);

    searchProviders(lat, lng, lang, need, nlQuery || undefined)
      .then((data: SearchResponse) => {
        setResults(data.results);
        setTotal(data.total);
        setParsedPrefs(data.parsed_preferences || null);
        setAppliedProfile(data.applied_profile || "balanced");
        setLimitingConstraints(data.limiting_constraints || []);
        if (data.clarification_needed) {
          setClarificationMessage(data.clarification_message || "Please clarify your location or search criteria.");
        }
        if (data.unanswerable) {
          setUnanswerableMessage(data.unanswerable_message || "This request cannot be answered by the directory.");
        }
        setIsLoading(false);

        trackEvent("results_viewed", {
          results_count: data.total,
          language_code: lang,
          need_category: need,
          has_natural_language_query: Boolean(nlQuery),
          lat,
          lng,
        });
      })
      .catch((err) => {
        console.error("Search error:", err);
        setError(err instanceof Error ? err.message : "Unable to connect to the search server. Please check your connection or try again.");
        setIsLoading(false);
      });
  }, [lat, lng, lang, need, nlQuery]);

  return (
    <div className="space-y-4">
      {/* Header with back navigation and view switcher */}
      <div className="flex items-center justify-between gap-2 pb-2 border-b border-slate-100">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 px-3 py-1.5 rounded-xl transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>New search</span>
        </Link>

        {/* View Toggle */}
        <div className="inline-flex rounded-xl bg-slate-100 p-0.5 border border-slate-200">
          <button
            type="button"
            onClick={() => setViewMode("list")}
            className={`inline-flex items-center gap-1 px-3 py-1 text-xs font-bold rounded-lg transition-all ${
              viewMode === "list"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            <List className="h-3.5 w-3.5" />
            List
          </button>
          <button
            type="button"
            onClick={() => setViewMode("map")}
            className={`inline-flex items-center gap-1 px-3 py-1 text-xs font-bold rounded-lg transition-all ${
              viewMode === "map"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            <MapIcon className="h-3.5 w-3.5" />
            Map
          </button>
        </div>
      </div>

      {/* Query summary pill */}
      <div className="bg-emerald-50 border border-emerald-200/60 rounded-xl px-3.5 py-2 text-xs flex items-center justify-between text-emerald-950">
        <div className="flex items-center gap-2 truncate">
          {nlQuery ? (
            <span className="font-bold truncate inline-flex items-center gap-1">
              <Sparkles className="h-3.5 w-3.5 text-emerald-600 flex-shrink-0" />
              &ldquo;{nlQuery}&rdquo;
            </span>
          ) : (
            <span className="font-bold capitalize">{need.replace("_", " ")}</span>
          )}
          <span>&bull;</span>
          <span className="truncate text-emerald-800">{locationLabel}</span>
        </div>
        <span className="font-semibold text-emerald-700 flex-shrink-0">
          {isLoading ? "Searching..." : `${total} matched`}
        </span>
      </div>

      {/* Parsed intent chips */}
      {!isLoading && parsedPrefs && (
        <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
          {parsedPrefs.specialty && (
            <span className="bg-slate-100 text-slate-800 px-2.5 py-1 rounded-full font-medium">
              Specialty: {parsedPrefs.specialty.replace("_", " ")}
            </span>
          )}
          {parsedPrefs.languages.length > 0 && (
            <span className="bg-slate-100 text-slate-800 px-2.5 py-1 rounded-full font-medium">
              Languages ({parsedPrefs.language_mode === "all" ? "all" : "any"}): {parsedPrefs.languages.join(", ")}
            </span>
          )}
          {parsedPrefs.radius_km != null && (
            <span className="bg-slate-100 text-slate-800 px-2.5 py-1 rounded-full font-medium">
              Within {parsedPrefs.radius_km} km
            </span>
          )}
          {parsedPrefs.budget_max != null && (
            <span className="bg-slate-100 text-slate-800 px-2.5 py-1 rounded-full font-medium">
              Max ₹{parsedPrefs.budget_max}
            </span>
          )}
          {parsedPrefs.verification_required && (
            <span className="bg-emerald-50 text-emerald-800 border border-emerald-200 px-2.5 py-1 rounded-full font-medium">
              Verified only
            </span>
          )}
          <span className="bg-indigo-50 text-indigo-800 px-2.5 py-1 rounded-full font-medium">
            Ranking: {appliedProfile.replace("_", " ")}
          </span>
        </div>
      )}

      {/* Clarification or Unanswerable notice */}
      {!isLoading && (clarificationMessage || unanswerableMessage) && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl text-xs text-amber-950 flex items-start gap-2.5">
          <HelpCircle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1 space-y-1">
            <p className="font-bold">
              {unanswerableMessage ? "Request cannot be fulfilled as stated" : "More details needed"}
            </p>
            <p className="text-amber-800">{unanswerableMessage || clarificationMessage}</p>
          </div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-2xl text-xs text-red-900 flex items-start gap-2.5">
          <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-bold">Search temporarily unavailable</p>
            <p className="mt-0.5 text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Loading Skeletons */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="bg-white rounded-2xl border border-slate-200 p-5 space-y-3 animate-pulse"
            >
              <div className="flex justify-between items-start">
                <div className="space-y-2 flex-1">
                  <div className="h-3 bg-slate-200 rounded w-24" />
                  <div className="h-5 bg-slate-200 rounded w-48" />
                  <div className="h-3 bg-slate-200 rounded w-32" />
                </div>
                <div className="h-7 w-12 bg-slate-200 rounded-lg" />
              </div>
              <div className="flex gap-2 pt-2 border-t border-slate-100">
                <div className="h-6 w-20 bg-slate-200 rounded-md" />
                <div className="h-6 w-24 bg-slate-200 rounded-md" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && !clarificationMessage && !unanswerableMessage && results.length === 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center space-y-3">
          <div className="text-4xl">🔍</div>
          <h3 className="text-base font-bold text-slate-900">No matching providers found</h3>
          {limitingConstraints.length > 0 ? (
            <div className="text-xs text-slate-600 max-w-sm mx-auto space-y-1">
              <p className="font-semibold text-slate-700">Limiting requirements:</p>
              <ul className="list-disc list-inside text-left">
                {limitingConstraints.map((c, idx) => (
                  <li key={idx}>{c}</li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-xs text-slate-500 max-w-xs mx-auto">
              Try picking a different location, widening your radius, or adjusting your care criteria.
            </p>
          )}
          <div className="pt-2">
            <Link
              href="/"
              className="inline-block bg-emerald-600 text-white font-bold text-xs py-2.5 px-4 rounded-xl hover:bg-emerald-700 transition-colors"
            >
              Adjust search
            </Link>
          </div>
        </div>
      )}

      {/* Results View: List or Map */}
      {!isLoading && !error && results.length > 0 && (
        <div>
          {viewMode === "list" ? (
            <div className="space-y-3">
              {results.map((prov, index) => (
                <ProviderCard key={prov.id} provider={prov} rank={index + 1} />
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              <MapView
                providers={results}
                center={[lat, lng]}
                zoom={12}
                onSelectProvider={(id) => router.push(`/providers/${id}`)}
              />
              <p className="text-[11px] text-slate-400 text-center">
                Tap on any pin to view details and jump to profile.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 text-center text-xs text-slate-400">Loading search results...</div>
      }
    >
      <ResultsContent />
    </Suspense>
  );
}

