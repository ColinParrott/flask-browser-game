from pymongo import MongoClient
from config import DB_URI

db_client = MongoClient(DB_URI)
