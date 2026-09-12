"use client";

import { AlertTriangle } from "lucide-react";

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-rose-500/15 text-rose-400 ring-1 ring-rose-500/30">
        <AlertTriangle className="h-6 w-6" />
      </span>
      <h1 className="mt-4 text-lg font-semibold text-slate-100">Something went wrong</h1>
      <p className="mt-1 max-w-sm text-sm text-slate-400">
        The data source could not be reached. Check that Supabase is configured or that the seed
        snapshot (data/web_seed.json) exists.
      </p>
      <button onClick={reset} className="btn btn-outline mt-6">
        Try again
      </button>
    </div>
  );
}