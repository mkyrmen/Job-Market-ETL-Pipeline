import { NextResponse } from "next/server";
import { getJobsByCompany } from "@/lib/data-source";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    return NextResponse.json({ companies: await getJobsByCompany() });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to load companies" },
      { status: 500 },
    );
  }
}