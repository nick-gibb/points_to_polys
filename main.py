import json

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

places_df = pd.read_csv('data/ECCCdata_19_0.csv')
places_df['coords'] = list(zip(places_df.LONGITUDE, places_df.LATITUDE))

points_dict = gpd.GeoDataFrame(
    places_df, crs={'init': 'epsg:4269'},
    geometry=places_df['coords'].apply(Point)
).to_dict('records')

# mun_gdf = gdp.read_file('https://opendata.arcgis.com/datasets/3aa9f7b1428642998fa399c57dad8045_0.geojson')
polys_dict = gpd.read_file(
    'data/Health_Regional_Archive__Public_View_.geojson').to_dict('records')
poly_geoms = [poly['geometry'] for poly in polys_dict]


def find_intersecting_poly(pt_geom):
    for poly in polys_dict:
        if pt_geom.within(poly['geometry']):
            return poly['HR_UID']
    return False


for i, point in enumerate(points_dict):
    if i % 10 == 0:
        print(f'Processing point {i}')

    HR_UID = find_intersecting_poly(point['geometry'])

    if not HR_UID:

        min_poly = min(poly_geoms, key=point['geometry'].distance)

        HR_UID = [poly for poly in polys_dict if poly['geometry']
                  == min_poly][0]['HR_UID']

    point['HR_UID'] = HR_UID
    point.pop('geometry')

pd.DataFrame(points_dict).to_csv('output.csv', index=False)
