import { NextResponse } from 'next/server';
import { Storage } from '@google-cloud/storage';
import { initializeApp, getApps } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';

// Initialize Firebase Admin (uses Application Default Credentials in GCP)
if (!getApps().length) {
  initializeApp();
}

const db = getFirestore();
const storage = new Storage();

export async function GET() {
  try {
    // 1. Find the most recent scan
    const scansRef = db.collection('scans');
    const scansSnapshot = await scansRef.orderBy('created_at', 'desc').limit(1).get();
    
    if (scansSnapshot.empty) {
      return NextResponse.json({ bugs: [] });
    }
    
    const latestScanId = scansSnapshot.docs[0].id;
    
    // 2. Fetch bugs for that scan
    const bugsRef = db.collection(`scans/${latestScanId}/bugs`);
    const bugsSnapshot = await bugsRef.orderBy('severity', 'desc').get();
    
    const bugs = [];
    for (const doc of bugsSnapshot.docs) {
      const bugData = doc.data();
      
      // 3. Convert gs:// URI to signed URL
      let signedUrl = null;
      if (bugData.screenshot_gcs_uri && bugData.screenshot_gcs_uri.startsWith('gs://')) {
        try {
          const parts = bugData.screenshot_gcs_uri.replace('gs://', '').split('/');
          const bucketName = parts[0];
          const fileName = parts.slice(1).join('/');
          
          const options = {
            version: 'v4',
            action: 'read',
            expires: Date.now() + 15 * 60 * 1000, // 15 minutes
          };
          
          const [url] = await storage
            .bucket(bucketName)
            .file(fileName)
            .getSignedUrl(options);
            
          signedUrl = url;
        } catch (err) {
          console.error(`Failed to sign URL for ${bugData.screenshot_gcs_uri}:`, err);
        }
      }
      
      bugs.push({
        ...bugData,
        signed_screenshot_url: signedUrl
      });
    }
    
    return NextResponse.json({ scanId: latestScanId, bugs });
    
  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
