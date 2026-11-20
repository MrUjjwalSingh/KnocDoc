"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  MapPin,
  Phone,
  MessageCircle,
  Navigation,
  Star,
  UserCheck,
  Tag,
  Calendar,
  MessageSquare,
  AlertCircle,
} from "lucide-react";
import { FeedbackForm } from "@/components/FeedbackForm";
import { fetchProvider } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";
import { ProviderDetail } from "@/lib/types";

const DAYS_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const DAY_LABELS: Record<string, string> = {
  mon: "Monday",
  tue: "Tuesday",
  wed: "Wednesday",
  thu: "Thursday",
  fri: "Friday",
  sat: "Saturday",
  sun: "Sunday",
};

export default function ProviderProfilePage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const [provider, setProvider] = useState<ProviderDetail | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showFeedbackModal, setShowFeedbackModal] = useState<boolean>(false);

  useEffect(() => {
    if (!id) return;

    setIsLoading(true);
    fetchProvider(id)
      .then((data) => {
        setProvider(data);
        setIsLoading(false);

        trackEvent("provider_opened", {
          provider_id: data.id,
          provider_name: data.name,
          verification_status: data.verification_status,
        });
      })
      .catch((err) => {
        console.error("Provider fetch error:", err);
        setError("Failed to load provider profile.");
        setIsLoading(false);
      });
  }, [id]);

  function handleActionTap(action: "call" | "whatsapp" | "directions") {
    if (!provider) return;

    if (action === "call") {
      trackEvent("call_tapped", { provider_id: provider.id });
    } else if (action === "whatsapp") {
      trackEvent("whatsapp_tapped", { provider_id: provider.id });
    } else if (action === "directions") {
      trackEvent("directions_tapped", { provider_id: provider.id });
    }
  }

  // Get current day key (0 is Sunday in JS, so convert to mon=0 ... sun=6)
  const currentDayIndex = (new Date().getDay() + 6) % 7;
  const currentDayKey = DAYS_ORDER[currentDayIndex];

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse py-6">
        <div className="h-6 w-24 bg-slate-200 rounded" />
        <div className="h-8 bg-slate-200 rounded w-3/4" />
        <div className="h-4 bg-slate-200 rounded w-1/2" />
        <div className="h-32 bg-slate-200 rounded-2xl" />
        <div className="h-40 bg-slate-200 rounded-2xl" />
      </div>
    );
  }

  if (error || !provider) {
    return (
      <div className="p-8 text-center space-y-4">
        <AlertCircle className="h-10 w-10 text-red-500 mx-auto" />
        <h3 className="text-base font-bold text-slate-900">Provider not found</h3>
        <p className="text-xs text-slate-500">{error || "Could not load profile details."}</p>
        <Link
          href="/"
          className="inline-block bg-slate-900 text-white text-xs font-bold py-2.5 px-4 rounded-xl"
        >
          Return to search
        </Link>
      </div>
    );
  }

  // Google Maps directions URL
  const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${provider.lat},${provider.lng}`;

  // WhatsApp link (strip non-digits for wa.me)
  const cleanWa = provider.whatsapp?.replace(/[^0-9]/g, "");
  const whatsappUrl = cleanWa
    ? `https://wa.me/${cleanWa}?text=Hello,%20I%20found%20you%20on%20TravelDoc.`
    : null;

  return (
    <div className="space-y-6 pb-24">
      {/* Top back nav */}
      <button
        type="button"
        onClick={() => router.back()}
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 px-3 py-1.5 rounded-xl transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        <span>Back to results</span>
      </button>

      {/* Provider Header Profile */}
      <section className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            {provider.type.replace("_", " ")}
          </span>
          {provider.verification_status === "verified" ? (
            <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Verified Healthcare Facility
            </span>
          ) : (
            <span className="text-xs font-medium text-amber-700 bg-amber-50 px-2.5 py-0.5 rounded-full border border-amber-200">
              Pending Verification
            </span>
          )}
        </div>

        <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900">
          {provider.name}
        </h1>

        <div className="flex items-start gap-2 text-xs text-slate-600">
          <MapPin className="h-4 w-4 text-slate-400 flex-shrink-0 mt-0.5" />
          <span>{provider.address}</span>
        </div>

        {/* Rating badge & walk-in badge */}
        <div className="flex items-center gap-2 pt-2 border-t border-slate-100">
          {provider.average_rating ? (
            <div className="inline-flex items-center gap-1.5 bg-amber-50 border border-amber-200 text-amber-900 rounded-lg px-2.5 py-1 text-xs font-bold">
              <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-500" />
              <span>{provider.average_rating.toFixed(1)} / 5.0</span>
              <span className="text-slate-400 text-[11px]">({provider.review_count} reviews)</span>
            </div>
          ) : (
            <span className="text-xs text-slate-400 font-medium bg-slate-50 px-2 py-1 rounded-md">
              No reviews yet
            </span>
          )}

          {provider.walk_in_available && (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg">
              ✓ Walk-ins welcome
            </span>
          )}
        </div>
      </section>

      {/* Opening Hours Schedule */}
      <section className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-emerald-600" />
          <h2 className="text-sm font-bold text-slate-900">Opening Hours</h2>
        </div>

        {provider.opening_hours?.["24x7"] ? (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-950 p-3 rounded-xl text-xs font-bold flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            Open 24 hours a day, 7 days a week (Emergency & Inpatient)
          </div>
        ) : (
          <div className="divide-y divide-slate-100 text-xs">
            {DAYS_ORDER.map((dayKey) => {
              const isToday = dayKey === currentDayKey;
              const slots = provider.opening_hours?.[dayKey] || [];
              const isClosed = slots.length === 0;

              return (
                <div
                  key={dayKey}
                  className={`flex items-center justify-between py-2 px-2.5 rounded-lg transition-colors ${
                    isToday ? "bg-emerald-50 font-bold text-emerald-950" : "text-slate-600"
                  }`}
                >
                  <span className="capitalize flex items-center gap-1.5">
                    {DAY_LABELS[dayKey]}
                    {isToday && (
                      <span className="text-[10px] bg-emerald-600 text-white px-1.5 py-0.2 rounded-full">
                        Today
                      </span>
                    )}
                  </span>
                  <span>
                    {isClosed
                      ? "Closed"
                      : slots.map((s: any) => `${s.open} – ${s.close}`).join(", ")}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Doctors & Spoken Languages */}
      <section className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
        <div className="flex items-center gap-2">
          <UserCheck className="h-4 w-4 text-emerald-600" />
          <h2 className="text-sm font-bold text-slate-900">
            Attending Doctors ({provider.doctors.length})
          </h2>
        </div>

        <div className="space-y-3 divide-y divide-slate-100">
          {provider.doctors.map((doc) => (
            <div key={doc.id} className="pt-3 first:pt-0 space-y-1.5">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">{doc.full_name}</h3>
                  {doc.qualifications && (
                    <p className="text-[11px] text-slate-500">{doc.qualifications}</p>
                  )}
                </div>
                {doc.specialty && (
                  <span className="text-[11px] font-semibold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-md">
                    {doc.specialty.name}
                  </span>
                )}
              </div>

              {/* Doctor's languages */}
              {doc.languages.length > 0 && (
                <div className="flex items-center gap-1.5 flex-wrap text-[11px]">
                  <span className="text-slate-400">Speaks:</span>
                  {doc.languages.map((dl, idx) => (
                    <span
                      key={idx}
                      className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded-md font-medium"
                    >
                      {dl.language.name} ({dl.proficiency})
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Upfront Price Table */}
      <section className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Tag className="h-4 w-4 text-emerald-600" />
            <h2 className="text-sm font-bold text-slate-900">Upfront Price Estimates</h2>
          </div>
          <span className="text-[10px] text-slate-400">INR (₹)</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-400 font-semibold">
                <th className="pb-2">Service</th>
                <th className="pb-2 text-right">Price Range</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {provider.services.map((svc) => (
                <tr key={svc.id} className="py-2.5">
                  <td className="py-2.5 text-slate-800 font-medium capitalize">
                    {svc.name.replace(/_/g, " ")}
                  </td>
                  <td className="py-2.5 text-right font-bold text-slate-900">
                    {svc.price_min && svc.price_max
                      ? `₹${Math.round(svc.price_min)} – ₹${Math.round(svc.price_max)}`
                      : "Inquire at desk"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[11px] text-slate-400 pt-1">
          Prices verified with provider. Additional procedures, tests, or medication will be billed separately.
        </p>
      </section>

      {/* Leave Feedback Section */}
      <section className="bg-slate-50 rounded-2xl border border-slate-200 p-5 text-center space-y-2">
        <MessageSquare className="h-6 w-6 text-emerald-600 mx-auto" />
        <h3 className="text-sm font-bold text-slate-900">Visited this clinic?</h3>
        <p className="text-xs text-slate-500 max-w-xs mx-auto">
          Help fellow travelers by sharing how much you paid and how your experience was.
        </p>
        <button
          type="button"
          onClick={() => setShowFeedbackModal(!showFeedbackModal)}
          className="inline-block mt-2 bg-white border border-slate-300 text-slate-800 text-xs font-bold py-2 px-4 rounded-xl hover:bg-slate-50 transition-colors shadow-sm"
        >
          {showFeedbackModal ? "Hide feedback form" : "Leave visit feedback"}
        </button>

        {showFeedbackModal && (
          <div className="pt-4 text-left">
            <FeedbackForm
              providerId={provider.id}
              providerName={provider.name}
              onSuccess={() => {
                setTimeout(() => setShowFeedbackModal(false), 3000);
              }}
            />
          </div>
        )}
      </section>

      {/* Sticky Bottom Action Bar */}
      <div className="fixed bottom-0 inset-x-0 bg-white border-t border-slate-200 p-3 z-40 shadow-lg">
        <div className="max-w-lg mx-auto flex items-center gap-2">
          {provider.phone && (
            <a
              href={`tel:${provider.phone}`}
              onClick={() => handleActionTap("call")}
              className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 px-3 rounded-xl text-xs sm:text-sm text-center flex items-center justify-center gap-1.5 shadow-sm transition-colors"
            >
              <Phone className="h-4 w-4" />
              <span>Call</span>
            </a>
          )}

          {whatsappUrl && (
            <a
              href={whatsappUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => handleActionTap("whatsapp")}
              className="flex-1 bg-green-500 hover:bg-green-600 text-white font-bold py-3 px-3 rounded-xl text-xs sm:text-sm text-center flex items-center justify-center gap-1.5 shadow-sm transition-colors"
            >
              <MessageCircle className="h-4 w-4" />
              <span>WhatsApp</span>
            </a>
          )}

          <a
            href={directionsUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => handleActionTap("directions")}
            className="flex-1 bg-slate-900 hover:bg-slate-800 text-white font-bold py-3 px-3 rounded-xl text-xs sm:text-sm text-center flex items-center justify-center gap-1.5 shadow-sm transition-colors"
          >
            <Navigation className="h-4 w-4" />
            <span>Directions</span>
          </a>
        </div>
      </div>
    </div>
  );
}

