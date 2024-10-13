import os 
import shutil
import sqlite3

import pandas as pd
import requests
# pass this in main file to download 

# db_url = "https://storage.googleapis.com/benchmarks-artifacts/travel-db/travel2.sqlite"
# local_file = "Db/travel2.sqlite"
# # The backup lets us restart for each tutorial section
# backup_file = "Db/travel2.backup.sqlite"




#loading DB and initializng teh Db 
#then AFter loading it through db its going to save 2 copys 
# one locally and one backup file 

#connecting own Db 
#
class DB:
    def __init__(self,url,local_path,backup_file,overide:bool=False):
        self.url=url
        self.local_path=local_path
        self.backup_file=backup_file
        self.overide=overide
    def download(self):
        
        # self.overwrite = False
        if self.overwrite or not os.path.exists(self.local_path):
            response = requests.get(self.url)
            response.raise_for_status()  # Ensure the request was successful
            with open(self.local_path, "wb") as f:
                f.write(response.content)
            # Backup - we will use this to "reset" our DB in each section
            shutil.copy(self.local_path, self.backup_file)

    def update_dates(self):
        #connecting DB
        shutil.copy(self.backup_file,self.local_path)
        conn=sqlite3.connect(self.local_path)
        cursor=conn.cursor()

        tables=pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';",conn).name.tolist()
        
        #making it dictionary then saving tabels to key value pair in dict
        tdf={}
        for t in tables:
            tdf[t]=pd.read_sql(f"SELECT * from {t}", conn)




        example_time = pd.to_datetime(
            tdf["flights"]["actual_departure"].replace("\\N", pd.NaT)
        ).max()
        current_time = pd.to_datetime("now").tz_localize(example_time.tz)
        time_diff = current_time - example_time

        
        tdf["bookings"]["book_date"] = (
            pd.to_datetime(tdf["bookings"]["book_date"].replace("\\N", pd.NaT), utc=True)
            + time_diff
        )
        datetime_columns = [
            "scheduled_departure",
            "scheduled_arrival",
            "actual_departure",
            "actual_arrival",
        ]


        for column in datetime_columns:
            tdf["flights"][column] = (
                pd.to_datetime(tdf["flights"][column].replace("\\N", pd.NaT)) + time_diff
            )
        
        for table_name, df in tdf.items():
            df.to_sql(table_name, conn, if_exists="replace", index=False)
        del df
        del tdf
        conn.commit()
        conn.close()

        return self.local_path



