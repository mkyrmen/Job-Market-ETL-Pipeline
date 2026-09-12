import { NextResponse } from "next/server";
import { getTopSkills } from "@/lib/data-source";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    return NextResponse.json({ skills: await getTopSkills() });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to load skills" },
      { status: 500 },
    );
  }
}