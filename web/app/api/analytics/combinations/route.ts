import { NextResponse } from "next/server";
import { getSkillCombinations } from "@/lib/data-source";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    return NextResponse.json({ combinations: await getSkillCombinations() });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to load combinations" },
      { status: 500 },
    );
  }
}