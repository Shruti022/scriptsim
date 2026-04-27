import { NextResponse } from 'next/server';
import { initializeApp, getApps } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';

if (!getApps().length) {
  initializeApp();
}

const db = getFirestore();

export async function GET() {
  try {
    const scansRef = db.collection('scans');
    const scansSnapshot = await scansRef.orderBy('created_at', 'desc').limit(1).get();
    
    if (scansSnapshot.empty) {
      return NextResponse.json({ activity: [] });
    }
    
    const latestScanId = scansSnapshot.docs[0].id;
    const activityRef = db.collection(`scans/${latestScanId}/activity`);
    const activitySnapshot = await activityRef.orderBy('timestamp', 'asc').limit(50).get();
    
    const activity = activitySnapshot.docs.map(doc => {
      const data = doc.data();
      let timestamp = new Date().toISOString();
      if (data.timestamp && typeof data.timestamp.toDate === 'function') {
        timestamp = data.timestamp.toDate().toISOString();
      }
      return {
        id: doc.id,
        ...data,
        timestamp
      };
    });
    
    return NextResponse.json({ scanId: latestScanId, activity });
    
  } catch (error) {
    console.error('Activity API Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
