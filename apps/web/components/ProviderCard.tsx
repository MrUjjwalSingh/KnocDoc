"use client";

import Link from "next/link";
import { CheckCircle2, Clock, MapPin, Star, Languages, Tag, ChevronRight } from "lucide-react";
import { ProviderSummary } from "@/lib/types";

interface ProviderCardProps {
  provider: ProviderSummary;
  rank?: number;
}

export function ProviderCard({ provider, rank }: ProviderCardProps) {
  return (
    <Link
      href={`/providers/${provider.id}`}
      className="block bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md hover:border-slate-300 transition-all overflow-hidden relative group p-4 sm:p-5"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            {rank !== undefined && (
              <span className="text-xs font-bold text-slate-400 bg-slate-100 rounded-md px-1.5 py-0.5">
                #{rank}
              </span>
            )}
            <span className="text-xs font-semibold capitalize text-slate-500">
              {provider.type.replace("_", " ")}
            </span>
            {provider.verification_status === "verified" ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                <CheckCircle2 className="h-3 w-3" />
                Verified
              </span>
            ) : (
              <span className="text-[11px] font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                Pending verification
              </span>
            )}
          </div>

          <h3 className="text-base sm:text-lg font-bold text-slate-900 truncate group-hover:text-emerald-700 transition-colors">
            {provider.name}
          </h3>

          <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
            <span className="inline-flex items-center gap-1 font-medium text-slate-700">
              <MapPin className="h-3.5 w-3.5 text-slate-400" />
              {provider.distance_km} km away
            </span>
            <span>&bull;</span>
            <span className="truncate">{provider.address}</span>
          </div>
        </div>

        {/* Rating */}
        <div className="flex flex-col items-end flex-shrink-0">
          {provider.average_rating ? (
            <div className="flex items-center gap-1 bg-amber-50 border border-amber-200 text-amber-900 rounded-lg px-2 py-1 text-xs font-bold">
              <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-500" />
              <span>{provider.average_rating.toFixed(1)}</span>
              <span className="text-slate-400 text-[10px]">({provider.review_count})</span>
            </div>
          ) : (
            <span className="text-[11px] text-slate-400 font-medium">New</span>
          )}
        </div>
      </div>

      {/* Badges row: Open now / Walk-in, Price */}
      <div className="flex items-center gap-2 flex-wrap mt-3 pt-3 border-t border-slate-100 text-xs">
        {provider.is_open_now ? (
          <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold bg-emerald-50 px-2.5 py-1 rounded-md">
            <Clock className="h-3.5 w-3.5 text-emerald-600" />
            Open now
          </span>
        ) : provider.walk_in_available ? (
          <span className="inline-flex items-center gap-1 text-amber-800 font-medium bg-amber-50 px-2.5 py-1 rounded-md">
            <Clock className="h-3.5 w-3.5 text-amber-600" />
            Walk-in accepted
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-slate-500 font-medium bg-slate-100 px-2.5 py-1 rounded-md">
            Closed
          </span>
        )}

        {provider.price_range && (
          <span className="inline-flex items-center gap-1 font-semibold text-slate-700 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-md">
            <Tag className="h-3 w-3 text-slate-400" />
            {provider.price_range}
          </span>
        )}

        <div className="inline-flex items-center gap-1 text-slate-600 bg-slate-50 px-2.5 py-1 rounded-md">
          <Languages className="h-3.5 w-3.5 text-slate-400" />
          <span className="truncate max-w-[150px]">
            {provider.language_names.slice(0, 3).join(", ")}
            {provider.language_names.length > 3 && ` +${provider.language_names.length - 3}`}
          </span>
        </div>
      </div>

      {/* Match reasons chips */}
      {provider.match_reasons.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap mt-2.5">
          {provider.match_reasons.map((reason, idx) => (
            <span
              key={idx}
              className="text-[11px] font-medium text-emerald-800 bg-emerald-50/80 px-2 py-0.5 rounded-full"
            >
              ✓ {reason}
            </span>
          ))}
        </div>
      )}

      <div className="absolute right-3 bottom-3 text-slate-300 group-hover:text-slate-600 transition-colors">
        <ChevronRight className="h-4 w-4" />
      </div>
    </Link>
  );
}

