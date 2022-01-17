from typing import List

from game.obj.JaydenInfo import JaydenInfo


class Round:

    def __init__(self, num: int, celebs: List = None, is_jayden: bool = False, jayden_info: JaydenInfo = None):
        self.num = num
        self.celebs = celebs
        self.is_jayden = is_jayden
        self.jayden_info = jayden_info


    # TODO: Remove override when the client-side JS code supports the above (cleaner) format
    def to_json(self):
        return {
            'num': self.num,
            'image1': self.celebs[0].url,
            'image2': self.celebs[1].url,
            'image3': self.celebs[2].url,
            'name1': self.celebs[0].name,
            'name2': self.celebs[1].name,
            'name3': self.celebs[2].name,
            'isJayden': self.is_jayden,
            'jaydenStat': str(self.jayden_info.stat) if self.jayden_info is not None else None,
            'jaydenUsername': self.jayden_info.username if self.jayden_info is not None else None,
            'jaydenVideoId': self.jayden_info.video_id if self.jayden_info is not None else None,
            'jaydenVideoStartTime': self.jayden_info.start_time if self.jayden_info is not None else None

        }
