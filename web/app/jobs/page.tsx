import { Suspense } from "react";
import { PageHeader } from "@/components/Card";
import { JobsExplorer } from "@/components/JobsExplorer";
import { listJobs } from "@/lib/data-source";

export const dynamic = "force-dynamic";

export default async function JobsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const filters = await searchParams;
  const initial = await listJobs(filters);

  return (
    <>
      <PageHeader
        title="Job explorer"
        subtitle="Search, filter and stack-rank every posting collected by the ETL pipeline."
      />
      <Suspense
        fallback={
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 9 }).map((_, i) => (
              <div key={i} className="h-44 animate-pulse rounded-xl bg-ink-800/70" />
            ))}
          </div>
        }
      >
        <JobsExplorer initial={initial} />
      </Suspense>
    </>
  );
}