import { NextResponse } from "next/server";
import { getSeniority } from "@/lib/data-source";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    return NextResponse.json({ seniority: await getSeniority() });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to load seniority" },
      { status: 500 },
    );
  }
}