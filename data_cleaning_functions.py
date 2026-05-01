import pandas as pd
import logging
import yaml
from api_functions import get_feature_names
from pandas.api.types import is_datetime64_any_dtype as is_datetime

# Load config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

def ids_to_names(df, column, access_token):
    """
    Function to convert a column of lists of ids to a column of lists of names using the corresponding id-to-name map csv.

    Inputs: 
    df (pd.DataFrame): Dataframe containing the column to be converted
    column (str): Name of the column to be converted

    Returns:
    new_col (pd.Series): Series containing the converted column
    """
    names_df = get_feature_names(column, access_token)
    id_to_name = dict(zip(names_df['id'], names_df['name']))
    new_col = df[column].apply(lambda ids: [id_to_name.get(i, "Unknown") for i in ids] if isinstance(ids, list) else ids)
    return new_col


def split_list_columns(df, access_token):
    """
    Function to clean list-type columns through the following:
    1. Convert lists of ids to lists of names using the corresponding id-to-name map csv.
    2. Expand lists of names into one-hot columns for each name.

    Inputs:
    df (pd.DataFrame): Dataframe containing the columns to be cleaned

    Returns:
    new_df (pd.DataFrame): Dataframe with cleaned columns
    """
    new_df = df.copy()
    columns = new_df.columns
    for col in columns:
        if new_df[col].dtype == 'object' and new_df[col].apply(lambda x: isinstance(x, list)).any():
            logging.info("Cleaning column: %s", col)
            subbed_col = ids_to_names(new_df, col, access_token) #Convert ids to names
            expanded_cols = pd.get_dummies(subbed_col.explode(), prefix=col).groupby(level=0).sum().astype(int) #Expand into one-hot columns
            new_df = pd.concat([new_df.drop(col, axis=1), expanded_cols], axis=1) #Concatenate with original dataframe
            logging.info("Finished cleaning column: %s", col)
    return new_df


def deduplicate(df):
    """
    Deduplicate dataframe so that the id column is unique.
    Drop duplicates by keeping the most recent entry (highest value of updated_at).
    Saves output to 

    Inputs:
    df (pd.DataFrame): Dataframe to be deduplicated
    
    Returns:
    deduplicated_df (pd.DataFrame): Dataframe with unique id values, keeping most recent entries
    """
    logging.info("Deduplicating dataframe by id column")
    assert is_datetime(df['updated_at']), "updated_at column must be of datetime type for deduplication"
    
    # Sort by updated_at in descending order to keep the most recent entries
    df_sorted = df.sort_values('updated_at', ascending=False)

    # Drop duplicates, keeping the first occurrence (most recent due to sort)
    deduplicated_df = df_sorted.drop_duplicates(subset=['id'], keep='first')

    # Reset index to maintain clean indexing
    deduplicated_df = deduplicated_df.reset_index(drop=True)
    logging.info("Deduplication complete. Removed %d duplicate entries", len(df) - len(deduplicated_df))
    return deduplicated_df


def clean_games_data(games_df, access_token):
    """
    Function to clean games dataframe through the following:
    1. Set appropriate data types for each column 
    2. Convert lists of ids to lists of names using the corresponding id-to-name map csv.
    3. Expand lists of names into one-hot columns for each name.
    4. Deduplicate dataframe so that the id column is unique, keeping the most recent entry.
    5. Handle missing values.
    6. Fix rows where columns give conflicting information

    Inputs:
    df (pd.DataFrame): Games dataframe to be cleaned

    Returns:
    cleaned_df (pd.DataFrame): Cleaned games dataframe
    """
    #1. Set appropriate data types for each column
    dtypes = config['games_dtypes']
    cleaned_df = games_df.astype(dtypes)

    # 2. Convert lists of ids to lists of names using the corresponding id-to-name map csv.
    # 3. Expand lists of names into one-hot columns for each name.
    cleaned_df = split_list_columns(cleaned_df, access_token)

    #4. Deduplicate dataframe so that the id column is unique, keeping the most recent entry.
    cleaned_df = deduplicate(cleaned_df)

    #5. Handle missing values (maintain column data type while adding impossible values)
    cleaned_df.fillna({'rating': -1, 'first_release_date': pd.Timestamp(0)}, inplace=True)

    #6. Fix rows where columns give conflicting information
    cleaned_df = fix_inaccurate_multiplayer_columns(cleaned_df)
    return cleaned_df



def clean_multiplayer_modes_data(modes_df, games_data):
    """
    Function to clean multiplayer modes dataframe through the following:
    1. Set appropriate data types for each column and handle missing values.
    2. Convert platform ids to names using the corresponding id-to-name map csv.
    3. Fix rows where columns give conflicting information

    Inputs:
    modes_df (pd.DataFrame): Multiplayer modes dataframe to be cleaned
    games_df (pd.DataFrame): Cleaned games dataframe; to be used when handling conflicts

    Returns:
    cleaned_df (pd.DataFrame): Cleaned multiplayer modes dataframe
    """
    logging.info("Cleaning multiplayer modes dataframe...")

    #1. Set appropriate data types for each column and handle missing values. 
    dtypes = config['multiplayer_modes_dtypes']
    cleaned_df = modes_df.fillna(-1).astype(dtypes)

    #2. Convert platform ids to names using the corresponding id-to-name map JSON.
    platform_df_fp = config['feature_maps_folder'] + config['feature_maps_fp_template'].format(field='platforms')
    platform_id_to_name = pd.read_json(platform_df_fp, orient='records')
    platform_id_to_name_dict = dict(zip(platform_id_to_name['id'], platform_id_to_name['name']))

    cleaned_df['platform'] = cleaned_df['platform'].apply(lambda x: platform_id_to_name_dict.get(x, "Unknown"))

    #3. Fix rows that give conflicting information
    cleaned_df = fix_conflicted_coop_columns(cleaned_df, games_data)

    return cleaned_df





def get_replacement_function(coop_column, coop_max_column, max_column):
    """
    Function to create function that solves conflicts across certain columns in multiplayer modes data.
    i.e., the 'offlinecoop' column may have a value of True, while the 'offlinecoopmax' column has a value of 0. The data from one column contradicts the other.

    Inputs: 
    coop_column (str): The boolean column that specifies whether a multiplayer mode supports online/offline coop 
    coop_max_column (str): The integer column that specifies the maximum number of players for offline coop
    max_column (str): The integer column that specifies the maximum number of players for offline play.

    Returns:
    replace_conflict_columns (function): Function to fix the conflicts in the given set of columns.
    """
    def replace_conflict_columns(row):
        return_row = row.copy()

        #offlinecoop == True
        if row[coop_column]:
            #offlinecoopmax < 0
            if row[coop_max_column] < 0:
                #offlinemax > 0 -- Case 1 
                if row[max_column] > 0:
                    if row['game_modes_Co-operative'] == 1:
                        return_row[coop_max_column] = row[max_column]
                    else:
                        return_row[coop_column] = False
                        return_row[coop_max_column] = 0
                        return_row[max_column] = 0
                #Any potential future cases that could occur
                else:
                    return_row[coop_column] = False
                    return_row[coop_max_column] = 0
                    return_row[max_column] = 0
                    
                
            #offlinecoopmax == 0
            elif row[coop_max_column] == 0 :
                #offlinemax > 0 -- Case 2
                if row[max_column] > 0:
                    return_row[coop_max_column] = row[max_column]
                #Any potential future cases that could occur
                else:
                    return_row[coop_column] = False
                    return_row[coop_max_column] = 0
                    return_row[max_column] = 0

            
            #offlinecoopmax > 0
            else:
                if row[max_column] < 0:
                    return_row[max_column] = 0
                #Uncomment the following line if the distinction between PvP and Co-Op is not made
                #return_row[max_column] = row[coop_max_column]
                pass

        #offlinecoop == False
        else:
            #offlinecoopmax < 0
            if row[coop_max_column] < 0:
                #Nothing else to do here except fill null values
                if row[max_column] < 0:
                    return_row[max_column] = 0
                return_row[coop_max_column] = 0

            #offlinecoopmax == 0
            elif row[coop_max_column] == 0:
                #offlinemax > 0 -- Case 3
                #We can always assume offlinemax is 0 in this case
                return_row[max_column] = 0

            #offlinecoopmax > 0
            else:
                #offlinemax < 0 -- Case 4
                #offlinemax = 0 -- Case 5
                #We can always assume offlinemax is 0 in this case
                return_row[coop_max_column] = 0
                return_row[max_column] = 0

        return return_row
    return replace_conflict_columns




def fix_conflicted_coop_columns(modes_df, games_data):
    """
    Function to fix rows where data conflicts across various columns

    Inputs: 
    modes_df: DataFrame of multiplayer modes data
    games_data: Data of game ids and co-op capability from games data

    Output:
    Returns a dataframe with the conflicting rows fixed 
    """
    df_with_games = modes_df.merge(games_data, left_on='game', right_on='id', how='left', suffixes=('', '_game'))
    df_with_games = df_with_games.apply(get_replacement_function(**config['multiplayer_modes_conflicts']['online']), axis = 1)
    df_with_games = df_with_games.apply(get_replacement_function(**config['multiplayer_modes_conflicts']['offline']), axis = 1)

    df_with_games.drop(columns = ['id_game', 'game_modes_Co-operative'], inplace = True)

    return df_with_games


def fix_inaccurate_multiplayer_columns(games_df):
    """
    Function to create function that solves conflicts across certain columns in games data.
    i.e., if a game supports Co-Op play, the value in the Multiplayer column should be 1. 
    
    """

    multiplayer_cols = config['multiplayer_cols']
    return_df = games_df.copy()

    for column in multiplayer_cols:
        rows_to_fix = return_df[(return_df['game_modes_' + column] > 0) & (return_df['game_modes_Multiplayer'] == 0)].index

        return_df.loc[rows_to_fix, 'game_modes_Multiplayer'] = 1
    
    return return_df