#!/usr/bin/env python3
"""
Health check script for CVVCalendarSync.
Returns exit code 0 if healthy, 1 if unhealthy.
"""

import sys
import requests

def check_health():
    """Check if ClasseViva API is reachable."""
    try:
        response = requests.get("https://web.spaggiari.eu", timeout=5)
        if response.status_code == 200:
            print("Health check passed: ClasseViva API is reachable")
            return 0
        else:
            print(f"Health check failed: Unexpected status code {response.status_code}")
            return 1
    except requests.exceptions.Timeout:
        print("Health check failed: Request timeout")
        return 1
    except requests.exceptions.RequestException as e:
        print(f"Health check failed: {e}")
        return 1
    except Exception as e:
        print(f"Health check failed with unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(check_health())
