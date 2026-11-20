"use client";

import { NeedCategory } from "@/lib/types";

interface NeedChipsProps {
  categories: NeedCategory[];
  selectedKey: string;
  onSelect: (key: string) => void;
}

export function NeedChips({ categories, selectedKey, onSelect }: NeedChipsProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
      {categories.map((cat) => {
        const isSelected = selectedKey === cat.key;
        return (
          <button
            key={cat.key}
            type="button"
            onClick={() => onSelect(cat.key)}
            className={`flex items-center space-x-2.5 p-3.5 rounded-xl border text-left transition-all duration-150 select-none ${
              isSelected
                ? "border-emerald-600 bg-emerald-50 text-emerald-950 shadow-sm ring-2 ring-emerald-500/30"
                : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50 text-slate-800"
            }`}
          >
            <span className="text-2xl flex-shrink-0" role="img" aria-label={cat.label}>
              {cat.icon}
            </span>
            <span className="font-medium text-sm leading-tight">{cat.label}</span>
          </button>
        );
      })}
    </div>
  );
}

