"""
Export BR-DWGD from Google Earth Engine to Google Drive, by variable and year.

After the export tasks complete in GEE, download the files from Drive manually
and move them to data/raw/brdwgd/{variable}/.

Note: GEE exports are asynchronous — check task status at code.earthengine.google.com.
"""
import ee

ee.Authenticate()
ee.Initialize()

VARIABLES = {
    "pr":      "pr",
    "tasmax":  "Tmax",
    "tasmin":  "Tmin",
    "rss":     "Rs",
    "sfcWind": "u2",
    "hur":     "RH",
}

YEARS = range(1980, 2014)
BRAZIL = ee.Geometry.Rectangle([-73, -33, -34, 5])
BRDWGD = ee.ImageCollection("projects/ee-alexandrexavier/assets/BR-DWGD")

for var_name, var_gee in VARIABLES.items():
    for year in YEARS:
        collection = (
            BRDWGD
            .select(var_gee)
            .filterDate(f"{year}-01-01", f"{year}-12-31")
            .filterBounds(BRAZIL)
        )

        # Use sum for precipitation, mean for other variables
        if var_name == "pr":
            image = collection.sum()
        else:
            image = collection.mean()

        task = ee.batch.Export.image.toDrive(
            image=image,
            description=f"brdwgd_{var_name}_{year}",
            folder="brdwgd_exports",
            region=BRAZIL,
            scale=10000,
            fileFormat="GeoTIFF",
            maxPixels=1e9,
        )
        task.start()
        print(f"[SUBMITTED] {var_name} {year} — check GEE Tasks panel")
