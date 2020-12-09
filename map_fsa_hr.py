import click
import logging
import os
from pathlib import Path
import sys
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.DEBUG)


def load_data(fluwatch, correspondence):
    """ Loads the fluwatch data (FSA-level), the reference file (from Yann), and the FSA population lookup dataframe """
    logging.info("Loading data...")
    # Load fluwatch data
    fluwatch_filepath = os.path.join('data', 'fsa_to_hr', fluwatch)
    df_fluwatch = pd.read_csv(fluwatch_filepath, index_col='FSA')

    # Load boundaries and population data (from Yann)
    df_filepath = os.path.join('data', 'fsa_to_hr', correspondence)
    df = pd.read_csv(df_filepath, encoding='latin1')

    # Get populations of FSA from pivot table
    fsa_populations = pd.pivot_table(df, index=['FSA'], values=[
                                     'DAPOP2020'], aggfunc=np.sum).to_dict()['DAPOP2020']

    logging.info("Data loaded.")
    return df_fluwatch, df, fsa_populations


def expand_df(df_fluwatch, df, fsa_populations):
    """ One dataframe apply operation to add the neccesary fields to the dataframe """
    logging.info("Expanding dataframe...")

    def expander(row):
        # Yann already obtained DA population in the spreadsheet
        da_population = row['DAPOP2020']
        # FSA population from pivot table
        fsa_population = fsa_populations[row['FSA']]
        da_population_fraction = da_population / \
            fsa_population  # Factor for weighting Fluwatch data

        # Fluwatch participants at DISSEMINATION AREA level
        try:  # Must be try/except because many FSAs have no data
            fsa_participants = df_fluwatch.loc[row['FSA']]['participants']
        except:
            fsa_participants = 0  # If no Fluwatch data, assign 0
        # Multiply by population weighting factor
        da_participants = fsa_participants * da_population_fraction

        # Fluwatch confirmed positive at DISSEMINATION AREA level
        try:
            fsa_confirmed_pos = df_fluwatch.loc[row['FSA']]['confirmed_pos']
        except:
            fsa_confirmed_pos = 0
        # Multiply by population weighting factor
        da_confirmed_pos = da_population_fraction * fsa_confirmed_pos

        # Expand dataframe by six columns
        return fsa_population, da_population_fraction, fsa_participants, fsa_confirmed_pos, da_participants, da_confirmed_pos
    # Call to transformation function
    columns_to_add = ['fsa_population', 'da_population_fraction',
                      'fsa_participants', 'fsa_confirmed_positive',
                      'da_participants', 'da_confirmed_positive']
    df[columns_to_add] = df.apply(expander, axis=1, result_type="expand")
    logging.info("Dataframe expanded.")
    return df


def make_hr_table(df_expanded):
    """ Aggregate dissemination areas up to health region """
    logging.info("Generating health region table...")
    df_hr = pd.pivot_table(df_expanded, index=['HR_UID'], values=[
                           'da_participants', 'da_confirmed_positive'], aggfunc=np.sum)
    df_hr = df_hr.rename({'da_confirmed_positive': 'confirmed_positive',
                          'da_participants': 'participants'}, axis=1)
    df_hr = df_hr.round(0).astype(int)  # round to integer
    df_hr.loc[df_hr['participants'] < 5, ['participants', 'confirmed_positive']
              ] = "data_suppressed"  # remove HRs with less than five participants
    logging.info("Health region table generated.")
    return df_hr


def export_data(df_expanded, df_hr, hr_path, correspondence_path):
    """ Exports expanded dataframe (for reference) and flu watcher data at HR-level (final output) """
    logging.info("Exporting data...")
    output_folder = get_output_folder(hr_path)
    epi_week = get_epi_week(hr_path)
    expanded_df_filename = output_folder.joinpath(
        'reference', f'{epi_week}_expanded_df_{correspondence_path.stem}.csv')
    # hr_fluwatchers_filename = output_folder.joinpath(f'{epi_week}_hr_fluwatchers_{correspondence_path.stem}.csv')
    hr_fluwatchers_filename = 'hr_fluwatchers.csv'
    df_hr.to_csv(hr_fluwatchers_filename)  # export HR-level results
    # export base dataframe, for reference
    df_expanded.to_csv(expanded_df_filename)
    logging.info(
        f"Exported {expanded_df_filename} and {hr_fluwatchers_filename}")


def get_output_folder(path):
    output_folder = path.parent.parent.joinpath('output')
    return output_folder


def get_epi_week(fluwatch_path):
    epi_week = fluwatch_path.stem.split('_')[-1]
    print(epi_week)
    return epi_week

def get_canada_df(df_fluwatch):
    canada_participants, canada_confirmed_positive = df_fluwatch[['participants', 'confirmed_pos']].sum().values
    df_canada = pd.DataFrame([[canada_participants, canada_confirmed_positive]], columns=list(['participants', 'confirmed_positive']), index=['Canada'])
    df_canada.index.name = 'HR_UID'
    return df_canada

def append_canada(df_hr, df_canada):
    df_hr = df_hr.append(df_canada)
    return df_hr

@click.command()
@click.option('-f', '--fluwatch', required=True, type=click.Path(exists=True), help='Path to Fluwatch data at forward sorting area level.')
@click.option('-c', '--correspondence', default='/workspaces/hrs_fsa/data/fsa_to_hr/DA_FSA_HR_07132020.csv', show_default=True, required=True, type=click.Path(exists=True), help='Path to correspondence file prepared by Yann.')
def main(fluwatch, correspondence):
    fluwatch_path = Path(fluwatch)
    correspondence_path = Path(correspondence)
    logging.info(f"Processing using input {correspondence}")
    df_fluwatch, df, fsa_populations = load_data(
        fluwatch_path, correspondence_path)
    df_expanded = expand_df(df_fluwatch, df, fsa_populations)
    df_hr = make_hr_table(df_expanded)
    df_canada = get_canada_df(df_fluwatch)
    df_hr = append_canada(df_hr, df_canada)
    export_data(df_expanded, df_hr, fluwatch_path, correspondence_path)


if __name__ == "__main__":
    main() 