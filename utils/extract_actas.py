#!/usr/bin/env python3
import os
import json
import re
from pathlib import Path
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import concurrent.futures
from tqdm import tqdm

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using OCR"""
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)

        if not images:
            return None

        # Perform OCR on the first page
        text = pytesseract.image_to_string(images[0], lang='spa')
        return text
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
        return None

def parse_acta_text(text, filename):
    """Parse the extracted text to structure data"""
    if not text:
        return None

    data = {
        "filename": filename,
        "jrv_number": None,
        "location": {
            "department": None,
            "municipality": None,
            "sector": None,
            "voting_center": None
        },
        "balance": {
            "ballots_received": None,
            "ballots_unused": None,
            "ballots_used": None,
            "total_voters": None
        },
        "results": {
            "parties": {},
            "blank_votes": None,
            "null_votes": None,
            "total": None
        },
        "officials": []
    }

    # Extract JRV number
    jrv_match = re.search(r'JRV\s*N[°º]?\s*(\d+)', text, re.IGNORECASE)
    if jrv_match:
        data["jrv_number"] = jrv_match.group(1)

    # Extract location info
    dept_match = re.search(r'DEPARTAMENTO[:\s]*([A-ZÁÉÍÓÚÑa-záéíóúñ\s]+)', text, re.IGNORECASE)
    if dept_match:
        data["location"]["department"] = dept_match.group(1).strip()

    muni_match = re.search(r'MUNICIPIO[:\s]*([A-ZÁÉÍÓÚÑa-záéíóúñ\s]+)', text, re.IGNORECASE)
    if muni_match:
        data["location"]["municipality"] = muni_match.group(1).strip()

    sector_match = re.search(r'SECTOR\s+ELECTORAL[:\s]*([^\n]+)', text, re.IGNORECASE)
    if sector_match:
        data["location"]["sector"] = sector_match.group(1).strip()

    center_match = re.search(r'CENTRO\s+DE\s+VOTACI[OÓ]N[:\s]*([^\n]+)', text, re.IGNORECASE)
    if center_match:
        data["location"]["voting_center"] = center_match.group(1).strip()

    # Extract numbers from balance section
    # Look for pattern with three digits
    numbers = re.findall(r'\b(\d{1,3})\b', text)

    # Try to extract party votes - look for party names and associated numbers
    parties_data = {}

    # Common party abbreviations
    party_patterns = {
        "DC": r'DC.*?(\d+)',
        "LIBRE": r'[Ll]ibre.*?(\d+)',
        "PARTIDO_INNOVACION": r'INNOVACI[OÓ]N.*?(\d+)',
        "PARTIDO_LIBERAL": r'LIBERAL.*?(\d+)',
        "PARTIDO_NACIONAL": r'NACIONAL.*?(\d+)'
    }

    for party, pattern in party_patterns.items():
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            parties_data[party] = match.group(1)

    data["results"]["parties"] = parties_data

    # Look for blank and null votes
    blank_match = re.search(r'BLANCO.*?(\d+)', text, re.IGNORECASE)
    if blank_match:
        data["results"]["blank_votes"] = blank_match.group(1)

    null_match = re.search(r'NULOS?.*?(\d+)', text, re.IGNORECASE)
    if null_match:
        data["results"]["null_votes"] = null_match.group(1)

    # Look for total
    total_match = re.search(r'TOTAL.*?(\d+)', text, re.IGNORECASE)
    if total_match:
        data["results"]["total"] = total_match.group(1)

    # Store raw text for reference
    data["raw_text"] = text

    return data

def process_single_pdf(pdf_path, output_dir):
    """Process a single PDF file"""
    filename = os.path.basename(pdf_path)
    json_filename = filename.replace('.pdf', '.json')
    json_path = os.path.join(output_dir, json_filename)

    # Skip if already processed
    if os.path.exists(json_path):
        return f"Skipped (already exists): {filename}"

    # Extract text
    text = extract_text_from_pdf(pdf_path)

    if text is None:
        return f"Failed: {filename}"

    # Parse data
    data = parse_acta_text(text, filename)

    # Save to JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return f"Processed: {filename}"

def main():
    # Directories
    actas_dir = "../actas"
    output_dir = "actas_json"

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Get all PDF files
    pdf_files = sorted([
        os.path.join(actas_dir, f)
        for f in os.listdir(actas_dir)
        if f.endswith('.pdf')
    ])

    print(f"Found {len(pdf_files)} PDF files to process")
    print("Starting extraction...")

    # Process PDFs in parallel
    max_workers = 4  # Adjust based on your CPU

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Create a list of futures
        futures = [
            executor.submit(process_single_pdf, pdf_path, output_dir)
            for pdf_path in pdf_files
        ]

        # Process results with progress bar
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(pdf_files)):
            try:
                result = future.result()
                # You can log the result if needed
            except Exception as e:
                print(f"Error: {str(e)}")

    print(f"\nExtraction complete! JSON files saved to {output_dir}/")

if __name__ == "__main__":
    main()
