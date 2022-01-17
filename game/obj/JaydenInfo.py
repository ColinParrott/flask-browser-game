from game.obj.consts.Choice import Choice


class JaydenInfo:

    def __init__(self, stat: Choice, username: str, video_id: str, start_time: int):
        self.stat = stat
        self.username = username
        self.video_id = video_id
        self.start_time = start_time
