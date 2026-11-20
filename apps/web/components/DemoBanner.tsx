"use client";

import { Info } from "lucide-react";

interface DemoBannerProps {
  isDemo?: boolean;
}

export function DemoBanner({ isDemo = true }: DemoBannerProps) {
  if (!isDemo) return null;

  return (
    <div
      role="status"
      className="bg-amber-50 border-b border-amber-200 px-4 py-1.5 text-xs text-amber-900 flex items-center justify-center space-x-1.5 font-medium"
    >
      <Info className="h-3.5 w-3.5 text-amber-600 flex-shrink-0" />
      <span>
        <strong>Demo Prototype:</strong> Doctors, prices, and reviews shown are placeholders.
      </span>
    </div>
  );
}

