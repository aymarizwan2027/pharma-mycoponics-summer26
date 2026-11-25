#!/usr/bin/env python3
"""Sync new EpiCollect chamber photos to Roboflow without duplicating legacy images.

Study dates come only from dates.csv -> 1_Date. created_at/uploaded_at are never
used to date observations. Run --mode baseline before the first upload run.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATES_CSV = ROOT / "data/epicollect/dates.csv"
TUBES_CSV = ROOT / "data/epicollect/tube_observations.csv"
MANIFEST = ROOT / "data/roboflow/manifest.csv"
DATE_MIN = date(2026, 6, 12)
DATE_MAX = date(2026, 8, 10)
MEDIA_RE = re.compile(r"https?://five\.epicollect\.net/api/media/[^\s\"'<>]+", re.I)
PHOTO_FIELD_RE = re.compile(r"^\d+_(?:Photo_of_exudate_.*|\d+)$", re.I)
FIELDS = [
    "image_key", "study_date", "culture", "parent_uuid", "ec5_branch_uuid",
    "photo_index", "photo_column", "media_filename", "roboflow_name",
    "roboflow_image_id", "annotation_status", "sync_status", "roboflow_project_url",
]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(f"Required synced export is missing: {path.relative_to(ROOT)}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader.fieldnames), list(reader)


def parse_study_date(raw: str) -> date | None:
    value = (raw or "").strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def media_filename(url: str) -> str:
    query = parse_qs(urlparse(url).query)
    return (query.get("name") or [Path(urlparse(url).path).name])[0]


def current_photos() -> list[dict[str, str]]:
    _, date_rows = read_csv(DATES_CSV)
    tube_headers, tube_rows = read_csv(TUBES_CSV)
    date_by_parent: dict[str, date] = {}
    for row in date_rows:
        parent = (row.get("ec5_uuid") or "").strip()
        study_date = parse_study_date(row.get("1_Date", ""))
        if parent and study_date:
            date_by_parent[parent] = study_date

    photo_columns = [name for name in tube_headers if PHOTO_FIELD_RE.match(name or "")]
    if not photo_columns:
        raise ValueError("No photo slots found in tube_observations.csv")

    photos: list[dict[str, str]] = []
    missing_date = 0
    outside_window = 0
    for row in tube_rows:
        parent = (row.get("ec5_branch_owner_uuid") or "").strip()
        event_uuid = (row.get("ec5_branch_uuid") or "").strip()
        study_date = date_by_parent.get(parent)
        if not study_date:
            missing_date += 1
            continue
        if not DATE_MIN <= study_date <= DATE_MAX:
            outside_window += 1
            continue
        culture = (row.get("title") or row.get("9_Which_chamber") or "").strip()
        if not event_uuid:
            continue

        for photo_index, column in enumerate(photo_columns, start=1):
            cell = row.get(column) or ""
            for url_number, url in enumerate(MEDIA_RE.findall(cell), start=1):
                filename = media_filename(url)
                image_key = f"{event_uuid}|{column}|{filename}"
                index_suffix = f"{photo_index:02d}" + (f"_{url_number}" if url_number > 1 else "")
                extension = Path(filename).suffix.lower() or ".jpg"
                roboflow_name = f"{event_uuid}_{index_suffix}{extension}"
                photos.append({
                    "image_key": image_key,
                    "study_date": study_date.isoformat(),
                    "culture": culture,
                    "parent_uuid": parent,
                    "ec5_branch_uuid": event_uuid,
                    "photo_index": index_suffix,
                    "photo_column": column,
                    "media_filename": filename,
                    "roboflow_name": roboflow_name,
                    "roboflow_image_id": "",
                    "annotation_status": "baseline_unmatched",
                    "sync_status": "baseline",
                    "roboflow_project_url": project_url(),
                    "source_url": url,
                })
    print(f"Study-date filter: {DATE_MIN.isoformat()} through {DATE_MAX.isoformat()} inclusive")
    print(f"Photos in range: {len(photos)}; rows without a usable 1_Date: {missing_date}; outside range: {outside_window}")
    return photos


def project_url() -> str:
    workspace = os.getenv("ROBOFLOW_WORKSPACE", "ayma-rizwan-s-workspace")
    project = os.getenv("ROBOFLOW_PROJECT", "fungal-culture-morphology-2")
    return f"https://app.roboflow.com/{workspace}/{project}"


def read_manifest() -> dict[str, dict[str, str]]:
    if not MANIFEST.exists():
        return {}
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return {row["image_key"]: {key: row.get(key, "") or "" for key in FIELDS}
                for row in reader if row.get("image_key")}


def write_manifest(rows: dict[str, dict[str, str]]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows.values(), key=lambda row: (row.get("study_date", ""), row.get("culture", ""), row.get("ec5_branch_uuid", ""), row.get("photo_index", "")))
    with MANIFEST.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(ordered)
    print(f"Saved {len(ordered)} image rows to {MANIFEST.relative_to(ROOT)}")


def roboflow_context():
    api_key = os.getenv("ROBOFLOW_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Set the ROBOFLOW_API_KEY GitHub Actions secret before reconcile/upload mode.")
    try:
        from roboflow import Roboflow
    except ImportError as exc:
        raise RuntimeError("Install the Roboflow Python SDK with: pip install roboflow") from exc
    workspace = os.getenv("ROBOFLOW_WORKSPACE", "ayma-rizwan-s-workspace")
    project_name = os.getenv("ROBOFLOW_PROJECT", "fungal-culture-morphology-2")
    rf = Roboflow(api_key=api_key)
    return rf.workspace(workspace).project(project_name)


def metadata_for(image: dict) -> dict:
    metadata = image.get("user_metadata") or image.get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    return metadata if isinstance(metadata, dict) else {}


def annotation_state(image: dict) -> str:
    labels = image.get("labels") or []
    annotations = image.get("annotations")
    return "annotated" if labels or annotations else "uploaded_unannotated"


def roboflow_images(project) -> tuple[dict[str, dict], dict[str, dict]]:
    by_name: dict[str, dict] = {}
    by_key: dict[str, dict] = {}
    for page in project.search_all(limit=100, fields=["id", "name", "labels", "annotations", "tags", "user_metadata"]):
        for image in page:
            name = str(image.get("name") or "").lower()
            if name:
                by_name[name] = image
            metadata = metadata_for(image)
            child = str(metadata.get("ec5_branch_uuid") or metadata.get("epicollect_uuid") or metadata.get("ec5_uuid") or "")
            media = str(metadata.get("media_filename") or "")
            if child and media:
                by_key[f"{child}|{media}"] = image
    return by_name, by_key


def matching_image(photo: dict, by_name: dict[str, dict], by_key: dict[str, dict]) -> dict | None:
    exact = by_name.get(photo["roboflow_name"].lower())
    if exact:
        return exact
    metadata_match = by_key.get(f"{photo['ec5_branch_uuid']}|{photo['media_filename']}")
    if metadata_match:
        return metadata_match
    # Legacy image names may already contain the Epicollect child UUID.
    for name, image in by_name.items():
        if photo["ec5_branch_uuid"].lower() in name and photo["media_filename"].lower() in name:
            return image
    return None


def attach_roboflow_state(row: dict[str, str], image: dict) -> None:
    row["roboflow_image_id"] = str(image.get("id") or "")
    row["annotation_status"] = annotation_state(image)
    row["sync_status"] = "matched_existing"


def download_to(path: Path, url: str) -> None:
    request = Request(url, headers={"User-Agent": "mycoponics-epicollect-roboflow-sync/1.0"})
    with urlopen(request, timeout=60) as response:
        path.write_bytes(response.read())


def upload_one(project, photo: dict) -> dict:
    metadata = {
        "ec5_branch_uuid": photo["ec5_branch_uuid"],
        "ec5_uuid": photo["parent_uuid"],
        "media_filename": photo["media_filename"],
        "photo_column": photo["photo_column"],
        "photo_index": photo["photo_index"],
        "culture": photo["culture"],
        "study_date": photo["study_date"],
    }
    with tempfile.TemporaryDirectory(prefix="mycoponics-photo-") as temp_dir:
        local_path = Path(temp_dir) / photo["roboflow_name"]
        download_to(local_path, photo["source_url"])
        uploaded, _upload_time, _retries = project.upload_image(
            image_path=str(local_path),
            split="train",
            tag_names=[photo["culture"]] if photo["culture"] else [],
            metadata=metadata,
        )
    result = dict(photo)
    result["roboflow_image_id"] = str(uploaded.get("id") or "")
    result["annotation_status"] = "uploaded_unannotated"
    result["sync_status"] = "uploaded"
    return result


def run(mode: str) -> int:
    if mode == "baseline":
        existing = read_manifest()
        photos = current_photos()
        added = 0
        for photo in photos:
            if photo["image_key"] not in existing:
                existing[photo["image_key"]] = {key: photo.get(key, "") for key in FIELDS}
                added += 1
        write_manifest(existing)
        print(f"Baseline complete. Added {added} photo references without uploading any image.")
        print("Next: run reconcile to match existing Roboflow images, then enable upload mode for future photos.")
        return 0

    project = roboflow_context()
    by_name, by_key = roboflow_images(project)
    manifest = read_manifest()
    photos = current_photos()

    if mode == "reconcile":
        matched = 0
        for photo in photos:
            row = manifest.get(photo["image_key"])
            if not row:
                row = {key: photo.get(key, "") for key in FIELDS}
                manifest[photo["image_key"]] = row
            image = matching_image(photo, by_name, by_key)
            if image:
                attach_roboflow_state(row, image)
                matched += 1
            elif not row.get("roboflow_image_id"):
                row["annotation_status"] = "unmatched_legacy"
                row["sync_status"] = "baseline_unmatched"
        write_manifest(manifest)
        print(f"Reconciliation complete: matched {matched} of {len(photos)} in-window photos to Roboflow.")
        return 0

    if not MANIFEST.exists():
        raise RuntimeError("No manifest exists. Run the baseline workflow first; this prevents a first-run bulk upload.")
    uploaded_count = 0
    matched_count = 0
    for photo in photos:
        row = manifest.get(photo["image_key"])
        if row:
            image = matching_image(photo, by_name, by_key) if not row.get("roboflow_image_id") else None
            if image:
                attach_roboflow_state(row, image)
                matched_count += 1
            continue
        image = matching_image(photo, by_name, by_key)
        if image:
            row = {key: photo.get(key, "") for key in FIELDS}
            attach_roboflow_state(row, image)
            manifest[photo["image_key"]] = row
            matched_count += 1
            continue
        row = upload_one(project, photo)
        manifest[photo["image_key"]] = {key: row.get(key, "") for key in FIELDS}
        by_name[row["roboflow_name"].lower()] = {"id": row["roboflow_image_id"], "name": row["roboflow_name"], "labels": []}
        uploaded_count += 1
        print(f"Uploaded {row['culture']} {row['study_date']} {row['roboflow_name']}")

    for row in manifest.values():
        if row.get("roboflow_image_id"):
            image = by_name.get(row.get("roboflow_name", "").lower())
            if image:
                row["annotation_status"] = annotation_state(image)
    write_manifest(manifest)
    print(f"Upload sync complete: {uploaded_count} uploaded; {matched_count} existing Roboflow images matched.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["baseline", "reconcile", "sync"], required=True)
    args = parser.parse_args()
    try:
        raise SystemExit(run(args.mode))
    except Exception as error:
        print(f"Roboflow sync failed: {error}", file=sys.stderr)
        raise SystemExit(1)
