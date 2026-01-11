import os
from urllib import request
import geopandas as gpd
from sentinelhub import (
    SHConfig, BBox, CRS, SentinelHubRequest,
    DataCollection, MimeType
)


# ------------------------------------------------------------
# AUTH CONFIG
# ------------------------------------------------------------

def get_sentinel_config():
    config = SHConfig()
    config.sh_client_id = os.getenv("SH_CLIENT_ID")
    config.sh_client_secret = os.getenv("SH_CLIENT_SECRET")

    if not config.sh_client_id or not config.sh_client_secret:
        raise RuntimeError(
            "Sentinel Hub credentials not found. "
            "Set SH_CLIENT_ID and SH_CLIENT_SECRET."
        )

    return config


# ------------------------------------------------------------
# AOI HELPERS
# ------------------------------------------------------------

def get_aoi_bbox_wgs84(aoi_path):
    gdf = gpd.read_file(aoi_path).to_crs(4326)
    minx, miny, maxx, maxy = gdf.total_bounds
    return minx, miny, maxx, maxy


# ------------------------------------------------------------
# SENTINEL DOWNLOAD
# ------------------------------------------------------------

def download_sentinel_rgb(
    aoi_path,
    out_dir,
    time_range=("2020-06-01", "2025-12-30"),
    max_cloud=1,
    size=(1024, 1024)
):
    minx, miny, maxx, maxy = get_aoi_bbox_wgs84(aoi_path)
    bbox = BBox((minx, miny, maxx, maxy), crs=CRS.WGS84)

    config = get_sentinel_config()

    evalscript = """
    //VERSION=3
    function setup() {
        return {
            input: ["B04", "B03", "B02"],
            output: { bands: 3 }
        };
    }

    function evaluatePixel(sample) {
        return [sample.B04, sample.B03, sample.B02];
    }
    """

    request = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A,
                time_interval=time_range,
                maxcc=max_cloud / 100
            )
        ],
        responses=[
            SentinelHubRequest.output_response("default", MimeType.TIFF)
        ],
        bbox=bbox,
        size=size,
        config=config,
        data_folder=str(out_dir) 
    )

    request.save_data()
    print(f"[✓] Sentinel-2 RGB downloaded → {out_dir}")

    
    
