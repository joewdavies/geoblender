# DEM preparation for Blender!

Before starting the tutorial, if you want to get a DEM, mask, etc for a country, simply run DEM_prep.py with python installed and the DEM tiles added to the /input/tiles folder!

I downloaded my tiles from https://ec.europa.eu/eurostat/web/gisco/geodata/digital-elevation-model/copernicus#Elevation

simply change `COUNTRY_CODE  = "CH"` in DEM_prep.py to your country of choice!

It will:

- Extract an AOI polygon for the country
- Extract, merge, clip and reproject your DEM files to the desired projection (`DESIRED_EPSG`)
- Provide a 'rendered' (rescaled) version to be used in Blender
- Provide an AOI mask
- Provide a water mask
- Download a Sentinel satellite image for your AOI (you must add your own copernicus tokens for this to a .env file)
  

You can then use these files in blender (see automated.blend)

Like so:

```
$ python DEM_prep.py 
[✓] AOI created for country 'CH' → aoi.gpkg
Extracting 10_DEM_y40x0.zip...
Extracting 10_DEM_y40x10.zip...
[✓] Extracted 2 DEM tiles
[✓] Merged DEM → dem_merged.tif
Reprojecting DEM to EPSG:2056...
[✓] Reprojected DEM → EPSG:2056
[✓] Clipped DEM → dem_clipped.tif
[✓] Rendered DEM → dem_rendered.png
    stretch: 0.00 → 3666.46
[✓] Mask written → aoi_mask.png
Extracting ne_10m_lakes.zip...
Extracting ne_10m_rivers_lake_centerlines.zip...
[✓] Water mask (lakes + rivers) → water_mask.png
Requesting Sentinel RGB at 2500 x 1582px...
[✓] Sentinel-2 RGB written → output\sentinel\sentinel_rgb.tif
[✓] Sentinel resampled to DEM grid → sentinel_draped.tif

--- Blender setup info ---
Rendered DEM dimensions: 4866px x 3080px
Plane scale suggestion:
  X: 4.866
  Y: 3.080
--------------------------
```