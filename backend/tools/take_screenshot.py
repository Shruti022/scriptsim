import json
import os
import tempfile
import time
try:
    from tools.browser import get_page
except ImportError:
    from browser import get_page


async def take_screenshot(label: str = "") -> str:
    """Take a screenshot of the current page and upload it to GCS.
    Use label to describe what's being captured (e.g. 'checkout-error').
    Returns the GCS URI gs://... and local temp path."""
    local_path = ""
    try:
        page = await get_page()
        timestamp = int(time.time())
        safe_label = label.replace(" ", "_").replace("/", "_")[:40]
        filename = f"{safe_label}_{timestamp}.png" if safe_label else f"screenshot_{timestamp}.png"
        local_path = os.path.join(tempfile.gettempdir(), filename)

        print(f"[take_screenshot] Capturing to {local_path}...")
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass # Continue if idle takes too long
        
        await page.screenshot(path=local_path, full_page=False)

        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket("scriptsim-screenshots")
        blob = bucket.blob(filename)
        blob.upload_from_filename(local_path, content_type="image/png")
        print(f"[take_screenshot] Upload complete: {filename} to scriptsim-screenshots")

        gcs_url = f"gs://scriptsim-screenshots/{filename}"
        return json.dumps({"success": True, "url": gcs_url, "local_path": local_path})

    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "url": "", "local_path": local_path})
