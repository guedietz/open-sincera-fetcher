import csv
import time
import requests
from typing import Dict, List, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import os

# Configuration
INPUT_FILE = "domains.txt"
OUTPUT_FILE_PREFIX = "open-sincera-io_results"
REQUEST_DELAY = 1.4  # seconds between requests

# Load environment variables from .env file
load_dotenv()


def read_domains(filepath: str) -> List[str]:
    """Read domains from a text file, one per line."""
    domains = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            domain = line.strip()
            if domain and not domain.startswith('#'):
                domains.append(domain)
    return domains


def query_sincera_api(domain: str, bearer_token: str) -> Dict[str, Any]:
    """Query the Open Sincera API for a given domain."""
    url = f"https://open.sincera.io/api/publishers?domain={domain}"
    
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error querying {domain}: {e}")
        return None


def flatten_data(domain: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten the API response into a single row for CSV."""
    # Add all publisher fields based on the API documentation
    fields = [
        "publisher_id",
        "name",
        "visit_enabled",
        "status",
        "primary_supply_type",
        "domain",
        "pub_description",
        "categories",
        "slug",
        "avg_ads_to_content_ratio",
        "avg_ads_in_view",
        "avg_ad_refresh",
        "total_unique_gpids",
        "id_absorption_rate",
        "avg_page_weight",
        "avg_cpu",
        "total_supply_paths",
        "reseller_count",
        "owner_domain",
        "updated_at"
    ]
    
    # Initialize row with domain and all fields empty
    row = {"domain": domain}
    for field in fields:
        row[field] = ""
    
    # If no data, mark as error and return
    if not data:
        row["error"] = "No data returned"
        return row
    
    # Fill in the data we have
    row["error"] = ""  # No error if we got data
    for field in fields:
        value = data.get(field, "")
        # Convert lists and dicts to strings for CSV compatibility
        if isinstance(value, (list, dict)):
            row[field] = str(value)
        else:
            row[field] = value
    
    return row


def fetch_domains(domains: List[str], output_file: str, bearer_token: str, delay: float = REQUEST_DELAY):
    """Fetch data for all domains and save to CSV."""
    results = []
    total = len(domains)
    
    print(f"Start fetching of {total} domains...")
    print(f"Results will be saved to: {output_file}\n")
    
    for i, domain in enumerate(domains, 1):
        print(f"[{i}/{total}] Querying {domain}...", end=" ")
        
        data = query_sincera_api(domain, bearer_token)
        row = flatten_data(domain, data)
        results.append(row)
        
        print("✓" if data else "✗")
        
        # Rate limiting
        if i < total:
            time.sleep(delay)
    
    # Write to CSV
    if results:
        fieldnames = results[0].keys()
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        print(f"\n✓ Saved {len(results)} results to {output_file}")
    else:
        print("\n✗ No results to save")


def main():
    # Check if .env file exists
    if not Path('.env').exists():
        print("Error: .env file not found!")
        print("Please create a .env file with:")
        print("SINCERA_API_TOKEN=your_bearer_token_here")
        return
    
    # Get bearer token from environment
    bearer_token = os.getenv('SINCERA_API_TOKEN')
    
    if not bearer_token:
        print("Error: SINCERA_API_TOKEN not found in .env file")
        print("Please add: SINCERA_API_TOKEN=your_bearer_token_here")
        return
    
    # Check if input file exists
    if not Path(INPUT_FILE).exists():
        print(f"Error: Input file '{INPUT_FILE}' not found!")
        print(f"Please create a {INPUT_FILE} file with one domain per line")
        return
    
    # Read domains and fetch
    domains = read_domains(INPUT_FILE)
    
    if not domains:
        print(f"Error: No domains found in {INPUT_FILE}")
        return
    
    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{OUTPUT_FILE_PREFIX}_{timestamp}.csv"
    
    print(f"Found {len(domains)} domains in {INPUT_FILE}")
    fetch_domains(domains, output_file, bearer_token)


if __name__ == "__main__":
    main()