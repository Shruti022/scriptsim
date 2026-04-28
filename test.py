import requests
print(requests.post("http://localhost:8000/scan", json={"url":"http://localhost:5000", "personas":["kid"], "scan_mode":"fast"}).json())
