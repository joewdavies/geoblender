#!/usr/bin/env python3
from sentinel import download_sentinel_rgb, fit_to_sentinel_limit

"""
DEM-prep.py
Full DEM preparation pipeline for GeoBlender

I downloaded my tiles from https://ec.europa.eu/eurostat/web/gisco/geodata/digital-elevation-model/copernicus#Elevation

Steps:
1. Extract zipped DEM tiles
2. Merge DEM tiles
3. Clip merged DEM by AOI (GeoPackage)
4. Export rendered DEM (QGIS-equivalent)
5. Create AOI alpha mask PNG
"""

# ============================================================
# USER CONFIGURATION SETTINGS
# ============================================================

COUNTRY_CODE  = "KR"  # ISO 3166-1 alpha-2 country code
DESIRED_EPSG = 5179   # output DEM projection (EPSG code)

COUNTRIES_GPKG = "./input/CNTR_RG_01M_2024_4326.gpkg"
AOI_OUTPUT = "./input/aoi/aoi.gpkg"


# INPUTS
TILES_DIR = "./input/tiles"                 # Folder with DEM ZIP tiles
EXTRACTED_TILES_DIR = "./input/tiles_tmp"   # Temp extraction folder
AOI_LAYER = "aoi"                        # Layer name inside gpkg

# OUTPUTS
OUTPUT_DIR = "./output"
MERGED_DEM_NAME = "dem_merged.tif"
CLIPPED_DEM_NAME = "dem_clipped.tif"
RENDERED_DEM_NAME = "dem_rendered.tif"

# MASK SETTINGS
AOI_MASK_NAME = "aoi_mask.png"                  # Output AOI mask PNG

# Water mask (Natural Earth)
WATER_LAKES_ZIP = "./input/water/ne_10m_lakes.zip"
WATER_LAKES_SHP = "ne_10m_lakes.shp"

WATER_RIVERS_ZIP = "./input/water/ne_10m_rivers_lake_centerlines.zip"
WATER_RIVERS_SHP = "ne_10m_rivers_lake_centerlines.shp"

WATER_EXTRACT_DIR = "./input/water/tmp"
WATER_MASK_NAME = "water_mask.png"

#SENTINEL SETTINGS
SENTINEL_RGB = "./output/sentinel/sentinel_rgb.tif"
SENTINEL_MAX_CLOUD = 5  # Max cloud cover percentage for Sentinel image
SENTINEL_TIME_RANGE = ("2023-07-01", "2023-09-15") # Time range for Sentinel image

# OUTPUT SETTINGS
PERCENTILE_CLIP = (0.1, 99.9)  # A percentile stretch is a way of converting raw DEM values (meters) into a 0–255 grayscale image by ignoring extreme values at the low and high ends.


# ============================================================


import sys
import zipfile
import numpy as np
import rasterio
import geopandas as gpd
import pandas as pd
import shutil

from pathlib import Path
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio.features import rasterize
from rasterio.warp import calculate_default_transform, reproject, Resampling

def create_aoi_from_country(
    countries_gpkg: Path,
    country_code: str,
    out_gpkg: Path
):
    gdf = gpd.read_file(countries_gpkg)

    if "CNTR_ID" not in gdf.columns:
        raise RuntimeError("CNTR_ID field not found in countries dataset")

    match = gdf[gdf["CNTR_ID"] == country_code]

    if match.empty:
        raise RuntimeError(f"Country code '{country_code}' not found")

    out_gpkg.parent.mkdir(parents=True, exist_ok=True)
    match.to_file(out_gpkg, driver="GPKG")

    print(f"[✓] AOI created for country '{country_code}' → {out_gpkg.name}")
    return out_gpkg

# ------------------------------------------------------------
# ZIP EXTRACTION
# ------------------------------------------------------------

def extract_dem_zips(tiles_dir: Path, extract_dir: Path) -> list[Path]:
    # Clear extract_dir on each run
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    zip_files = list(tiles_dir.glob("*.zip"))
    if not zip_files:
        sys.exit(f"[✗] No DEM ZIP files found in {tiles_dir}")

    for zip_path in zip_files:
        print(f"Extracting {zip_path.name}...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)

    tifs = list(extract_dir.rglob("*.tif")) + list(extract_dir.rglob("*.tiff"))
    if not tifs:
        sys.exit("[✗] No DEM .tif found after extraction")

    print(f"[✓] Extracted {len(tifs)} DEM tiles")
    return tifs


# ------------------------------------------------------------
# DEM MERGE
# ------------------------------------------------------------

def merge_dem_tiles(tile_paths: list[Path], out_tif: Path) -> Path:
    srcs = [rasterio.open(t) for t in tile_paths]

    mosaic, transform = merge(srcs)

    profile = srcs[0].profile.copy()
    profile.update(
        height=mosaic.shape[1],
        width=mosaic.shape[2],
        transform=transform
    )

    with rasterio.open(out_tif, "w", **profile) as dst:
        dst.write(mosaic)

    for src in srcs:
        src.close()

    print(f"[✓] Merged DEM → {out_tif.name}")
    return out_tif


# ------------------------------------------------------------
# DEM REPROJECTION
# ------------------------------------------------------------

def reproject_dem(
    dem_tif: Path,
    out_tif: Path,
    dst_epsg: int
) -> Path:
    dst_crs = f"EPSG:{dst_epsg}"
    print(f"Reprojecting DEM to EPSG:{dst_epsg}...")

    with rasterio.open(dem_tif) as src:
        transform, width, height = calculate_default_transform(
            src.crs,
            dst_crs,
            src.width,
            src.height,
            *src.bounds
        )

        profile = src.profile.copy()
        profile.update(
            crs=dst_crs,
            transform=transform,
            width=width,
            height=height
        )

        with rasterio.open(out_tif, "w", **profile) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.bilinear
                )

    print(f"[✓] Reprojected DEM → EPSG:{dst_epsg}")
    return out_tif


# ------------------------------------------------------------
# DEM CLIP BY AOI
# ------------------------------------------------------------

def clip_dem_by_aoi(dem_tif: Path, aoi_path: Path, aoi_layer, out_tif: Path) -> Path:
    if aoi_layer:
        gdf = gpd.read_file(aoi_path, layer=aoi_layer)
    else:
        gdf = gpd.read_file(aoi_path)

    with rasterio.open(dem_tif) as src:
        gdf = gdf.to_crs(src.crs)
        geoms = [geom for geom in gdf.geometry]

        clipped, transform = mask(
            src,
            geoms,
            crop=True,
            nodata=src.nodata
        )

        profile = src.profile.copy()
        profile.update(
            height=clipped.shape[1],
            width=clipped.shape[2],
            transform=transform
        )

    with rasterio.open(out_tif, "w", **profile) as dst:
        dst.write(clipped)

    print(f"[✓] Clipped DEM → {out_tif.name}")
    return out_tif


# ------------------------------------------------------------
# RENDERED DEM EXPORT (QGIS EQUIVALENT)
# ------------------------------------------------------------

def export_rendered_dem(dem_tif: Path, out_png: Path, percentile_clip):
    with rasterio.open(dem_tif) as src:
        dem = src.read(1).astype("float32")
        profile = src.profile.copy()
        nodata = src.nodata

    if nodata is not None:
        dem = np.where(dem == nodata, np.nan, dem)

    vmin, vmax = np.nanpercentile(dem, percentile_clip)

    dem_norm = np.clip((dem - vmin) / (vmax - vmin), 0, 1)
    dem_8bit = (dem_norm * 255).astype(np.uint8)

    profile.update(
        driver="PNG",
        dtype="uint8",
        count=1,
        nodata=0
    )

    with rasterio.open(out_png, "w", **profile) as dst:
        dst.write(dem_8bit, 1)

    print(f"[✓] Rendered DEM → {out_png.name}")
    print(f"    stretch: {vmin:.2f} → {vmax:.2f}")

def export_rendered_dem_uint16(
    dem_tif: Path,
    out_tif: Path,
    percentile_clip=None
):
    """
    Export DEM as 16-bit unsigned integer (0–65535),
    rescaled from existing elevation values.
    """

    with rasterio.open(dem_tif) as src:
        dem = src.read(1).astype("float32")
        profile = src.profile.copy()
        nodata = src.nodata

    # Mask NoData
    if nodata is not None:
        dem = np.where(dem == nodata, np.nan, dem)

    # Optional percentile clip (usually OFF for displacement)
    if percentile_clip:
        vmin, vmax = np.nanpercentile(dem, percentile_clip)
    else:
        vmin = np.nanmin(dem)
        vmax = np.nanmax(dem)

    if vmin == vmax:
        raise RuntimeError("DEM has zero elevation range")

    # Rescale to 0–65535
    dem_norm = (dem - vmin) / (vmax - vmin)
    dem_uint16 = np.clip(dem_norm * 65535, 0, 65535).astype(np.uint16)

    profile.update(
        driver="GTiff",
        dtype="uint16",
        count=1,
        nodata=0
    )

    with rasterio.open(out_tif, "w", **profile) as dst:
        dst.write(dem_uint16, 1)

    print(f"[✓] 16-bit DEM written → {out_tif.name}")
    print(f"    value range: {vmin:.2f} → {vmax:.2f}")
    
# ------------------------------------------------------------
# CREATE MASK (ALPHA PNG)
# ------------------------------------------------------------

def create_vector_mask(
    dem_tif: Path,
    vector_path: Path,
    out_png: Path,
    burn_value: int = 255
):
    gdf = gpd.read_file(vector_path, layer=AOI_LAYER)

    with rasterio.open(dem_tif) as src:
        gdf = gdf.to_crs(src.crs)
        transform = src.transform
        shape = (src.height, src.width)
        profile = src.profile.copy()

    mask_arr = rasterize(
        [(geom, burn_value) for geom in gdf.geometry],
        out_shape=shape,
        transform=transform,
        fill=0,
        dtype="uint8"
    )

    rgba = np.zeros((4, shape[0], shape[1]), dtype=np.uint8)
    rgba[3] = mask_arr  # alpha channel

    profile.update(
        driver="PNG",
        dtype="uint8",
        count=4
    )

    with rasterio.open(out_png, "w", **profile) as dst:
        dst.write(rgba)

    print(f"[✓] Mask written → {out_png.name}")
    
def extract_vector_zip(zip_path: Path, extract_dir: Path, shp_name: str) -> Path:
    extract_dir.mkdir(parents=True, exist_ok=True)

    print(f"Extracting {zip_path.name}...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)

    shp = extract_dir / shp_name
    if not shp.exists():
        sys.exit(f"[✗] Shapefile not found: {shp}")

    return shp

def create_merged_water_mask(
    dem_tif: Path,
    vector_paths: list[Path],
    out_png: Path
):
    print(f"Creating merged water mask...")
    gdfs = [gpd.read_file(p) for p in vector_paths]

    with rasterio.open(dem_tif) as src:
        gdfs = [gdf.to_crs(src.crs) for gdf in gdfs]
        transform = src.transform
        shape = (src.height, src.width)
        profile = src.profile.copy()

    # Merge lakes + rivers
    merged = gpd.GeoDataFrame(
        pd.concat(gdfs, ignore_index=True),
        crs=gdfs[0].crs
    )

    mask_arr = rasterize(
        [(geom, 255) for geom in merged.geometry],
        out_shape=shape,
        transform=transform,
        fill=0,
        dtype="uint8"
    )

    rgba = np.zeros((4, shape[0], shape[1]), dtype=np.uint8)
    rgba[3] = mask_arr

    profile.update(
        driver="PNG",
        dtype="uint8",
        count=4
    )

    with rasterio.open(out_png, "w", **profile) as dst:
        dst.write(rgba)

    print(f"[✓] Water mask (lakes + rivers) → {out_png.name}")
    
def print_blender_dims(rendered_png: Path):
    with rasterio.open(rendered_png) as src:
        width = src.width
        height = src.height

    print("\n--- Blender setup info ---")
    print(f"Rendered DEM dimensions: {width} x {height}")
    print("Plane scale suggestion:")
    print(f"  X: {width / 1000:.3f}")
    print(f"  Y: {height / 1000:.3f}")
    print("--------------------------\n")

def resample_raster_to_dem(
    src_tif: Path,
    dem_tif: Path,
    out_tif: Path
):
    with rasterio.open(dem_tif) as dem:
        dst_crs = dem.crs
        dst_transform = dem.transform
        dst_width = dem.width
        dst_height = dem.height
        dst_profile = dem.profile.copy()

    with rasterio.open(src_tif) as src:
        dst_profile.update(
            dtype=src.dtypes[0],
            count=src.count
        )

        data = np.zeros(
            (src.count, dst_height, dst_width),
            dtype=src.dtypes[0]
        )

        for i in range(src.count):
            reproject(
                source=rasterio.band(src, i + 1),
                destination=data[i],
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst_transform,
                dst_crs=dst_crs,
                resampling=Resampling.bilinear
            )

    with rasterio.open(out_tif, "w", **dst_profile) as dst:
        dst.write(data)

    print(f"[✓] Sentinel resampled to DEM grid → {out_tif.name}")
    

def get_raster_size(raster_path: Path) -> tuple[int, int]:
    with rasterio.open(raster_path) as src:
        return src.width, src.height
    
# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():
    tiles_dir = Path(TILES_DIR)
    extract_dir = Path(EXTRACTED_TILES_DIR)
    output_dir = Path(OUTPUT_DIR)

    output_dir.mkdir(parents=True, exist_ok=True)
    
    aoi_path = create_aoi_from_country(
    Path(COUNTRIES_GPKG),
    COUNTRY_CODE,
    Path(AOI_OUTPUT)
)

    merged_dem = output_dir / MERGED_DEM_NAME
    clipped_dem = output_dir / CLIPPED_DEM_NAME
    
    tile_paths = extract_dem_zips(tiles_dir, extract_dir)

    merged_dem = merge_dem_tiles(tile_paths, merged_dem)

    reprojected_dem = output_dir / f"dem_epsg{DESIRED_EPSG}.tif"
    reprojected_dem = reproject_dem(
        merged_dem,
        reprojected_dem,
        DESIRED_EPSG
    )

    clipped_dem = clip_dem_by_aoi(
        reprojected_dem,
        Path(aoi_path),
        AOI_LAYER,
        clipped_dem
    )

    # export_rendered_dem(
    #     clipped_dem,
    #     output_dir / RENDERED_DEM_NAME,
    #     PERCENTILE_CLIP
    # )
    
    export_rendered_dem_uint16(
        clipped_dem,
        output_dir / RENDERED_DEM_NAME
    )

    # AOI mask
    create_vector_mask(
        clipped_dem,
        Path(aoi_path),
        output_dir / AOI_MASK_NAME
    )
    
    # WATER MASK (LAKES + RIVERS)
    # lakes_shp = extract_vector_zip(
    #     Path(WATER_LAKES_ZIP),
    #     Path(WATER_EXTRACT_DIR),
    #     WATER_LAKES_SHP
    # )

    # rivers_shp = extract_vector_zip(
    #     Path(WATER_RIVERS_ZIP),
    #     Path(WATER_EXTRACT_DIR),
    #     WATER_RIVERS_SHP
    # )

    # create_merged_water_mask(
    #     clipped_dem,
    #     [lakes_shp, rivers_shp],
    #     output_dir / WATER_MASK_NAME
    # )
    
    # SENTINEL ORTHOIMAGE
    # Read DEM size
    dem_width, dem_height = get_raster_size(clipped_dem)

    # Sentinel Hub pixel limit
    dem_width, dem_height = fit_to_sentinel_limit(dem_width, dem_height)

    print(f"Requesting Sentinel RGB at {dem_width} x {dem_height}px...")

    sentinel_out = Path(SENTINEL_RGB)
    sentinel_out.parent.mkdir(parents=True, exist_ok=True)

    download_sentinel_rgb(
        aoi_gpkg=AOI_OUTPUT,
        out_tif=str(sentinel_out),
        max_cloud=SENTINEL_MAX_CLOUD,
        time_range=SENTINEL_TIME_RANGE,
        width=dem_width,
        height=dem_height,
    )


    # Optional but recommended: resample to DEM grid (guarantees alignment)
    sentinel_draped = output_dir / "sentinel/sentinel_draped.tif"

    resample_raster_to_dem(
        sentinel_out,
        clipped_dem,
        sentinel_draped
    )

    # PRINT BLENDER DIMENSIONS
    print_blender_dims(output_dir / RENDERED_DEM_NAME)


if __name__ == "__main__":
    main()
