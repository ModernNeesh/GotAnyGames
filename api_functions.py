import os
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter, Retry
import pandas as pd
import numpy as np
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






#Takes access token and returns dataframe of multiplayer games
def get_multiplayer_games(access_token):
    """
    Function to get multiplayer games from IGDB API.

    Inputs:
    access_token (str): Access token for Twitch API

    Returns:
    df (pd.DataFrame): Dataframe containing multiplayer games; contains name, game modes, genres, platforms, and rating
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
        status_forcelist=[429, 500, 502, 503, 504]
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))

    multiplayer_games_raw_fp = Path(config['multiplayer_games_folder'] + config['multiplayer_games_raw_fp'])
    if os.path.exists(multiplayer_games_raw_fp):
        df = pd.read_csv(multiplayer_games_raw_fp)
        last_updated = int(df['updated_at'].max()) 
    else:
        df = pd.DataFrame(columns = ','.split(config['games_request_params']['fields']))
        last_updated = 0 #Get all data if we don't have a previous file
        

    offset = 0
    limit = config['api_request_limit']
    num_returned = limit

    #Looping until we get less than the limit (indicates we've reached the end of the data)
    logging.info("Making requests...")
    while(num_returned >= limit):
        
        #Load request data from config and format with last_updated, limit, and offset
        request_fields = "fields " + config['games_request_params']['fields'] + "; "
        request_filters = config['games_request_params']['filters'].format(last_updated=last_updated, limit=limit, offset=offset)
        data = request_fields + request_filters


        try:
            url = 'https://api.igdb.com/v4/games'
            resp = session.post(url, data=data, timeout=10)
            if resp.status_code == 200:
                #Get data and set offset for next request
                data = resp.json()
                num_returned = len(data)
                offset += limit

                if len(data) > 0:
                    df = pd.concat([df, pd.DataFrame(data)], ignore_index=True)
                logging.info("Retrieved %s games (offset %s)", num_returned, offset)    
            else:
                logging.error("Error: status code %s", resp.status_code)
                logging.error("Data received: %s", data)
                break
        except Exception as e:
            logging.error("Error: %s", e)
            return

    if len(df) > 0:
        df.to_csv(multiplayer_games_raw_fp, index=False)

    return df




def get_feature_names(field, access_token):

    """
    Function to get names of a specific field from IGDB API.

    Inputs:
    field (str): The field for which to get names
    access_token (str): Access token for Twitch API

    Returns:
    field_names_df (pd.DataFrame): Dataframe containing the names of the specified field
    """

    field_names_data_path = Path(config['feature_maps_folder'] + config['feature_maps_fp_template'].format(field=field))
    #If we already have a csv with field names, read it in.
    if os.path.exists(field_names_data_path):
        field_names_df = pd.read_csv(field_names_data_path)
        last_updated = int(field_names_df['updated_at'].max()) if not field_names_df.empty else 0
    else:
        field_names_df = pd.DataFrame(columns= ";".split(config['feature_names_request_params']['fields']))
        last_updated = 0 #Get all data if we don't have a previous file

    session = requests.Session()
    session.headers.update({
        'Client-ID': CLIENT_ID,
        'Authorization' : f'Bearer {access_token}',
    })

    offset = 0
    limit = config['api_request_limit']
    num_returned = limit

    #Looping until we get less than the limit (indicates we've reached the end of the data)
    while(num_returned >= limit):
        
        #Load request data from config and format with last_updated, limit, and offset
        request_fields = "fields " + config['feature_names_request_params']['fields'] + "; "
        request_filters = config['feature_names_request_params']['filters'].format(last_updated=last_updated, limit=limit, offset=offset)
        data = request_fields + request_filters


        try:
            url = f'https://api.igdb.com/v4/{field}'
            resp = session.post(url, data=data, timeout=10)
            if resp.status_code == 200:
                #Get data and set offset for next request
                data = resp.json()
                num_returned = len(data)
                offset += limit

                #Add data to field names dataframe
                if len(data) > 0:
                    field_names_df = pd.concat([field_names_df, pd.DataFrame(data)], ignore_index=True)
                logging.info("Retrieved %s names for %s (offset %s)", num_returned, field, offset)   
            else:
                logging.error("Error: status code %s", resp.status_code)
                logging.error("%s", data)
                break

        except Exception as e:
            logging.error("Error: %s", e)
            return
    
    if len(field_names_df) > 0:
        field_names_df.to_csv(field_names_data_path, index=False)



def download_feature_id_maps(df, access_token):
    """
    Function to download the id-to-name maps for all fields in the multiplayer games dataframe that are list of ids.
    """
    for col in df.columns:
        if df[col].dtype == 'object' and df[col].apply(lambda x: isinstance(x, list)).any():
            get_feature_names(col, access_token)