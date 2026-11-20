"use client";

import { useState } from "react";
import { Star, CheckCircle, AlertCircle } from "lucide-react";
import { submitReview } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";

interface FeedbackFormProps {
  providerId: string;
  providerName: string;
  onSuccess?: () => void;
}

export function FeedbackForm({ providerId, providerName, onSuccess }: FeedbackFormProps) {
  const [rating, setRating] = useState<number>(0);
  const [hoverRating, setHoverRating] = useState<number>(0);
  const [amountPaid, setAmountPaid] = useState<string>("");
  const [comment, setComment] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isSuccess, setIsSuccess] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (rating === 0) {
      setError("Please select a star rating (1–5).");
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      await submitReview({
        provider_id: providerId,
        rating,
        actual_amount_paid: amountPaid ? parseFloat(amountPaid) : undefined,
        comment: comment.trim() || undefined,
      });

      trackEvent("feedback_submitted", {
        provider_id: providerId,
        rating,
        amount_paid: amountPaid ? parseFloat(amountPaid) : null,
      });

      setIsSuccess(true);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setError(err.message || "Failed to submit feedback. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isSuccess) {
    return (
      <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-6 text-center">
        <CheckCircle className="h-10 w-10 text-emerald-600 mx-auto mb-2" />
        <h4 className="text-base font-bold text-emerald-950">Thank you for your feedback!</h4>
        <p className="text-xs text-emerald-800 mt-1">
          Your review will help fellow travelers find trusted healthcare in Goa. Reviews are moderated before appearing publicly.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
      <div>
        <h4 className="text-base font-bold text-slate-900">Leave visit feedback</h4>
        <p className="text-xs text-slate-500 mt-0.5">
          Share your experience with {providerName} to help other travelers.
        </p>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 flex-shrink-0 text-red-500" />
          <span>{error}</span>
        </div>
      )}

      {/* Star rating */}
      <div>
        <label className="block text-xs font-semibold text-slate-700 mb-1">
          How was your visit? <span className="text-red-500">*</span>
        </label>
        <div className="flex items-center gap-2">
          {[1, 2, 3, 4, 5].map((star) => (
            <button
              key={star}
              type="button"
              onClick={() => setRating(star)}
              onMouseEnter={() => setHoverRating(star)}
              onMouseLeave={() => setHoverRating(0)}
              className="p-1 focus:outline-none focus:ring-2 focus:ring-emerald-500 rounded"
              aria-label={`Rate ${star} star${star > 1 ? "s" : ""}`}
            >
              <Star
                className={`h-7 w-7 transition-colors ${
                  (hoverRating || rating) >= star
                    ? "fill-amber-400 text-amber-500"
                    : "text-slate-200 hover:text-slate-300"
                }`}
              />
            </button>
          ))}
          <span className="text-xs text-slate-500 font-medium ml-2">
            {rating ? `${rating} of 5 stars` : "Select rating"}
          </span>
        </div>
      </div>

      {/* Amount paid */}
      <div>
        <label className="block text-xs font-semibold text-slate-700 mb-1">
          Actual amount paid (optional)
        </label>
        <div className="relative rounded-xl shadow-sm">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
            <span className="text-slate-400 text-sm">₹</span>
          </div>
          <input
            type="number"
            min="0"
            step="1"
            value={amountPaid}
            onChange={(e) => setAmountPaid(e.target.value)}
            placeholder="e.g. 500"
            className="block w-full rounded-xl border border-slate-200 py-2.5 pl-8 pr-3 text-sm focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
          />
        </div>
        <p className="text-[11px] text-slate-400 mt-1">
          Helps travelers know real price expectations.
        </p>
      </div>

      {/* Comment */}
      <div>
        <label className="block text-xs font-semibold text-slate-700 mb-1">
          Comments / advice for travelers (optional)
        </label>
        <textarea
          rows={3}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="e.g. English spoken, quick walk-in registration, clean facilities..."
          className="block w-full rounded-xl border border-slate-200 p-3 text-sm focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 resize-none"
        />
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2.5 px-4 rounded-xl text-sm transition-colors shadow-sm disabled:opacity-50"
      >
        {isSubmitting ? "Submitting..." : "Submit feedback"}
      </button>
    </form>
  );
}

