import { NextResponse } from "next/server";
import { getJobsOverTime, getSkillTrends } from "@/lib/data-source";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const [overTime, skillTrends] = await Promise.all([getJobsOverTime(), getSkillTrends()]);
    return NextResponse.json({ overTime, skillTrends });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to load trends" },
      { status: 500 },
    );
  }
}