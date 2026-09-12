import { NextResponse } from "next/server";
import { getInsights } from "@/lib/data-source";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    return NextResponse.json({ insights: await getInsights() });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to load insights" },
      { status: 500 },
    );
  }
}