"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BarChart3, Database, Lightbulb, ListFilter, TrendingUp, Radar } from "lucide-react";

const links = [
  { href: "/", label: "Overview", icon: BarChart3 },
  { href: "/jobs", label: "Jobs", icon: ListFilter },
  { href: "/skills", label: "Skills", icon: Radar },
  { href: "/trends", label: "Market trends", icon: TrendingUp },
  { href: "/insights", label: "Insights", icon: Lightbulb },
  { href: "/pipeline", label: "Pipeline", icon: Database },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-ink-700/60 bg-ink-950/80 backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30">
            <Activity className="h-4 w-4" />
          </span>
          <span className="hidden text-sm font-semibold tracking-tight text-slate-100 sm:block">
            Job Market Intelligence
          </span>
        </Link>
        <nav className="flex items-center gap-1 overflow-x-auto scrollbar-thin">
          {links.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  active
                    ? "bg-ink-800 text-emerald-300"
                    : "text-slate-400 hover:bg-ink-800/60 hover:text-slate-200"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}