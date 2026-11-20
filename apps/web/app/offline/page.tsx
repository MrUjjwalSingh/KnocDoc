import Link from "next/link";
import { WifiOff, PhoneCall } from "lucide-react";

export default function OfflinePage() {
  return (
    <div className="py-12 text-center space-y-4">
      <div className="bg-amber-100 text-amber-700 w-16 h-16 rounded-full flex items-center justify-center mx-auto">
        <WifiOff className="h-8 w-8" />
      </div>
      <h1 className="text-xl font-bold text-slate-900">You are offline</h1>
      <p className="text-xs text-slate-500 max-w-xs mx-auto">
        You seem to have lost internet connectivity. Reconnect to search for doctors and clinics.
      </p>

      <div className="bg-red-50 border border-red-200 rounded-2xl p-4 max-w-sm mx-auto text-left space-y-2">
        <p className="text-xs font-bold text-red-900">Emergency Numbers in Goa, India:</p>
        <div className="flex items-center justify-between text-xs text-red-800">
          <span>All Emergencies (National):</span>
          <a href="tel:112" className="font-bold underline flex items-center gap-1">
            <PhoneCall className="h-3 w-3" /> 112
          </a>
        </div>
        <div className="flex items-center justify-between text-xs text-red-800">
          <span>Ambulance Service:</span>
          <a href="tel:108" className="font-bold underline flex items-center gap-1">
            <PhoneCall className="h-3 w-3" /> 108
          </a>
        </div>
      </div>

      <div className="pt-2">
        <Link
          href="/"
          className="inline-block bg-emerald-600 text-white font-bold text-xs py-2.5 px-5 rounded-xl hover:bg-emerald-700"
        >
          Try reconnecting
        </Link>
      </div>
    </div>
  );
}

