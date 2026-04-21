import os
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter, Retry
import pandas as pd
import numpy as np
from datetime import datetime

#Load environment variables
load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")



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
        print(f"Error: status code {response.status_code}")
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

    if os.path.exists("multiplayer_games.csv"):
        df = pd.read_csv("multiplayer_games.csv")
        last_updated = df['updated_at'].max() 
    else:
        df = pd.DataFrame(columns = ['name', 'game_modes', 'genres', 'platforms', 'rating', 'updated_at'])
        last_updated = 0 #Get all data if we don't have a previous file
        

    offset = 0
    limit = 500
    num_returned = limit

    #Looping until we get less than the limit (indicates we've reached the end of the data)
    print("Making requests...")
    while(num_returned >= limit):
        data = "fields name, game_modes, genres, platforms, rating, updated_at;" \
        f"where game_modes = (2,3,4,5) & updated_at > {last_updated}; limit {limit}; offset {offset};"
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
                print(f"Retrieved {num_returned} games (offset {offset})")    
            else:
                print(f"Error: status code {resp.status_code}")
                break
        except Exception as e:
            print(f"Error: {e}")
            return
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

    data_path = fr"feature_id_maps/{field}_names.csv"
    #If we already have a csv with field names, read it in.
    if os.path.exists(data_path):
        field_names_df = pd.read_csv(data_path)
        last_updated = int(field_names_df['updated_at'].max()) if not field_names_df.empty else 0
    else:
        field_names_df = pd.DataFrame(columns=['id', 'name'])
        last_updated = 0 #Get all data if we don't have a previous file

    session = requests.Session()
    session.headers.update({
        'Client-ID': CLIENT_ID,
        'Authorization' : f'Bearer {access_token}',
    })

    offset = 0
    limit = 500
    num_returned = limit

    #Looping until we get less than the limit (indicates we've reached the end of the data)
    while(num_returned >= limit):
        data = f"fields name, updated_at; where updated_at > {last_updated}; limit {limit}; offset {offset};"
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
            else:
                print(f"Error: status code {resp.status_code}")
                print(data)
                break

        except Exception as e:
            print(f"Error: {e}")
            return
    
    if len(field_names_df) > 0:
        field_names_df.to_csv(data_path, index=False)