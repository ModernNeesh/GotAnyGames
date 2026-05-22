import os
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter, Retry
import pandas as pd
import yaml
from pathlib import Path
import logging


#Load environment variables
load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Load config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)


def get_access_token():
    """
    Function to get access token for Twitch API using client credentials flow.

    Returns: access_token (str): Access token for Twitch API
    """

    #Post request
    url = f"https://id.twitch.tv/oauth2/token"
    params = {
        'client_id' : CLIENT_ID,
        'client_secret' : CLIENT_SECRET,
        'grant_type' : 'client_credentials'
    }
    response = requests.post(url=url, params=params)

    #Return access token if request succeeds
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        logging.error("Error: status code %s", response.status_code)
        exit()


#General function to request data




def request_data(access_token, request_params_key, url, df, last_updated, data_type):
    """
    Generic function to request paginated data from IGDB API.

    Inputs:
    access_token (str): Access token for Twitch API
    request_params_key (str): Key in config for request parameters (e.g., 'games_request_params')
    url (str): API endpoint URL
    csv_output_path (Path): Path to save CSV output
    df (pd.DataFrame): DataFrame to append data to
    last_updated (int): Timestamp for filtering updated data
    data_type (str): String indicating the type of data being requested (for logging purposes)

    Returns:
    df (pd.DataFrame): Updated dataframe with retrieved data
    """

    # Set up a single persistent session (much faster + API friendly)
    session = requests.Session()
    session.headers.update({
        'Client-ID': CLIENT_ID,
        'Authorization' : f'Bearer {access_token}',
    })

    # Add robust retry logic (prevents failures on 503 / 504 / timeouts)
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))

    offset = 0
    limit = config['api_request_limit']
    num_returned = limit

    # Looping until we get less than the limit (indicates we've reached the end of the data)
    while(num_returned >= limit):
        
        # Load request data from config and format with last_updated, limit, and offset
        request_fields = "fields " + config[request_params_key]['fields'] + "; "
        request_filters = config[request_params_key]['filters'].format(last_updated=last_updated, limit=limit, offset=offset)
        data = request_fields + request_filters

        try:
            resp = session.post(url, data=data, timeout=10)
            if resp.status_code == 200:
                # Get data and set offset for next request
                resp_data = resp.json()
                num_returned = len(resp_data)
                offset += limit

                # Add data to dataframe
                if len(resp_data) > 0:
                    df = pd.concat([df, pd.DataFrame(resp_data)], ignore_index=True)
                if num_returned < limit:
                    logging.info("Retrieved %s records for %s. Reached end of data.", num_returned, data_type)
                else:
                    if offset % (limit*10) == 0: #Log every 10 requests
                        logging.info("Retrieved %s records for %s", offset, data_type)    
            else:
                logging.error("Error: status code %s", resp.status_code)
                logging.error("Data received: %s", resp_data)
                break
        except Exception as e:
            logging.error("Error: %s", e)
            return df
        
    return df





#Games endpoint





def get_games(access_token):
    """
    Function to get games from IGDB API.

    Inputs:
    access_token (str): Access token for Twitch API

    Returns:
    df (pd.DataFrame): Dataframe containing games
    """

    games_raw_fp = Path(config['games_folder'] + config['games_raw_fp'])
    if os.path.exists(games_raw_fp) and os.path.getsize(games_raw_fp) > 0:
        df = pd.read_json(games_raw_fp, orient='records')
        last_updated = int(df['updated_at'].max().timestamp()) 
    else:
        df = pd.DataFrame(columns = config['games_request_params']['fields'].split(','))
        last_updated = 0 #Get all data if we don't have a previous file
        
    logging.info("Making requests...")
    url = 'https://api.igdb.com/v4/games'
    df = request_data(access_token, 'games_request_params', 
                      url, df,
                      last_updated, data_type="games")
    
    if len(df) > 0:
        logging.info("Saving raw games data to: %s", games_raw_fp)
        df.to_json(games_raw_fp, orient='records', date_format='iso')
        logging.info("Saved raw games dataframe with %s records", len(df))

    return df

def get_covers(access_token):
    """
    Function to get covers data from IGDB API.

    Inputs:
    access_token (str): Access token for Twitch API

    Returns:
    df (pd.DataFrame): Dataframe containing multiplayer modes data
    """

    covers_fp = Path(config['covers_folder'] + config['covers_fp'])
    if os.path.exists(covers_fp) and os.path.getsize(covers_fp) > 0:
        old_data = pd.read_json(covers_fp, orient='records')
    else:
        
        old_data = None
    logging.info("Making requests for covers data...")
    url = 'https://api.igdb.com/v4/covers'

    new_data = pd.DataFrame([config['covers_request_params']['unknown_value']], columns = config['covers_request_params']['fields'].split(','))
    new_data = request_data(access_token, 'covers_request_params', 
                      url, new_data,
                      last_updated=-1, data_type="covers")
    
    if old_data is not None:
        #Add new rows from new_data to old_data
        new_data = new_data[~new_data['id'].isin(old_data['id'])]
        if len(new_data) > 0:
            full_df = pd.concat([old_data, new_data], ignore_index=True)
            logging.info("Added %s new records to multiplayer modes data", len(new_data))
        else:
            full_df = old_data
            logging.info("No new records found for multiplayer modes data")
    else:
        full_df = new_data

    new_data['url'] = "https:" + new_data['url']
    
    if len(full_df) > 0:
        logging.info("Saving covers data to: %s", covers_fp)
        full_df.to_json(covers_fp, orient='records', date_format='iso')
        logging.info("Saved covers dataframe with %s records", len(full_df))

    return full_df





#Multiplayer Modes endpoint



def get_multiplayer_modes(access_token):
    """
    Function to get multiplayer modes data from IGDB API.

    Inputs:
    access_token (str): Access token for Twitch API

    Returns:
    df (pd.DataFrame): Dataframe containing multiplayer modes data
    """

    multiplayer_modes_raw_fp = Path(config['multiplayer_modes_folder'] + config['multiplayer_modes_raw_fp'])
    if os.path.exists(multiplayer_modes_raw_fp) and os.path.getsize(multiplayer_modes_raw_fp) > 0:
        old_data = pd.read_json(multiplayer_modes_raw_fp, orient='records')
    else:
        
        old_data = None
    logging.info("Making requests for multiplayer modes data...")
    url = 'https://api.igdb.com/v4/multiplayer_modes'

    new_data = pd.DataFrame(columns = config['multiplayer_modes_request_params']['fields'].split(','))
    new_data = request_data(access_token, 'multiplayer_modes_request_params', 
                      url, new_data,
                      last_updated=-1, data_type="multiplayer modes")
    
    if old_data is not None:
        #Add new rows from new_data to old_data
        new_data = new_data[~new_data['id'].isin(old_data['id'])]
        if len(new_data) > 0:
            full_df = pd.concat([old_data, new_data], ignore_index=True)
            logging.info("Added %s new records to multiplayer modes data", len(new_data))
        else:
            full_df = old_data
            logging.info("No new records found for multiplayer modes data")
    else:
        full_df = new_data
    
    if len(full_df) > 0:
        logging.info("Saving raw multiplayer modes data to: %s", multiplayer_modes_raw_fp)
        full_df.to_json(multiplayer_modes_raw_fp, orient='records', date_format='iso')
        logging.info("Saved raw multiplayer modes dataframe with %s records", len(full_df))

    return full_df





#Lookup and junction tables



def get_junction_table(df, column):
    """
    Function to save a column's values as a junction table (game_id to feature id mapping)

    Inputs:
    df (pd.DataFrame): DataFrame containing data to be saved
    column (str): Column of df to convert into a junction table. Must be a column of lists.

    Returns:
    column_exploded (pd.DataFrame): DataFrame version of junction table.
    """

    junction_fp = Path(config['junctions_folder'] + config['junctions_fp_template'].format(field=column))

    column_exploded = df[['id', column]].explode(column)

    column_exploded.columns = ['game_id', column + '_id']

    column_exploded.drop_duplicates(inplace = True)
    column_exploded.dropna(inplace = True)

    column_exploded.to_json(junction_fp, orient = 'records', date_format = 'iso')

    return column_exploded





def get_lookup_tables(field, access_token):

    """
    Function to get names of a specific field from IGDB API.

    Inputs:
    field (str): The field for which to get names
    access_token (str): Access token for Twitch API

    Returns:
    field_names_df (pd.DataFrame): Dataframe containing the names of the specified field
    """

    field_names_data_path = Path(config['lookups_folder'] + config['lookups_fp_template'].format(field=field))
    #If we already have a json with field names, read it in.
    if os.path.exists(field_names_data_path) and os.path.getsize(field_names_data_path) > 0:
        field_names_df = pd.read_json(field_names_data_path, orient='records')
        last_updated = int(field_names_df['updated_at'].max().timestamp()) if not field_names_df.empty else 0
    else:
        #Initialize with a value for unknown data
        field_names_df = pd.DataFrame([config['feature_names_request_params']['unknown_value']], columns = config['feature_names_request_params']['fields'].split(","))
        last_updated = 0 #Get all data if we don't have a previous file

    url = f'https://api.igdb.com/v4/{field}'
    field_names_df = request_data(access_token, 'feature_names_request_params', 
                                  url, field_names_df, 
                                  last_updated, data_type=field)
    
    dtypes = config['lookup_dtypes']
    field_names_df = field_names_df.astype(dtypes)

    
    if len(field_names_df) > 0:
        logging.info("Saving %s names data to: %s", field, field_names_data_path)
        field_names_df.to_json(field_names_data_path, orient='records', date_format='iso')
        logging.info("Saved %s names dataframe with %s records", field, len(field_names_df))

    return field_names_df





def get_lookup_and_junction(features_df, access_token):
    """
    Function to get a lookup table for each feature as well as separate it into a junction table.

    Inputs:
    features_df (pd.DataFrame): Dataframe containing the columns to be cleaned
    access_tokem (int): Access token

    """
    columns = features_df.columns
    for col in columns:
        if col == 'id':
            continue

        assert features_df[col].dtype == 'object' and features_df[col].apply(lambda x: isinstance(x, list)).any()

        logging.info("Getting lookup and junction for: %s", col)
        get_lookup_tables(col, access_token) 
        get_junction_table(features_df, col)
        logging.info("Created lookup and junction for: %s", col)
