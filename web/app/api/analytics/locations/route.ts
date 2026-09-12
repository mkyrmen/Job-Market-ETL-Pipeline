import { NextResponse } from "next/server";
import { getJobsByLocation } from "@/lib/data-source";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    return NextResponse.json({ locations: await getJobsByLocation() });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to load locations" },
      { status: 500 },
    );
  }
}