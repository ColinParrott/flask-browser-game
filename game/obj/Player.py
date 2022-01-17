from typing import List


class Player:

    def __init__(self, discord_name: str, discord_id: int, nickname: str, choices: List = [],
                 chosen: bool = False):
        self.discord_name = discord_name
        self.discord_id = discord_id
        self.nickname = nickname

        self.choices = choices
        self.chosen = chosen

    def __str__(self):
        return self.discord_name

    def to_json(self):
        return {
            'name': self.discord_name,
            'discord_id': self.discord_id,
            'nickname': self.nickname,
            'choice1': self.choices[0] if len(self.choices) > 0 else None,
            'choice2': self.choices[1] if len(self.choices) > 1 else None,
            'choice3': self.choices[2] if len(self.choices) > 2 else None,
            'chosen': self.chosen
        }
