import requests
import csv
from datetime import datetime
import argparse
import re
import sys

# -----------------------------
# CONFIGURATION
# -----------------------------
ZABBIX_URL = "your_zabbix_url/api_jsonrpc.php"
# Examples:
# ZABBIX_URL = "https://myzabbix.test/api_jsonrpc.php"
# ZABBIX_URL = "http://myzabbix.test/api_jsonrpc.php"

VERIFY_SSL_CERT = True  # Set to False if Zabbix uses a self-signed SSL certificate

API_TOKEN = "YOUR_API_TOKEN_HERE"


HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

TIME_FROM = 0
TIME_TILL = int(datetime.now().timestamp())

# -----------------------------
# ARGUMENTS
# -----------------------------
parser = argparse.ArgumentParser(description="Export Zabbix history/trend in CSV")
parser.add_argument("--itemid", required=True, help="ID of the item")
parser.add_argument("--no-history", action="store_true", help="Do not export history")
parser.add_argument("--no-trend", action="store_true", help="Do not export trends")
args = parser.parse_args()

ITEM_ID = args.itemid

# -----------------------------
# UTILS
# -----------------------------
def sanitize_filename(text):
    text = re.sub(r"[^\w\-]", "_", text)
    return re.sub(r"_+", "_", text).strip("_")

# -----------------------------
# RÉCUPÉRATION NOM HOST + ITEM
# -----------------------------
def get_item_and_host_name(item_id):
    payload = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "itemids": item_id,
            "output": ["name"],
            "selectHosts": ["name"]
        },
        "id": 1
    }

    r = requests.post(ZABBIX_URL, headers=HEADERS, json=payload, verify=VERIFY_SSL_CERT)
    r.raise_for_status()
    resp = r.json()

    if "error" in resp or not resp.get("result"):
        print("Impossible de récupérer le nom de l'item")
        sys.exit(1)

    item = resp["result"][0]
    host_name = item["hosts"][0]["name"]
    item_name = item["name"]

    return sanitize_filename(host_name), sanitize_filename(item_name)

HOST_NAME, ITEM_NAME = get_item_and_host_name(ITEM_ID)

HISTORY_FILE = f"{HOST_NAME}_{ITEM_NAME}_{ITEM_ID}.csv"
TREND_FILE   = f"{HOST_NAME}_{ITEM_NAME}_{ITEM_ID}_trend.csv"

# -----------------------------
# HISTORY
# -----------------------------
def fetch_history(item_id):
    type_map = {0: "float", 3: "int", 1: "string", 2: "log"}
    types = [0, 3, 1, 2]

    for htype in types:
        all_data = []
        current_time = TIME_FROM

        print(f"Test history type {type_map[htype]}")

        while True:
            payload = {
                "jsonrpc": "2.0",
                "method": "history.get",
                "params": {
                    "output": "extend",
                    "history": htype,
                    "itemids": item_id,
                    "sortfield": "clock",
                    "sortorder": "ASC",
                    "time_from": current_time,
                    "time_till": TIME_TILL,
                    "limit": 10000
                },
                "id": 2
            }

            r = requests.post(ZABBIX_URL, headers=HEADERS, json=payload, verify=VERIFY_SSL_CERT)
            r.raise_for_status()
            resp = r.json()

            data = resp.get("result", [])
            if not data:
                break

            all_data.extend(data)
            current_time = int(data[-1]["clock"]) + 1

        if all_data:
            return all_data

    return []

# -----------------------------
# TRENDS
# -----------------------------
def fetch_trend(item_id):
    all_data = []
    current_time = TIME_FROM

    while True:
        payload = {
            "jsonrpc": "2.0",
            "method": "trend.get",
            "params": {
                "output": "extend",
                "itemids": item_id,
                "sortfield": "clock",
                "sortorder": "ASC",
                "time_from": current_time,
                "time_till": TIME_TILL,
                "limit": 10000
            },
            "id": 3
        }

        r = requests.post(ZABBIX_URL, headers=HEADERS, json=payload)
        r.raise_for_status()
        resp = r.json()

        data = resp.get("result", [])
        if not data:
            break

        all_data.extend(data)
        current_time = int(data[-1]["clock"]) + 1

    return all_data

# -----------------------------
# EXPORT
# -----------------------------
history_data = [] if args.no_history else fetch_history(ITEM_ID)
trend_data   = [] if args.no_trend else fetch_trend(ITEM_ID)

if history_data:
    with open(HISTORY_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "datetime", "value"])
        for p in history_data:
            ts = int(p["clock"])
            dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([ts, dt, p["value"]])

    print(f"✅ History exported : {HISTORY_FILE} ({len(history_data)} lines)")
else:
    print("ℹ️ No history exported")

if trend_data:
    with open(TREND_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "datetime", "value_avg", "value_min", "value_max"])
        for p in trend_data:
            ts = int(p["clock"])
            dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([ts, dt, p["value_avg"], p["value_min"], p["value_max"]])

    print(f"✅ Trend exported : {TREND_FILE} ({len(trend_data)} lines)")
else:
    print("ℹ️ No trend exported")
