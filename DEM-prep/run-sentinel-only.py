from sentinel_simple import download_sentinel_rgb

download_sentinel_rgb(
    aoi_gpkg="./input/aoi/aoi.gpkg",
    out_tif="./output/sentinel/sentinel_rgb.tif",
    width=1024,
    height=1024,
)