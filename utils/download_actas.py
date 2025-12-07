import requests
import json
import hashlib
import time
import os
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs

def calculate_file_hash(file_path):
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def download_file(url, output_path):
    """Download a file from URL to output_path"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            f.write(response.content)

        return True
    except Exception as e:
        print(f"Error downloading file: {e}")
        return False

def load_file_registry(registry_path):
    """Load the file registry that tracks versions and hashes"""
    if registry_path.exists():
        with open(registry_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_file_registry(registry_path, registry):
    """Save the file registry"""
    with open(registry_path, 'w', encoding='utf-8') as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)

def process_mesas_file(mesas_file_path, dept_code, municipio_code, zona_code, centro_code,
                       actas_dir, history_dir, registry, stats, resume_point=None):
    """Process a single mesas.json file and download PDFs"""

    try:
        with open(mesas_file_path, 'r', encoding='utf-8') as f:
            mesas = json.load(f)

        for mesa in mesas:
            mesa_numero = mesa.get('numero')
            pdf_url = mesa.get('nombre_archivo')
            needs_download = mesa.get('needs_download', True)  # Default to True if not set

            if not pdf_url or not mesa_numero:
                continue

            # Skip if this mesa doesn't need downloading
            if not needs_download:
                stats['skipped'] += 1
                continue

            # Check if we should skip based on resume point
            if should_skip_based_on_resume(dept_code, municipio_code, zona_code,
                                          centro_code, mesa_numero, resume_point):
                stats['skipped'] += 1
                continue

            # Create filename: DEPT-MUNI-ZONA-CENTRO-MESA.pdf
            filename = f"{dept_code}-{municipio_code}-{zona_code}-{centro_code}-{mesa_numero}.pdf"

            # Track last processed acta (for resume capability)
            stats['last_processed'] = f"{dept_code}-{municipio_code}-{zona_code}-{centro_code}-{mesa_numero}"
            file_path = actas_dir / filename
            temp_path = actas_dir / f"{filename}.tmp"

            # Create registry key
            registry_key = filename

            # Check if file already exists locally
            if file_path.exists():
                # File exists locally, check registry
                if registry_key in registry:
                    # File is tracked in registry, check if URL changed
                    if registry[registry_key]['url'] == pdf_url:
                        # Same URL, skip download entirely
                        stats['skipped'] += 1
                        continue
                    else:
                        # URL changed, need to download and check
                        should_download = True
                        is_new_file = False
                        stats['updated_urls'] += 1
                else:
                    # File exists but not in registry, add to registry without downloading
                    file_hash = calculate_file_hash(file_path)
                    registry[registry_key] = {
                        'hash': file_hash,
                        'url': pdf_url,
                        'version': 1,
                        'last_updated': datetime.now().strftime('%Y%m%d_%H%M%S'),
                        'mesa_info': {
                            'numero': mesa_numero,
                            'departamento': dept_code,
                            'municipio': municipio_code,
                            'zona': zona_code,
                            'centro': centro_code,
                            'publicada': mesa.get('publicada'),
                            'escrutado': mesa.get('escrutado'),
                            'digitalizado': mesa.get('digitalizado')
                        }
                    }
                    stats['skipped'] += 1
                    continue
            else:
                # File doesn't exist locally, need to download
                should_download = True
                is_new_file = registry_key not in registry
                if is_new_file:
                    stats['new_files'] += 1
                else:
                    stats['updated_urls'] += 1

            if should_download:
                print(f"  Downloading: {filename}...", end=" ")

                if download_file(pdf_url, temp_path):
                    # Calculate hash of downloaded file
                    new_hash = calculate_file_hash(temp_path)

                    # Check if file content actually changed
                    if not is_new_file and registry[registry_key]['hash'] == new_hash:
                        # Same file, no need to keep
                        temp_path.unlink()
                        print("✓ (unchanged)")
                        stats['unchanged_files'] += 1
                    else:
                        # File is new or changed
                        if not is_new_file:
                            # Move old version to history
                            old_version = registry[registry_key].get('version', 1)
                            new_version = old_version + 1

                            # Create history folder structure
                            history_subdir = history_dir / f"{dept_code}-{municipio_code}-{zona_code}-{centro_code}"
                            history_subdir.mkdir(parents=True, exist_ok=True)

                            # Move old file to history with timestamp
                            old_timestamp = registry[registry_key].get('last_updated', 'unknown')
                            history_filename = f"{mesa_numero}_v{old_version}_{old_timestamp}.pdf"
                            history_path = history_subdir / history_filename

                            if file_path.exists():
                                file_path.rename(history_path)
                                print(f"✓ (updated - v{old_version} archived)")
                                stats['updated_files'] += 1
                            else:
                                print(f"✓ (new)")
                        else:
                            new_version = 1
                            print("✓ (new)")

                        # Move temp file to final location
                        temp_path.rename(file_path)

                        # Update registry
                        registry[registry_key] = {
                            'hash': new_hash,
                            'url': pdf_url,
                            'version': new_version,
                            'last_updated': datetime.now().strftime('%Y%m%d_%H%M%S'),
                            'mesa_info': {
                                'numero': mesa_numero,
                                'departamento': dept_code,
                                'municipio': municipio_code,
                                'zona': zona_code,
                                'centro': centro_code,
                                'publicada': mesa.get('publicada'),
                                'escrutado': mesa.get('escrutado'),
                                'digitalizado': mesa.get('digitalizado')
                            }
                        }

                        stats['downloaded'] += 1
                else:
                    print("✗ (download failed)")
                    stats['failed'] += 1
                    if temp_path.exists():
                        temp_path.unlink()
            else:
                stats['skipped'] += 1

    except Exception as e:
        print(f"  Error processing {mesas_file_path}: {e}")
        stats['errors'] += 1

def parse_resume_point(resume_str):
    """
    Parse resume point string.
    Format: DEPT-MUNI-ZONA-CENTRO-MESA or DEPT-MUNI-ZONA-CENTRO or DEPT-MUNI or DEPT
    Returns tuple of (dept_code, municipio_code, zona_code, centro_code, mesa_numero)
    with None for unspecified parts
    """
    if not resume_str:
        return None

    parts = resume_str.split('-')
    result = [None, None, None, None, None]

    for i, part in enumerate(parts[:5]):
        if part:
            result[i] = part

    return tuple(result)

def should_skip_based_on_resume(dept_code, municipio_code, zona_code, centro_code, mesa_numero, resume_point):
    """
    Determine if we should skip this item based on resume point.
    Returns True if we should skip (haven't reached resume point yet).
    """
    if not resume_point:
        return False

    resume_dept, resume_muni, resume_zona, resume_centro, resume_mesa = resume_point

    # Compare department
    if resume_dept:
        if dept_code < resume_dept:
            return True
        elif dept_code > resume_dept:
            return False
        # dept_code == resume_dept, continue checking

    # Compare municipio
    if resume_muni:
        if municipio_code < resume_muni:
            return True
        elif municipio_code > resume_muni:
            return False
        # municipio_code == resume_muni, continue checking

    # Compare zona
    if resume_zona:
        if zona_code < resume_zona:
            return True
        elif zona_code > resume_zona:
            return False
        # zona_code == resume_zona, continue checking

    # Compare centro
    if resume_centro:
        if centro_code < resume_centro:
            return True
        elif centro_code > resume_centro:
            return False
        # centro_code == resume_centro, continue checking

    # Compare mesa
    if resume_mesa:
        if str(mesa_numero) < resume_mesa:
            return True
        elif str(mesa_numero) > resume_mesa:
            return False
        # mesa_numero == resume_mesa, this is the resume point, skip it (already downloaded)
        return True

    # We've reached the resume point
    return False

def scan_and_download_actas(resume_from=None):
    """
    Main function to scan all mesas.json files and download PDFs

    Args:
        resume_from: Optional string to resume from a specific point.
                    Format: DEPT-MUNI-ZONA-CENTRO-MESA
                    Example: "01-001-01-015-911" or "01-001" or "08"
    """

    # Parse resume point
    resume_point = parse_resume_point(resume_from)
    if resume_point:
        print(f"Resuming from: {resume_from}")
        print(f"Parsed as: Dept={resume_point[0]}, Muni={resume_point[1]}, "
              f"Zona={resume_point[2]}, Centro={resume_point[3]}, Mesa={resume_point[4]}")

    # Setup directories
    base_dir = Path("..")
    mesas_data_dir = base_dir / "mesas_data"
    actas_dir = base_dir / "actas"
    history_dir = base_dir / "actas_history"
    registry_path = base_dir / "actas_registry.json"

    # Create directories
    actas_dir.mkdir(exist_ok=True)
    history_dir.mkdir(exist_ok=True)

    # Load registry
    registry = load_file_registry(registry_path)

    # Statistics
    stats = {
        'total_mesas': 0,
        'downloaded': 0,
        'updated_files': 0,
        'new_files': 0,
        'unchanged_files': 0,
        'skipped': 0,
        'failed': 0,
        'errors': 0,
        'updated_urls': 0,
        'last_processed': None  # Track last processed acta for resume
    }

    print(f"Starting download at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # Load municipios data to get codes
    with open("municipios_data.json", "r", encoding="utf-8") as f:
        municipios_data = json.load(f)

    # Create lookup for municipio codes
    municipio_codes = {}
    for dept_name, dept_info in municipios_data.items():
        dept_code = dept_info["codigo"]
        if dept_code not in municipio_codes:
            municipio_codes[dept_code] = {}
        for municipio in dept_info["municipios"]:
            municipio_codes[dept_code][municipio["municipio"]] = municipio["id_municipio"]

    # Scan all department folders
    if not mesas_data_dir.exists():
        print("Error: mesas_data directory not found!")
        return

    for dept_folder in sorted(mesas_data_dir.iterdir()):
        if not dept_folder.is_dir():
            continue

        dept_name = dept_folder.name

        # Get department code
        dept_code = None
        for dept_name_lookup, dept_info in municipios_data.items():
            if dept_name_lookup == dept_name:
                dept_code = dept_info["codigo"]
                break

        if not dept_code:
            print(f"Warning: Could not find code for department {dept_name}")
            continue

        print(f"\nProcessing {dept_name} (code: {dept_code})...")

        # Iterate through municipios
        for municipio_folder in sorted(dept_folder.iterdir()):
            if not municipio_folder.is_dir():
                continue

            municipio_name = municipio_folder.name
            municipio_code = None

            # Find municipio code
            for muni_name, muni_code in municipio_codes.get(dept_code, {}).items():
                if muni_name == municipio_name:
                    municipio_code = muni_code
                    break

            if not municipio_code:
                print(f"  Warning: Could not find code for {municipio_name}")
                continue

            print(f"  {municipio_name} (code: {municipio_code})...")

            # Iterate through centros
            for centro_folder in sorted(municipio_folder.iterdir()):
                if not centro_folder.is_dir():
                    continue

                # Extract centro code from folder name (format: XXX_Name)
                folder_parts = centro_folder.name.split('_', 1)
                if len(folder_parts) < 2:
                    continue

                centro_code = folder_parts[0]

                # Determine zona code from parent structure
                # We need to check the centros_data.json to get the zona
                # For now, we'll check both possibilities (01 and 02)
                mesas_file = centro_folder / "mesas.json"

                if not mesas_file.exists():
                    continue

                # Try to determine zona code from the mesas file content
                # The id_informacion_mesa_corporacion contains the zona code
                try:
                    with open(mesas_file, 'r', encoding='utf-8') as f:
                        mesas_sample = json.load(f)

                    if mesas_sample:
                        # Parse the ID to extract zona code
                        # Format: DDDMMMZZCCCNNN where DD=dept, MMM=muni, ZZ=zona, CCC=centro, NNN=mesa
                        mesa_id = mesas_sample[0].get('id_informacion_mesa_corporacion', '')
                        if len(mesa_id) >= 8:
                            zona_code = mesa_id[5:7]
                        else:
                            zona_code = "00"

                        stats['total_mesas'] += len(mesas_sample)

                        process_mesas_file(mesas_file, dept_code, municipio_code, zona_code,
                                         centro_code, actas_dir, history_dir, registry, stats, resume_point)
                except Exception as e:
                    print(f"    Error reading {mesas_file}: {e}")
                    stats['errors'] += 1

            # Save registry periodically (after each municipio)
            save_file_registry(registry_path, registry)

    # Final save
    save_file_registry(registry_path, registry)

    # Print summary
    print("\n" + "="*60)
    print("Download Summary:")
    print(f"  Total mesas found: {stats['total_mesas']}")
    print(f"  Files downloaded: {stats['downloaded']}")
    print(f"  New files: {stats['new_files']}")
    print(f"  Updated files: {stats['updated_files']}")
    print(f"  Unchanged files: {stats['unchanged_files']}")
    print(f"  Skipped (already current): {stats['skipped']}")
    print(f"  Failed downloads: {stats['failed']}")
    print(f"  Errors: {stats['errors']}")

    if stats['last_processed']:
        print(f"\nLast processed acta: {stats['last_processed']}")
        print(f"  To resume from this point, use: --resume {stats['last_processed']}")

    print(f"\nRegistry saved to: {registry_path}")
    print(f"PDFs saved to: {actas_dir}")
    print(f"History saved to: {history_dir}")
    print(f"\nCompleted at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Download election actas PDFs with version control',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Resume Examples:
  Resume from a specific mesa:
    python3 download_actas.py --resume 01-001-01-015-911

  Resume from a specific centro (all mesas in that centro onwards):
    python3 download_actas.py --resume 01-001-01-015

  Resume from a specific municipio:
    python3 download_actas.py --resume 01-001

  Resume from a specific department:
    python3 download_actas.py --resume 08

Format: DEPT-MUNI-ZONA-CENTRO-MESA (any part can be omitted from the right)
        """
    )

    parser.add_argument(
        '--resume',
        type=str,
        help='Resume from a specific point (Format: DEPT-MUNI-ZONA-CENTRO-MESA or partial)',
        metavar='RESUME_POINT'
    )

    args = parser.parse_args()

    scan_and_download_actas(resume_from=args.resume)
