import time
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def run_download_script(resume_from=None):
    """
    Run the download_actas.py script

    Args:
        resume_from: Optional resume point to pass to download script
    """
    print(f"\n{'='*60}")
    print(f"Starting download check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    try:
        # Build command
        cmd = [sys.executable, "download_actas.py"]
        if resume_from:
            cmd.extend(["--resume", resume_from])

        # Run the download script
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
            check=False
        )

        if result.returncode == 0:
            print(f"\n✓ Download check completed successfully")
        else:
            print(f"\n✗ Download check completed with errors (exit code: {result.returncode})")

        return result.returncode == 0

    except Exception as e:
        print(f"\n✗ Error running download script: {e}")
        return False

def run_fetch_mesas_script():
    """Run the fetch_mesas.py script to update mesas data"""
    print(f"\n{'='*60}")
    print(f"Updating mesas data at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    try:
        result = subprocess.run(
            [sys.executable, "fetch_mesas.py"],
            capture_output=False,
            text=True,
            check=False
        )

        if result.returncode == 0:
            print(f"\n✓ Mesas data updated successfully")
        else:
            print(f"\n✗ Mesas data update completed with errors (exit code: {result.returncode})")

        return result.returncode == 0

    except Exception as e:
        print(f"\n✗ Error updating mesas data: {e}")
        return False

def monitor_actas(check_interval_minutes=30, update_mesas=True, resume_from=None):
    """
    Monitor and download actas periodically

    Args:
        check_interval_minutes: How often to check for updates (default: 30 minutes)
        update_mesas: Whether to update mesas data before downloading (default: True)
        resume_from: Optional resume point for the first download
    """

    print("="*60)
    print("ACTAS MONITORING SERVICE")
    print("="*60)
    print(f"Check interval: {check_interval_minutes} minutes")
    print(f"Update mesas data: {update_mesas}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print("\nPress Ctrl+C to stop monitoring\n")

    iteration = 0

    try:
        while True:
            iteration += 1
            print(f"\n{'#'*60}")
            print(f"Check iteration #{iteration}")
            print(f"{'#'*60}")

            # Update mesas data if requested
            if update_mesas:
                print("\n[1/2] Updating mesas data...")
                run_fetch_mesas_script()

            # Download actas
            print(f"\n[{'2/2' if update_mesas else '1/1'}] Checking for new/updated actas...")
            # Only use resume_from on first iteration
            run_download_script(resume_from if iteration == 1 else None)

            # Wait for next check
            next_check = datetime.now().timestamp() + (check_interval_minutes * 60)
            next_check_time = datetime.fromtimestamp(next_check).strftime('%Y-%m-%d %H:%M:%S')

            print(f"\n{'='*60}")
            print(f"Waiting {check_interval_minutes} minutes until next check...")
            print(f"Next check at: {next_check_time}")
            print(f"{'='*60}")

            # Sleep with periodic status updates
            sleep_interval = 60  # Update every minute
            remaining_seconds = check_interval_minutes * 60

            while remaining_seconds > 0:
                time.sleep(min(sleep_interval, remaining_seconds))
                remaining_seconds -= sleep_interval

                if remaining_seconds > 0:
                    minutes_left = remaining_seconds // 60
                    seconds_left = remaining_seconds % 60
                    print(f"  Time until next check: {int(minutes_left)}m {int(seconds_left)}s", end='\r')

    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("Monitoring stopped by user")
        print(f"Total iterations completed: {iteration}")
        print(f"Stopped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Monitor and download election actas')
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Check interval in minutes (default: 30)'
    )
    parser.add_argument(
        '--no-update-mesas',
        action='store_true',
        help='Skip updating mesas data before each download check'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (no monitoring)'
    )
    parser.add_argument(
        '--resume',
        type=str,
        help='Resume from a specific point (Format: DEPT-MUNI-ZONA-CENTRO-MESA or partial)',
        metavar='RESUME_POINT'
    )

    args = parser.parse_args()

    if args.once:
        # Run once and exit
        print("Running single check (no monitoring)...\n")

        if not args.no_update_mesas:
            print("[1/2] Updating mesas data...")
            run_fetch_mesas_script()

        print(f"\n[{'2/2' if not args.no_update_mesas else '1/1'}] Checking for new/updated actas...")
        success = run_download_script(resume_from=args.resume)

        sys.exit(0 if success else 1)
    else:
        # Start monitoring
        monitor_actas(
            check_interval_minutes=args.interval,
            update_mesas=not args.no_update_mesas,
            resume_from=args.resume
        )
