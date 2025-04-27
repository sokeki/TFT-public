from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

def get_database():
   CONNECTION_STRING = os.getenv('ATLAS_URI')
   client = MongoClient(CONNECTION_STRING)
   return client['tft']
  
dbname = get_database()

if __name__ == "__main__":   
   dbname = get_database()