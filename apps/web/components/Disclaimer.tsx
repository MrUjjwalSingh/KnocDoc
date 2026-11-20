export function Disclaimer() {
  return (
    <footer className="mt-12 py-6 border-t border-slate-200 bg-slate-50 text-center text-xs text-slate-500 px-4">
      <p className="max-w-md mx-auto">
        TravelDoc connects you with independent healthcare providers. We do NOT diagnose, treat, or give medical advice.
      </p>
      <p className="mt-1 text-[11px] text-slate-400">
        &copy; {new Date().getFullYear()} TravelDoc Prototype
      </p>
    </footer>
  );
}

