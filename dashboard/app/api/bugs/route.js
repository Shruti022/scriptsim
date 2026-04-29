export const dynamic = 'force-dynamic';
import { NextResponse } from 'next/server';
import { initializeApp, getApps } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';

if (!getApps().length) {
  initializeApp();
}

const db = getFirestore();

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const requestedScanId = searchParams.get('scanId');

    let latestScanId = requestedScanId;
    let scanData = null;

    if (requestedScanId) {
      const scanDoc = await db.collection('scans').doc(requestedScanId).get();
      if (!scanDoc.exists) return NextResponse.json({ bugs: [] });
      scanData = scanDoc.data();
    } else {
      const scansSnapshot = await db.collection('scans').orderBy('created_at', 'desc').limit(1).get();
      if (scansSnapshot.empty) return NextResponse.json({ bugs: [] });
      latestScanId = scansSnapshot.docs[0].id;
      scanData = scansSnapshot.docs[0].data();
    }

    let rawBugs = [];
    if (scanData.status === 'completed' && scanData.report && scanData.report.bugs) {
      rawBugs = scanData.report.bugs;
    } else {
      const bugsSnapshot = await db.collection(`scans/${latestScanId}/bugs`).orderBy('severity', 'desc').get();
      rawBugs = bugsSnapshot.docs.map(doc => doc.data());
    }

    const bugs = rawBugs.map(bugData => {
      // Proxy gs:// URIs through our own API route — no signing or public bucket needed
      const uri = bugData.screenshot_gcs_uri || bugData.screenshot_url || '';
      const screenshotUrl = uri.startsWith('gs://')
        ? `/api/screenshot?uri=${encodeURIComponent(uri)}`
        : uri || null;
      return { ...bugData, signed_screenshot_url: screenshotUrl };
    });

    return NextResponse.json({ scanId: latestScanId, bugs });

  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}