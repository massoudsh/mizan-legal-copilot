"""Sync approved JSON regulation feeds; run from a trusted scheduler."""

import os
from urllib.parse import urlparse

import requests

from app import storage
from app.schemas import RegulationInput


def sync_sources() -> int:
    allowed_hosts = {host.strip().lower() for host in os.getenv("MIZAN_REGULATORY_SOURCE_HOSTS", "").split(",") if host.strip()}
    synced = 0
    for source in storage.list_regulatory_sources():
        host = urlparse(str(source.feed_url)).hostname or ""
        if host.lower() not in allowed_hosts:
            continue
        response = requests.get(str(source.feed_url), timeout=15)
        response.raise_for_status()
        for item in response.json():
            regulation, changed = storage.create_regulation(RegulationInput(**item, source_name=source.name))
            if changed:
                storage.create_alert_for_all("نسخهٔ جدید مقرره", f"{regulation.title} با نسخهٔ {regulation.source_version} ثبت شد.")
            synced += 1
        storage.mark_source_checked(source.id)
    return synced


if __name__ == "__main__":
    print(sync_sources())
