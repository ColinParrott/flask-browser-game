from pymongo.collection import Collection

import config
from db import db_client
from game.obj.consts.Choice import Choice


class SettingsDatabase:

    def __init__(self):
        self.client = db_client

        if config.test:
            self.db_users = db_client['sma']['test_users']  # type: Collection
        else:
            self.db_users = db_client['sma']['users']  # type: Collection

    def get_number_of_users(self):
        return self.db_users.count()

    def get_all_users(self):
        return list(self.db_users.find())

    def get_jayden_settings(self, discord_id: int, choice: Choice):

        return self.db_users.find_one(
            {
                '_id': int(discord_id)
            },
            projection=
            {
                '_id': False,
                'jayden_' + str(choice) + '.video_id': True,
                'jayden_' + str(choice) + '.start_time': True
            }
        )

    def save_jayden_settings(self, discord_id: int, video: str, start: int, choice: Choice):

        start_time = int(start)
        self.db_users.update_one(
            {
                '_id': int(discord_id)
            },
            {
                '$set':
                    {
                        'jayden_' + str(choice):
                            {
                                'video_id': video,
                                'start_time': start_time
                            }
                    }
            }
        )
