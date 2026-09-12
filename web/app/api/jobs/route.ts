import { NextResponse } from "next/server";
import { listJobs } from "@/lib/data-source";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const filters = Object.fromEntries(searchParams.entries());
    const result = await listJobs(filters);
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to load jobs" },
      { status: 500 },
    );
  }
}