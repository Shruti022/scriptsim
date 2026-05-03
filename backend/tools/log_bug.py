import json
import time
try:
    from tools.browser import get_page
except ImportError:
    from browser import get_page


async def log_bug(scan_id: str, persona: str, description: str, severity: int, screenshot_url: str = "") -> str:
    """Log a discovered bug to Firestore during a persona scan.
    severity: 1=cosmetic, 2=minor, 3=moderate, 4=major, 5=critical.
    persona: one of kid, power_user, parent, retiree.
    Returns the Firestore document ID of the logged bug."""
    try:
        page = await get_page()
        current_url = page.url

        # Auto-take screenshot if none provided
        if not screenshot_url or not screenshot_url.startswith("gs://"):
            try:
                from tools.take_screenshot import take_screenshot
                result = json.loads(await take_screenshot(label=f"auto-{persona}-bug"))
                screenshot_url = result.get("url", "")
            except Exception:
                pass

        from google.cloud import firestore
        db = firestore.Client()
        bug_ref = (
            db.collection("scans")
            .document(scan_id)
            .collection("bugs")
            .document()
        )
        bug_ref.set({
            "persona": persona,
            "description": description,
            "severity": max(1, min(5, severity)),
            "url": current_url,
            "screenshot_gcs_uri": screenshot_url,  # field name expected by dashboard
            "timestamp": int(time.time()),
        })
        return json.dumps({
            "success": True,
            "bug_id": bug_ref.id,
            "url": current_url,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})