import os
import json
from pathlib import Path

def generate_results_metadata():
    """
    Generate a metadata JSON file containing all available result directories
    and their available states (JSON files).
    This should be run whenever new results are added.

    States property logic:
    - No 'states' property: all states are available
    - Empty array: no options available
    - Array with values: only those specific states are available
    """
    # Complete list of all possible states
    ALL_STATES = [
        "TODOS",
        "ATLANTIDA",
        "CHOLUTECA",
        "COLON",
        "COMAYAGUA",
        "COPAN",
        "CORTES",
        "EL PARAISO",
        "FRANCISCO MORAZAN",
        "GRACIAS A DIOS",
        "INTIBUCA",
        "ISLAS DE LA BAHIA",
        "LA PAZ",
        "LEMPIRA",
        "OCOTEPEQUE",
        "OLANCHO",
        "SANTA BARBARA",
        "VALLE",
        "VOTO EN EL EXTERIOR",
        "YORO"
    ]

    results_dir = Path("results")

    if not results_dir.exists():
        print("Results directory not found!")
        return

    # Get all subdirectories (result dates) and their available states
    dates_data = {}
    result_dates = []

    for item in results_dir.iterdir():
        if item.is_dir():
            date_name = item.name
            result_dates.append(date_name)

            # Get all JSON files in this date directory
            states = []
            for json_file in item.glob("*.json"):
                # Get filename without extension (e.g., "TODOS.json" -> "TODOS")
                state_name = json_file.stem
                states.append(state_name)

            # Sort states alphabetically, but put TODOS first
            states.sort()
            if "TODOS" in states:
                states.remove("TODOS")
                states.insert(0, "TODOS")

            # Determine what to store based on the states found
            date_entry = {}
            if len(states) == 0:
                # No states available - store empty array
                date_entry["states"] = []
            elif sorted(states) == sorted(ALL_STATES):
                # All states available - don't include states property
                pass
            else:
                # Partial states - store the specific states
                date_entry["states"] = states

            dates_data[date_name] = date_entry

    # Sort dates in descending order (newest first)
    result_dates.sort(reverse=True)

    metadata = {
        "available_dates": result_dates,
        "latest_date": result_dates[0] if result_dates else None,
        "dates": dates_data
    }

    # Save metadata to JSON file
    with open("results_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"Metadata generated successfully!")
    print(f"Available dates: {len(result_dates)}")
    print(f"Latest date: {metadata['latest_date']}")

    if metadata['latest_date']:
        latest_states = dates_data.get(metadata['latest_date'], {}).get('states', [])
        print(f"States in latest date: {len(latest_states)}")

if __name__ == "__main__":
    generate_results_metadata()
