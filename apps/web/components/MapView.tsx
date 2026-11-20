"use client";

import { useEffect, useRef } from "react";
import { ProviderSummary } from "@/lib/types";

// NOTE: This Leaflet map is encapsulated in this single component.
// To swap to Google Maps or Mapbox later, replace this implementation
// while keeping the same MapViewProps interface.

interface MapViewProps {
  providers: ProviderSummary[];
  center: [number, number];
  zoom?: number;
  onSelectProvider?: (id: string) => void;
}

export function MapView({ providers, center, zoom = 12, onSelectProvider }: MapViewProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (typeof window === "undefined") return;

    // Dynamically load leaflet on client only
    let isMounted = true;

    async function initMap() {
      const L = await import("leaflet");

      // Inject Leaflet CSS if not already present
      if (!document.getElementById("leaflet-css")) {
        const link = document.createElement("link");
        link.id = "leaflet-css";
        link.rel = "stylesheet";
        link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
        document.head.appendChild(link);
      }

      if (!isMounted || !mapContainerRef.current) return;

      if (!mapInstanceRef.current) {
        const map = L.map(mapContainerRef.current).setView(center, zoom);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
          maxZoom: 19,
        }).addTo(map);

        mapInstanceRef.current = map;
      } else {
        mapInstanceRef.current.setView(center, zoom);
      }

      const map = mapInstanceRef.current;

      // Clear existing markers
      map.eachLayer((layer: any) => {
        if (layer instanceof L.Marker) {
          map.removeLayer(layer);
        }
      });

      // Custom marker icon
      const defaultIcon = L.divIcon({
        className: "custom-map-pin",
        html: `<div style="background-color: #16a34a; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; box-shadow: 0 2px 6px rgba(0,0,0,0.3); border: 2px solid white;">+</div>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      providers.forEach((prov) => {
        if (prov.lat && prov.lng) {
          const marker = L.marker([prov.lat, prov.lng], { icon: defaultIcon }).addTo(map);

          const popupContent = `
            <div style="font-family: sans-serif; padding: 4px;">
              <h4 style="margin: 0 0 4px 0; font-size: 14px; font-weight: bold; color: #0f172a;">${prov.name}</h4>
              <p style="margin: 0 0 4px 0; font-size: 12px; color: #64748b;">${prov.address}</p>
              <div style="font-size: 11px; font-weight: 600; color: #16a34a;">${prov.is_open_now ? "● Open Now" : "Closed"} · ${prov.distance_km} km</div>
              <div style="margin-top: 6px;">
                <a href="/providers/${prov.id}" style="color: #2563eb; font-size: 12px; font-weight: bold; text-decoration: none;">View profile &rarr;</a>
              </div>
            </div>
          `;

          marker.bindPopup(popupContent);

          marker.on("click", () => {
            if (onSelectProvider) onSelectProvider(prov.id);
          });
        }
      });
    }

    initMap();

    return () => {
      isMounted = false;
    };
  }, [providers, center, zoom, onSelectProvider]);

  return (
    <div className="relative w-full h-[400px] sm:h-[500px] rounded-2xl overflow-hidden border border-slate-200 shadow-sm">
      <div ref={mapContainerRef} className="w-full h-full z-0" />
    </div>
  );
}

