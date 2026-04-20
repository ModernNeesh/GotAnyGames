import os
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter, Retry
import pandas as pd

#Load environment variables
load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")

#Gets access token for authentication
def get_access_token():
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")


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
    # Set up a single persistent session (much faster + API friendly)
    session = requests.Session()
    session.headers.update({
        'Client-ID': CLIENT_ID,
        'Authorization' : f'Bearer {access_token}',
    })

    data = "fields name, game_modes, genres, platforms, rating, summary, platforms; " \
    "where game_modes = (2,3,4,5);"

    # Add robust retry logic (prevents failures on 503 / 504 / timeouts)
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    
    try:
        url = 'https://api.igdb.com/v4/games'
        resp = session.post(url, data=data, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return pd.DataFrame(data)
    except Exception as e:
        print(f"Error: {e}")
        return
    

def get_field_names(field, access_token):

    data_path = f"{field}_names.csv"
    #If we already have a csv with field names, read it in.
    if os.path.exists(data_path):
        field_names_df = pd.read_csv(data_path)
        max_id = field_names_df['id'].max()
    else:
        field_names_df = pd.DataFrame(columns=['id', 'name'])
        max_id = 0
    
    session = requests.Session()
    session.headers.update({
        'Client-ID': CLIENT_ID,
        'Authorization' : f'Bearer {access_token}',
    })

    offset = 0
    limit = 500
    num_returned = limit

    print("Starting retrieval of field names...")
    while(num_returned >= limit):
        data = f"fields name; where id > {max_id}; limit {limit}; offset {offset};"
        try:
            url = f'https://api.igdb.com/v4/{field}'
            resp = session.post(url, data=data, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                num_returned = len(data)
                offset += limit
                field_names_df = pd.concat([field_names_df, pd.DataFrame(data)], ignore_index=True)
                print(f"Retrieved {num_returned} {field} (offset {offset})")
        except Exception as e:
            print(f"Error: {e}")
            break
    
    field_names_df.to_csv(data_path, index=False)


def ids_to_names(df, column):
    return


access_token = get_access_token()

print("Getting field names...")
get_field_names(field="game_modes", access_token=access_token)









