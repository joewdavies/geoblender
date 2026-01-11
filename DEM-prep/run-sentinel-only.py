from sentinel import download_sentinel_rgb

download_sentinel_rgb(
    aoi_gpkg="./input/aoi/aoi.gpkg",
    out_tif="./output/sentinel/sentinel_rgb.tif",
    max_cloud=5,
    time_range=("2023-07-01", "2023-09-15"),
    width=2500,
    height=1582,
)

# 4866px x 3080px