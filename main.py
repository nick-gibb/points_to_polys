from datetime import datetime
import json
import os
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


def load_data():
    places_df = pd.read_csv(os.path.join('data', 'ECCCdata_19_0.csv'))
    places_df['coords'] = list(zip(places_df.LONGITUDE, places_df.LATITUDE))

    points_dict = gpd.GeoDataFrame(
        places_df, crs='epsg:4269',
        geometry=places_df['coords'].apply(Point)
    ).to_dict('records')

    HR_PATH = os.path.join('data', 'HR COVID',
                           'PopEstimates2019_RegionalHealthBoundaries_Lambert.shp')
    polys_gdf = gpd.read_file(HR_PATH).to_crs(epsg=4269)
    polys_dict = polys_gdf.to_dict('records')

    return (points_dict, polys_dict)


def find_intersecting_poly(pt_geom, polys_dict):
    for poly in polys_dict:
        if pt_geom.within(poly['geometry']):
            return poly['HR_UID']
    return False


def add_HR_UID_field(points_dict, polys_dict):
    poly_geoms = [poly['geometry'] for poly in polys_dict]
    for i, point in enumerate(points_dict):
        if i % 100 == 0:
            print(f'Processing point {i}')

        HR_UID = find_intersecting_poly(point['geometry'], polys_dict)

        if not HR_UID:
            geom_min_poly = min(poly_geoms, key=point['geometry'].distance)
            closest_HR = [
                poly for poly in polys_dict if poly['geometry'] == geom_min_poly]
            HR_UID = closest_HR[0]['HR_UID']

        point['HR_UID'] = HR_UID
        point.pop('geometry')
    return points_dict


def save_csv(points_dict):
    current_date = datetime.now().date().strftime("%Y-%m-%d")
    filename = f'places_to_HRs_{current_date}.csv'
    pd.DataFrame(points_dict).to_csv(filename, index=False)


def main():
    points_dict, polys_dict = load_data()
    points_dict = add_HR_UID_field(points_dict, polys_dict)
    save_csv(points_dict)


if __name__ == "__main__":
    main()
