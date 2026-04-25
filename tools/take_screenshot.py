import json
import os
import tempfile
import time
try:
    from tools.browser import get_page
except ImportError:
    from browser import get_page


def take_screenshot(label: str = "") -> str:
    """Take a screenshot of the current page and upload it to GCS.
    Use label to describe what's being captured (e.g. 'checkout-error', 'empty-cart').
    Returns the public GCS URL and local path."""
    local_path = ""
    try:
        page = get_page()
        timestamp = int(time.time())
        safe_label = label.replace(" ", "_").replace("/", "_")[:40]
        filename = f"{safe_label}_{timestamp}.png" if safe_label else f"screenshot_{timestamp}.png"
        local_path = os.path.join(tempfile.gettempdir(), filename)

        page.screenshot(path=local_path, full_page=False)

        # Upload to GCS — no public access needed, Cloud Run service account handles auth
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket("scriptsim-screenshots")
        blob = bucket.blob(filename)
        blob.upload_from_filename(local_path)

        gcs_url = f"gs://scriptsim-screenshots/{filename}"
        return json.dumps({"success": True, "url": gcs_url, "local_path": local_path})

    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "url": "", "local_path": local_path})


if __name__ == "__main__":
    import sys
    try:
        from tools.browser import start_browser, close_browser
    except ImportError:
        from browser import start_browser, close_browser

    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    label = sys.argv[2] if len(sys.argv) > 2 else "test"
    start_browser(url)
    print(take_screenshot(label))
    close_browser()
