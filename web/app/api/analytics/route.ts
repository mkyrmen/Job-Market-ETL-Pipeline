import { NextResponse } from "next/server";
import { getAnalyticsBundle } from "@/lib/data-source";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const bundle = await getAnalyticsBundle();
    return NextResponse.json(bundle);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to compute analytics" },
      { status: 500 },
    );
  }
}