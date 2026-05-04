export const dynamic = 'force-dynamic';
import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    shopUrl:   process.env.SHOP_URL   || null,
    jobUrl:    process.env.JOB_URL    || null,
    doctorUrl: process.env.DOCTOR_URL || null,
  });
}
