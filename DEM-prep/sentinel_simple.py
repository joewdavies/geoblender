#!/usr/bin/env python3
"""
sentinel_simple.py

Minimal, robust Sentinel-2 RGB downloader using the
Copernicus Data Space Ecosystem (CDSE) Process API.

- Uses OAuth2 client_credentials
- No sentinelhub-py
- Reads AOI from GeoPackage
- Outputs a GeoTIFF
"""

import os
import json
from pathlib import Path

import geopandas as gpd
import requests


# ============================================================
# CONSTANTS
# ============================================================

TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/"
    "auth/realms/CDSE/protocol/openid-connect/token"
)

PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"


# ============================================================
# AUTH
# ============================================================

def get_access_token() -> str:
    """Fetch OAuth access token using client credentials."""
    client_id = os.getenv("SH_CLIENT_ID")
    client_secret = os.getenv("SH_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError(
            "Missing Sentinel credentials. "
            "Set SH_CLIENT_ID and SH_CLIENT_SECRET."
        )

    r = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )

    r.raise_for_status()
    return r.json()["access_token"]


# ============================================================
# AOI
# ============================================================

def get_aoi_bbox_wgs84(aoi_gpkg: str, layer: str = "aoi"):
    """Read AOI and return bbox in EPSG:4326."""
    gdf = gpd.read_file(aoi_gpkg, layer=layer).to_crs(4326)
    return gdf.total_bounds  # minx, miny, maxx, maxy


# ============================================================
# SENTINEL DOWNLOAD
# ============================================================

def download_sentinel_rgb(
    aoi_gpkg: str,
    out_tif: str,
    layer: str = "aoi",
    time_range=("2024-06-01", "2024-08-01"),
    max_cloud: int = 20,
    width: int = 1024,
    height: int = 1024,
):
    """
    Download Sentinel-2 RGB image for AOI.

    Parameters
    ----------
    aoi_gpkg : str
        Path to AOI GeoPackage
    out_tif : str
        Output GeoTIFF path
    layer : str
        AOI layer name inside gpkg
    time_range : tuple
        (start_date, end_date) YYYY-MM-DD
    max_cloud : int
        Max cloud cover percentage
    width, height : int
        Output image size in pixels
    """

    token = get_access_token()
    minx, miny, maxx, maxy = get_aoi_bbox_wgs84(aoi_gpkg, layer)

    payload = {
        "input": {
            "bounds": {
                "bbox": [minx, miny, maxx, maxy],
                "properties": {
                    "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                },
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": f"{time_range[0]}T00:00:00Z",
                            "to": f"{time_range[1]}T23:59:59Z",
                        },
                        "maxCloudCoverage": max_cloud,
                    },
                }
            ],
        },
        "output": {
            "width": width,
            "height": height,
            "responses": [
                {
                    "identifier": "default",
                    "format": {"type": "image/tiff"},
                }
            ],
        },
        "evalscript": """
//VERSION=3
function setup() {
  return {
    input: ["B04", "B03", "B02"],
    output: { bands: 3 }
  };
}

function evaluatePixel(s) {
  return [s.B04, s.B03, s.B02];
}
""",
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    r = requests.post(
        PROCESS_URL,
        headers=headers,
        json=payload,
        stream=True,
        timeout=180,
    )

    r.raise_for_status()

    out_tif = Path(out_tif)
    out_tif.parent.mkdir(parents=True, exist_ok=True)

    with open(out_tif, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"[✓] Sentinel-2 RGB written → {out_tif}")
