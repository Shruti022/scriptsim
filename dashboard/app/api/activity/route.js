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
      if (!scanDoc.exists) return NextResponse.json({ activity: [] });
      scanData = scanDoc.data();
    } else {
      const scansRef = db.collection('scans');
      const scansSnapshot = await scansRef.orderBy('created_at', 'desc').limit(1).get();
      
      if (scansSnapshot.empty) {
        return NextResponse.json({ activity: [] });
      }
      latestScanId = scansSnapshot.docs[0].id;
      scanData = scansSnapshot.docs[0].data();
    }
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
    
    return NextResponse.json({ 
      scanId: latestScanId, 
      scanStatus: scanData.status || 'unknown',
      activity 
    });
    
  } catch (error) {
    console.error('Activity API Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
