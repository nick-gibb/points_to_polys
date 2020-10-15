# Determining the health region of Canada's cities/towns/villages

- Recommended to use VS Code development container due to the Python geospatial dependencies (e.g. GDAL). Required libraries: `geopandas` (specified in Dockerfile)

- Required datasets: (1) ECCC's cities/towns/etc; (2) health region polygons

- To run: `python main.py`. Produces a csv file with the cities/towns and the associated HR_UID.