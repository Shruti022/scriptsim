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

    // Always fetch live bugs from subcollection — these have reliable screenshot URIs
    // logged directly by log_bug.py, indexed by persona
    const liveBugsSnap = await db.collection(`scans/${latestScanId}/bugs`).get();
    const screenshotByPersona = {};
    liveBugsSnap.docs.forEach(doc => {
      const d = doc.data();
      const uri = d.screenshot_gcs_uri || d.screenshot_url || '';
      if (uri.startsWith('gs://') && d.persona && !screenshotByPersona[d.persona]) {
        screenshotByPersona[d.persona] = uri;
      }
    });

    let rawBugs = [];
    if (scanData.status === 'completed' && scanData.report && scanData.report.bugs) {
      rawBugs = scanData.report.bugs;
    } else {
      rawBugs = liveBugsSnap.docs.map(doc => doc.data()).sort((a, b) => (b.severity || 0) - (a.severity || 0));
    }

    const bugs = rawBugs.map(bugData => {
      // Try the URI embedded in the bug first, then fall back to any screenshot
      // captured by the same persona in the live subcollection
      let uri = bugData.screenshot_gcs_uri || bugData.screenshot_url || '';
      if (!uri.startsWith('gs://')) {
        const personas = bugData.personas_affected || (bugData.persona ? [bugData.persona] : []);
        for (const p of personas) {
          if (screenshotByPersona[p]) { uri = screenshotByPersona[p]; break; }
        }
      }
      const screenshotUrl = uri.startsWith('gs://')
        ? `/api/screenshot?uri=${encodeURIComponent(uri)}`
        : null;
      return { ...bugData, signed_screenshot_url: screenshotUrl };
    });

    // Include top-level summary fields when scan is complete (from EvalAgent final report)
    const summary = (scanData.status === 'completed' && scanData.report) ? {
      scan_summary: scanData.report.scan_summary || null,
      total_bugs: scanData.report.total_bugs ?? bugs.length,
      critical_count: scanData.report.critical_count ?? 0,
      major_count: scanData.report.major_count ?? 0,
      metrics: scanData.report.metrics || [],
    } : null;

    return NextResponse.json({ scanId: latestScanId, bugs, summary });

  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}