class CelebStatSet:

    def __init__(self, apps: int, firsts: int, seconds: int, thirds: int):
        self.apps = apps
        self.firsts = firsts
        self.seconds = seconds
        self.thirds = thirds

    def to_json(self):
        return {
            'apps': self.apps,
            'firsts': self.firsts,
            'seconds': self.seconds,
            'thirds': self.thirds
        }