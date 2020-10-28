import logging
import os
import sys
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.DEBUG)


def load_data(filename):
    """ Loads the fluwatch data (FSA-level), the reference file (from Yann), and the FSA population lookup dataframe """
    logging.info("Loading data...")
    # Load fluwatch data
    fluwatch_filepath = os.path.join('data', 'fsa_to_hr', 'FWR_CLI.csv')
    df_fluwatch = pd.read_csv(fluwatch_filepath, index_col='FSA')

    # Load boundaries and population data (from Yann)
    df_filepath = os.path.join('data', 'fsa_to_hr', filename)
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
            fsa_participants = df_fluwatch.loc[row['FSA']]['Participants']
        except:
            fsa_participants = 0  # If no Fluwatch data, assign 0
        # Multiply by population weighting factor
        da_participants = fsa_participants * da_population_fraction

        # Fluwatch confirmed positive at DISSEMINATION AREA level
        try:
            fsa_confirmed_pos = df_fluwatch.loc[row['FSA']]['CorF_Pos']
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
    df_hr = df_hr[df_hr['participants']>=5] # remove HRs with less than five participants
    logging.info("Health region table generated.")
    return df_hr


def export_data(df_expanded, df_hr, filename):
    """ Exports expanded dataframe (for reference) and flu watcher data at HR-level (final output) """
    filename = filename.strip('.csv')
    logging.info("Exporting data...")
    df_hr.to_csv(f'{filename}_hr_fluwatchers.csv')  # export HR-level results
    # export base dataframe, for reference
    df_expanded.to_csv(f'{filename}_expanded_dataframe.csv')
    logging.info("Data exported.")


def main(filenames):
    for filename in filenames: # If multiple files to process
        logging.info(f"Processing using input {filename}")
        df_fluwatch, df, fsa_populations = load_data(filename)
        df_expanded = expand_df(df_fluwatch, df, fsa_populations)
        df_hr = make_hr_table(df_expanded)
        export_data(df_expanded, df_hr, filename)



if __name__ == "__main__":
    filenames = sys.argv[1:]
    main(filenames)