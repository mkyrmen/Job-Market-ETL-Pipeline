"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { monthLabel } from "@/lib/types";

const PALETTE = [
  "#34d399",
  "#2dd4bf",
  "#60a5fa",
  "#a78bfa",
  "#fbbf24",
  "#fb7185",
  "#22d3ee",
  "#f472b6",
  "#4ade80",
  "#facc15",
];

export function colorAt(i: number): string {
  return PALETTE[i % PALETTE.length];
}

const tooltipStyle = {
  backgroundColor: "rgba(10,16,32,0.95)",
  border: "1px solid #1a2440",
  borderRadius: "0.5rem",
  fontSize: "12px",
  color: "#e2e8f0",
};

export function DonutChart({
  data,
  valueKey = "count",
  nameKey = "label",
  formatValue = (n: number) => n.toLocaleString(),
  centerLabel,
}: {
  data: { label: string; count: number }[];
  valueKey?: string;
  nameKey?: string;
  formatValue?: (n: number) => string;
  centerLabel?: string;
}) {
  const total = data.reduce((sum, d) => sum + d.count, 0);
  return (
    <div className="relative h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey={valueKey}
            nameKey={nameKey}
            innerRadius="58%"
            outerRadius="85%"
            paddingAngle={2}
            strokeWidth={0}
            isAnimationActive={false}
          >
            {data.map((_entry, i) => (
              <Cell key={i} fill={colorAt(i)} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value) => formatValue(Number(value))}
          />
          <Legend
            layout="vertical"
            align="right"
            verticalAlign="middle"
            iconType="circle"
            iconSize={8}
            formatter={(value) => (
              <span className="text-xs text-slate-400">{String(value)}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
      {total > 0 ? (
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center pb-10">
          <span className="font-mono text-2xl font-semibold text-slate-100">
            {total.toLocaleString()}
          </span>
          <span className="label-muted">{centerLabel ?? "total"}</span>
        </div>
      ) : null}
    </div>
  );
}

export function HorizontalBarListChart({
  data,
  formatValue = (n: number) => n.toLocaleString(),
}: {
  data: { label: string; count: number }[];
  formatValue?: (n: number) => string;
}) {
  return (
    <ResponsiveContainer width="100%" height={Math.max(220, data.length * 28)}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24 }}>
        <CartesianGrid horizontal={false} stroke="#1a2440" strokeDasharray="3 3" />
        <XAxis type="number" tick={{ fill: "#64748b", fontSize: 11 }} tickFormatter={formatValue} />
        <YAxis
          type="category"
          dataKey="label"
          width={132}
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
        <Bar dataKey="count" radius={[0, 6, 6, 0]} isAnimationActive={false}>
          {data.map((_entry, i) => (
            <Cell key={i} fill={colorAt(i)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function OverTimeAreaChart({
  data,
}: {
  data: { month: string; job_count: number }[];
}) {
  const labelled = data.map((d) => ({ ...d, label: monthLabel(d.month) }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={labelled} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="gradJobs" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#34d399" stopOpacity={0.45} />
            <stop offset="100%" stopColor="#34d399" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="#1a2440" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fill: "#64748b", fontSize: 11 }} width={36} tickLine={false} axisLine={false} />
        <Tooltip contentStyle={tooltipStyle} />
        <Area
          type="monotone"
          dataKey="job_count"
          stroke="#34d399"
          strokeWidth={2}
          fill="url(#gradJobs)"
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function SkillTrendLineChart({
  data,
}: {
  data: { month: string; skill: string; job_count: number }[];
}) {
  const skills = [...new Set(data.map((d) => d.skill))];
  const months = [...new Set(data.map((d) => d.month))].sort();
  const series = skills.map((skill, si) => {
    const byMonth = new Map<string, number>();
    for (const d of data) {
      if (d.skill === skill) byMonth.set(d.month, d.job_count);
    }
    return {
      skill,
      color: colorAt(si),
      points: months.map((m) => ({ month: m, label: monthLabel(m), count: byMonth.get(m) ?? 0 })),
    };
  });

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart
        margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
        data={months.map((m) => {
          const row: Record<string, string | number> = { label: monthLabel(m) };
          for (const s of series) row[s.skill] = s.points.find((p) => p.month === m)?.count ?? 0;
          return row;
        })}
      >
        <CartesianGrid stroke="#1a2440" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fill: "#64748b", fontSize: 11 }} width={32} tickLine={false} axisLine={false} />
        <Tooltip contentStyle={tooltipStyle} />
        <Legend
          iconType="circle"
          iconSize={8}
          formatter={(value) => <span className="text-xs text-slate-400">{String(value)}</span>}
        />
        {series.map((s) => (
          <Line
            key={s.skill}
            type="monotone"
            dataKey={s.skill}
            stroke={s.color}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}