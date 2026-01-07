# Export Zabbix history/trends to CSV

Script: [get_zabbix_graph_to_csv.py](get_zabbix_graph_to_csv.py)

This script queries Zabbix's JSON-RPC API to export history (`history.get`) and/or trends (`trend.get`) for a given `itemid` into CSV files.

## Overview
- Automatically retrieves host and item names via `item.get`.
- Exports history (all values) and/or trends (min/avg/max), based on options.
- Paginates results in 10,000-row chunks continuously until the full period is covered.
- Produces CSV filenames derived from the host, item, and `itemid`.

## Prerequisites
- Python 3.8+
- Python package `requests`
- Zabbix API access (JSON-RPC URL) and a valid API token.

Install dependencies:

```bash
pip install requests
```

## Configuration
Edit the constants at the top of the script:
- `ZABBIX_URL`: JSON-RPC API URL (e.g., `https://myzabbix/api_jsonrpc.php`).
- `VERIFY_SSL_CERT`: `True` (default) or `False` for self-signed certificates.
- `API_TOKEN`: your Zabbix API token.

Tip: avoid committing secrets. Store the token in a secret manager or a non-versioned file, then inject it at runtime (e.g., via templating or environment/export).

## Usage

```bash
python scripts/get_zabbix_graph_to_csv.py --itemid <ID>
```

Options:
- `--no-history`: do not export history.
- `--no-trend`: do not export trends.

### Finding the itemid
You can obtain the `itemid` directly from Zabbix UI:
- Open a graph for the metric in Zabbix.
- Look at the browser URL and copy the value of `itemids[]`.

Example:

```text
https://my_zabbix_url/history.php?action=showgraph&itemids%5B%5D=53980
# itemid = 53980
```

Examples:
```bash
# Export history + trends for item 12345
python scripts/get_zabbix_graph_to_csv.py --itemid 12345

# Export only trends
python scripts/get_zabbix_graph_to_csv.py --itemid 12345 --no-history

# Export only history
python scripts/get_zabbix_graph_to_csv.py --itemid 12345 --no-trend
```

## Outputs
- History: `<HOST>_<ITEM>_<ITEMID>.csv`
  - Columns: `timestamp`, `datetime`, `value`
- Trends: `<HOST>_<ITEM>_<ITEMID>_trend.csv`
  - Columns: `timestamp`, `datetime`, `value_avg`, `value_min`, `value_max`

Filenames are sanitized to avoid problematic characters.

## Behavior and limits
- Period: from the beginning (`time_from = 0`) to now (`time_till = now`).
- Pagination: requests in blocks of 10,000, sorted by `clock` ASC, then resumed at `last_clock + 1`.
- History types tested: float, int, string, log. The first type returning data is used.

## Troubleshooting
- "Unable to retrieve the item name": check `itemid`, API URL, token, and permissions.
- SSL errors: set `VERIFY_SSL_CERT = False` if you use a self-signed certificate (not recommended in production).
- Empty responses: the item may have no history or trends for the requested period.

## Security
- Never commit your `API_TOKEN` to a public repository.
- Prefer least-privileged permissions for the token.
