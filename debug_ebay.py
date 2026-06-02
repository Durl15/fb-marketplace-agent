import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

params = {
    "OPERATION-NAME": "findItemsByKeywords",
    "SERVICE-VERSION": "1.0.0",
    "SECURITY-APPNAME": os.getenv("EBAY_APP_ID"),
    "RESPONSE-DATA-FORMAT": "JSON",
    "keywords": "dewalt",
}

r = requests.get("https://svcs.ebay.com/services/search/FindingService/v1", params=params)
print("Status:", r.status_code)
print("Body:", r.text[:3000])
