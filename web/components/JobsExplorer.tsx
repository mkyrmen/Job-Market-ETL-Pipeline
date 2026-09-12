"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight, Loader2, Search } from "lucide-react";
import type { Job, JobsResponse } from "@/lib/types";
import { JobCard } from "@/components/JobCard";
import { SourceBadge } from "@/components/SourceBadge";

const SENIORITY = ["Senior", "Mid Level", "Manager", "Intern", "Entry Level", "Lead", "Junior", "Staff", "Director", "Principal"];
const REMOTE = ["Remote", "Hybrid", "Onsite"];
const EMPLOYMENT = ["Full-time", "Internship", "Contract", "Part-time"];

export function JobsExplorer({ initial }: { initial: JobsResponse }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [data, setData] = useState<JobsResponse>(initial);
  const [loading, setLoading] = useState(false);
  const firstRun = useRef(true);

  const applyable = useCallback(
    (patch: Record<string, string | null>) => {
      const next = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(patch)) {
        if (value) next.set(key, value);
        else next.delete(key);
      }
      return next.toString();
    },
    [searchParams],
  );

  const fetchJobs = useCallback(
    async (qs: string) => {
      setLoading(true);
      try {
        const res = await fetch(`/api/jobs?${qs}`);
        if (!res.ok) throw new Error("Failed to load jobs");
        setData((await res.json()) as JobsResponse);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (firstRun.current) {
      firstRun.current = false;
      return;
    }
    const qs = searchParams.toString();
    void fetchJobs(qs);
  }, [searchParams, fetchJobs]);

  const set = (patch: Record<string, string | null>) => {
    router.push(`/jobs?${applyable(patch)}`, { scroll: false });
  };

  const page = Number(searchParams.get("page") ?? "1") || 1;
  const totalPages = Math.max(1, Math.ceil(data.total / data.pageSize));
  const q = searchParams.get("q") ?? "";

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 basis-64">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            className="input w-full pl-9"
            placeholder="Search titles, companies…"
            defaultValue={q}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                const value = (e.target as HTMLInputElement).value.trim();
                set({ q: value || null, page: null });
              }
            }}
          />
        </div>
        <select
          className="input"
          value={searchParams.get("seniority") ?? ""}
          onChange={(e) => set({ seniority: e.target.value || null, page: null })}
        >
          <option value="">All seniority</option>
          {SENIORITY.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          className="input"
          value={searchParams.get("remote") ?? ""}
          onChange={(e) => set({ remote: e.target.value || null, page: null })}
        >
          <option value="">Any work mode</option>
          {REMOTE.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <select
          className="input"
          value={searchParams.get("employment") ?? ""}
          onChange={(e) => set({ employment: e.target.value || null, page: null })}
        >
          <option value="">Any employment</option>
          {EMPLOYMENT.map((e) => (
            <option key={e} value={e}>{e}</option>
          ))}
        </select>
        <select
          className="input"
          value={searchParams.get("sort") ?? "posted_at"}
          onChange={(e) => set({ sort: e.target.value || null })}
        >
          <option value="posted_at">Newest first</option>
          <option value="salary">Highest salary</option>
          <option value="title">Title A–Z</option>
        </select>
      </div>

      <div className="mb-5 flex items-center justify-between gap-3">
        <p className="text-sm text-slate-400">
          <span className="font-semibold text-slate-200">{data.total.toLocaleString()}</span> postings
        </p>
        <SourceBadge source={data.source} />
      </div>

      {loading ? (
        <div className="flex items-center justify-center gap-2 py-24 text-slate-400">
          <Loader2 className="h-5 w-5 animate-spin" /> Loading…
        </div>
      ) : data.jobs.length === 0 ? (
        <div className="card card-pad py-16 text-center">
          <p className="text-sm text-slate-400">No postings match those filters.</p>
          <button className="btn btn-outline mt-4" onClick={() => router.push("/jobs")}>
            Clear filters
          </button>
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data.jobs.map((job: Job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="mt-8 flex items-center justify-center gap-3">
          <button
            className="btn btn-outline"
            disabled={page <= 1}
            onClick={() => set({ page: String(page - 1) })}
          >
            <ChevronLeft className="h-4 w-4" /> Prev
          </button>
          <span className="font-mono text-xs text-slate-500">
            {page} / {totalPages}
          </span>
          <button
            className="btn btn-outline"
            disabled={page >= totalPages}
            onClick={() => set({ page: String(page + 1) })}
          >
            Next <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}