"use client";

import { AlertTriangle, PhoneCall } from "lucide-react";

interface EmergencyBannerProps {
  emergencyNumber?: string;
}

export function EmergencyBanner({ emergencyNumber = "112" }: EmergencyBannerProps) {
  return (
    <aside
      aria-label="Emergency warning"
      className="bg-red-600 text-white px-4 py-2.5 text-xs sm:text-sm font-medium flex items-center justify-between sticky top-0 z-50 shadow-md"
    >
      <div className="flex items-center space-x-2">
        <AlertTriangle className="h-4 w-4 flex-shrink-0 text-amber-200" aria-hidden="true" />
        <span>
          Life-threatening emergency? Call{" "}
          <strong className="underline font-bold tracking-wide">{emergencyNumber}</strong> immediately.
        </span>
      </div>
      <a
        href={`tel:${emergencyNumber}`}
        className="ml-3 inline-flex items-center gap-1 bg-white text-red-700 px-2.5 py-1 rounded-full text-xs font-bold hover:bg-red-50 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-white"
        aria-label={`Call emergency number ${emergencyNumber}`}
      >
        <PhoneCall className="h-3 w-3" />
        Call {emergencyNumber}
      </a>
    </aside>
  );
}

