export const dynamic = 'force-dynamic';
import { NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const url = searchParams.get('url');
  const res = await fetch(`${BACKEND}/session-status?url=${encodeURIComponent(url)}`);
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
