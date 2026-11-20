import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { EmergencyBanner } from "@/components/EmergencyBanner";
import { DemoBanner } from "@/components/DemoBanner";
import { Disclaimer } from "@/components/Disclaimer";
import { fetchConfig } from "@/lib/api";

const inter = Inter({ subsets: ["latin"] });

export const viewport: Viewport = {
  themeColor: "#16a34a",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export const metadata: Metadata = {
  title: "TravelDoc — Find Trusted Nearby Doctors Abroad",
  description: "Find nearby, verified doctors and clinics who speak your language with upfront pricing.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "TravelDoc",
  },
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const config = await fetchConfig();

  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
      </head>
      <body className={`${inter.className} flex flex-col min-h-screen bg-slate-50 text-slate-900`}>
        <EmergencyBanner emergencyNumber={config.city_emergency_number} />
        <DemoBanner isDemo={config.is_demo_data} />

        <div className="flex-1 w-full max-w-lg mx-auto bg-white min-h-[calc(100vh-80px)] shadow-sm sm:border-x sm:border-slate-200 flex flex-col">
          <main className="flex-1 p-4 sm:p-6">{children}</main>
          <Disclaimer />
        </div>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  navigator.serviceWorker.register('/sw.js').catch(function(err) {
                    console.debug('ServiceWorker registration skipped:', err);
                  });
                });
              }
            `,
          }}
        />
      </body>
    </html>
  );
}
