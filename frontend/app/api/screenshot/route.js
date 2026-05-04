export const dynamic = 'force-dynamic';
import { NextResponse } from 'next/server';
import { Storage } from '@google-cloud/storage';

const storage = new Storage();

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const uri = searchParams.get('uri'); // gs://bucket/filename

    if (!uri || !uri.startsWith('gs://')) {
      return new NextResponse('Missing or invalid uri', { status: 400 });
    }

    const withoutScheme = uri.replace('gs://', '');
    const slashIndex = withoutScheme.indexOf('/');
    const bucketName = withoutScheme.slice(0, slashIndex);
    const fileName = withoutScheme.slice(slashIndex + 1);

    const [buffer] = await storage.bucket(bucketName).file(fileName).download();

    return new NextResponse(buffer, {
      status: 200,
      headers: {
        'Content-Type': 'image/png',
        'Cache-Control': 'public, max-age=3600',
      },
    });
  } catch (error) {
    console.error('Screenshot proxy error:', error);
    return new NextResponse('Not found', { status: 404 });
  }
}