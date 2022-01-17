import unittest
from game import GameController as gc
from game.obj.Celebrity import Celebrity
from game.obj.JaydenInfo import JaydenInfo
from game.obj.Round import Round
from game.obj.consts.Choice import Choice


class UsernameValidation(unittest.TestCase):

    def test_empty_name(self):
        self.assertFalse(gc.valid_username('', [])[0])

    def test_only_spaces(self):
        self.assertFalse(gc.valid_username('   ', ['a'])[0])

    def test_tab(self):
        self.assertFalse(gc.valid_username('\t ', ['a'])[0])

    def test_carriage_return(self):
        self.assertFalse(gc.valid_username('\r ', ['a'])[0])

    def test_new_line(self):
        self.assertFalse(gc.valid_username('\n ', ['a'])[0])

    def test_invisible_char(self):
        self.assertFalse(gc.valid_username(u"\u00A0", ['a'])[0])

    def test_name_already_present(self):
        self.assertFalse(gc.valid_username('john', ['john', 'ronald', 'meme'])[0])

    def test_valid(self):
        self.assertTrue(gc.valid_username('john', ['kevin', 'steve'])[0])

    def test_emoji(self):
        self.assertTrue(gc.valid_username('huff papa u"\U0001F624"', ['kev'])[0])


class DictOverrides(unittest.TestCase):

    def test_round_to_dict_correct_non_jayden(self):
        celebs = [Celebrity('John', 'John.png'), Celebrity('Steve', 'Steve.png'),
                  Celebrity('Kevin Keg', 'Kevin Keg.png')]
        round = Round(num=1, celebs=celebs, is_jayden=False)

        desired_dict = {
            'num': 1,
            'isJayden': False,
            'jaydenStat': None,
            'jaydenUsername': None,
            'jaydenVideoId': None,
            'jaydenVideoStartTime': None,
            'image1': 'John.png',
            'image2': 'Steve.png',
            'image3': 'Kevin Keg.png',
            'name1': 'John',
            'name2': 'Steve',
            'name3': 'Kevin Keg'
        }

        self.assertEqual(desired_dict, round.__dict__())

    def test_round_to_dict_correct_is_jayden(self):
        celebs = [Celebrity('John', 'John.png'), Celebrity('Steve', 'Steve.png'),
                  Celebrity('Kevin Keg', 'Kevin Keg.png')]
        round = Round(num=1, celebs=celebs, is_jayden=True, jayden_info=JaydenInfo(stat=Choice.SECOND, username='Jambo', video_id='1234567890a', start_time=60))

        desired_dict = {
            'num': 1,
            'isJayden': True,
            'jaydenStat': Choice.SECOND,
            'jaydenUsername': 'Jambo',
            'jaydenVideoId': '1234567890a',
            'jaydenVideoStartTime': 60,
            'image1': 'John.png',
            'image2': 'Steve.png',
            'image3': 'Kevin Keg.png',
            'name1': 'John',
            'name2': 'Steve',
            'name3': 'Kevin Keg'
        }

        self.assertEqual(desired_dict, round.__dict__())


if __name__ == '__main__':
    unittest.main()
