from pymongo.collection import Collection

from db import db_client


class StatsDatabase:

    def __init__(self):
        self.client = db_client
        self.db_rounds = db_client['sma']['rounds']  # type: Collection
        self.db_users = db_client['sma']['users']  # type: Collection

    def get_number_of_rounds(self):
        return self.db_rounds.count()

    def get_all_rounds(self):
        return list(self.db_rounds.find())

    def get_number_of_users(self):
        return self.db_users.count()

    def get_all_users(self):
        return list(self.db_users.find())
