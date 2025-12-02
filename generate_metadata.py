import os
import json
from pathlib import Path

def generate_results_metadata():
    """
    Generate a metadata JSON file containing all available result directories.
    This should be run whenever new results are added.
    """
    results_dir = Path("results")

    if not results_dir.exists():
        print("Results directory not found!")
        return

    # Get all subdirectories (result dates)
    result_dates = []
    for item in results_dir.iterdir():
        if item.is_dir():
            result_dates.append(item.name)

    # Sort dates in descending order (newest first)
    result_dates.sort(reverse=True)

    metadata = {
        "available_dates": result_dates,
        "latest_date": result_dates[0] if result_dates else None
    }

    # Save metadata to JSON file
    with open("results_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"Metadata generated successfully!")
    print(f"Available dates: {len(result_dates)}")
    print(f"Latest date: {metadata['latest_date']}")

if __name__ == "__main__":
    generate_results_metadata()
