import pandas as pd
import sqlalchemy as sa
from src.sql_loading_helpers import *
from dotenv import load_dotenv
import os

load_dotenv()
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# Create the engine
engine = sa.create_engine(f'postgresql://postgres:{POSTGRES_PASSWORD}@localhost:5432/GamesDatabase')

#Start logging
logging.basicConfig(filename='logging/app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

updates = [pd.Timestamp(year=2000, month = (i+1), day = 1) for i in range(3)]
base_df = pd.DataFrame({'id': [1234, 4567, 7890], 'name': ["ab", "cd", "ef"], 'updated_at' : updates})

def initialize_test_case(tablename):
    with engine.begin() as conn:
        base_df.set_index('id').to_sql(tablename, conn, if_exists='replace', index=True)





#Test case 1: Updating an existing dataframe with update date less than or equal to existing data 
initialize_test_case('test_case_1')
#Try to add conflicting data from the same day
new_df = pd.DataFrame({'id': [1234, 4567, 7890], 'name': ["Updated!", "Updated!", "Updated!"], 'updated_at' : updates})
update_data_with_pkey(new_df, 'test_case_1', has_updated_at=True) #Should have the original names



#Test case 2: Updating an existing dataframe with more recently updated data
initialize_test_case('test_case_2')
new_updates = [pd.Timestamp(year=2000, month = (i+1), day = 2) if i > 0 else updates[i] for i in range(3)] #Only the second and third ids have been updated
#Try to add conflicting data from the same day
new_df = pd.DataFrame({'id': [1234, 4567, 7890], 'name': ["Updated!", "Updated!", "Updated!"], 'updated_at' : new_updates})
update_data_with_pkey(new_df, 'test_case_2', has_updated_at=True) #Should only have updated names for second and third ids



#Test case 3: Update an existing dataframe without using update data
initialize_test_case('test_case_3')
update_data_with_pkey(new_df, 'test_case_3', has_updated_at=False) #Should have updated names in all rows



#Test case 4: Update an existing dataframe with an empty dataframe
initialize_test_case('test_case_4')
blank_df = pd.DataFrame(columns = ['id', 'name', 'updated_at'])
update_data_with_pkey(blank_df, 'test_case_4', has_updated_at=True) #Has base data
update_data_with_pkey(blank_df, 'test_case_4', has_updated_at=False) #Has base data



#Test case 5/6: Insert a completely new dataframe
update_data_with_pkey(base_df, 'test_case_5', has_updated_at=True) #Has base data
update_data_with_pkey(base_df, 'test_case_6', has_updated_at=False) #Has base data



#Test case 7/8: Insert new data with new ids
initialize_test_case('test_case_7') 
initialize_test_case('test_case_8')

new_ids_updates = [pd.Timestamp(year=2000, month = (i+1), day = 1) for i in range(5)]
new_df_new_ids = pd.DataFrame({'id': [1234, 4567, 7890, 6543, 43], 'name': ["Updated!", "Updated!", "Updated!", "New Data", "New Data"], 'updated_at' : new_ids_updates})

update_data_with_pkey(new_df_new_ids, 'test_case_7', has_updated_at=True) #3 original rows not updated, new data added
update_data_with_pkey(new_df_new_ids, 'test_case_8', has_updated_at=False) #3 original rows updated, new data added




logging.info("Done running test cases with primary keys!")