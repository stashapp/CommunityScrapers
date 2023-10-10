import unittest

from Algolia import determine_fqdn, determine_studio_name_from_json

params_list = [
    {
        'input': {"serie_name": "21 Erotic Anal", "network_name": "21 Naturals", "mainChannelName": None, "sitename": "21eroticanal", "sitename_pretty": "21eroticanal", 'url': "https://21naturals.com/en/video/21naturals/Sit-On-This/218114"},
        'expected': {'studio': '21 Erotic Anal', 'fqdn': 'www.21naturals.com', 'studio_path': '21eroticanal'}
    },
    {
        'input': {"serie_name": "21FootArt", "network_name": "21 Naturals", "mainChannelName": None, "sitename": "21footart", "sitename_pretty": "21footart", 'url': "https://www.21naturals.com/en/video/21footart/Rock-My-Feet/169915"},
        'expected': {'studio': '21 Foot Art', 'fqdn': 'www.21naturals.com', 'studio_path': '21footart'}
    },
    {
        'input': {"serie_name": "21 Naturals", "network_name": "21 Naturals", "mainChannelName": "21 Naturals", "sitename": "21naturals", "sitename_pretty": "21 Naturals", 'url': "https://www.21naturals.com/en/video/21naturals/Perfection/91278"},
        'expected': {'studio': '21 Naturals', 'fqdn': 'www.21naturals.com', 'studio_path': '21naturals'}
    },
    {
        'input': {"serie_name": "Baby Got Balls", "network_name": "21 Sextreme", "mainChannelName": "Baby Got Balls", "sitename": "babygotballs", "sitename_pretty": "Babygotballs", 'url': "https://www.21sextreme.com/en/video/Alessandra-loves-Suzanna/95533"},
        'expected': {'studio': 'Baby Got Balls', 'fqdn': 'www.21sextreme.com', 'studio_path': 'babygotballs'}
    },
    {
        'input': {"serie_name": "Creampie Reality", "network_name": "21 Sextreme", "mainChannelName": "Creampie Reality", "sitename": "creampiereality", "sitename_pretty": "Creampiereality", 'url': "https://www.21sextreme.com/en/video/21sextreme/Meaty/88323"},
        'expected': {'studio': 'Creampie Reality', 'fqdn': 'www.21sextreme.com', 'studio_path': 'creampiereality'}
    },
    {
        'input': {"serie_name": "Cumming Matures", "network_name": "21 Sextreme", "mainChannelName": "Cumming Matures", "sitename": "cummingmatures", "sitename_pretty": "Cummingmatures", 'url': "https://www.21sextreme.com/en/video/Love-me-youngster/88645"},
        'expected': {'studio': 'Cumming Matures', 'fqdn': 'www.21sextreme.com', 'studio_path': 'cummingmatures'}
    },
    {
        'input': {"serie_name": "Grandpas Fuck Teens", "network_name": "21 Sextreme", "mainChannelName": None, "sitename": "grandpasfuckteens", "sitename_pretty": "Grandpasfuckteens", 'url': "https://21sextreme.com/en/video/The-Simpler-Joys-of-Life/181626"},
        'expected': {'studio': 'Grandpas Fuck Teens', 'fqdn': 'www.21sextreme.com', 'studio_path': 'grandpasfuckteens'}
    },
    {
        'input': {"serie_name": "Home Porn Reality", "network_name": "21 Sextreme", "mainChannelName": "Home Porn Reality", "sitename": "homepornreality", "sitename_pretty": "Homepornreality", 'url': "https://www.21sextreme.com/en/video/Meet-me-in-the-garage/93955"},
        'expected': {'studio': 'Home Porn Reality', 'fqdn': 'www.21sextreme.com', 'studio_path': 'homepornreality'}
    },
    {
        'input': {"serie_name": "Lusty Grandmas", "network_name": "21 Sextreme", "mainChannelName": None, "sitename": "lustygrandmas", "sitename_pretty": "Lustygrandmas", 'url': "https://www.21sextreme.com/en/video/21sextreme/Eager-to-Please/181628"},
        'expected': {'studio': 'Lusty Grandmas', 'fqdn': 'www.21sextreme.com', 'studio_path': 'lustygrandmas'}
    },
    {
        'input': {"serie_name": "Mandy Is Kinky", "network_name": "21 Sextreme", "mainChannelName": "Mandy Is Kinky", "sitename": "mandyiskinky", "sitename_pretty": "Mandyiskinky", 'url': "https://www.21sextreme.com/en/video/Heaven-sent/92346"},
        'expected': {'studio': 'Mandy Is Kinky', 'fqdn': 'www.21sextreme.com', 'studio_path': 'mandyiskinky'}
    },
    {
        'input': {"serie_name": "Mighty Mistress", "network_name": "21 Sextreme", "mainChannelName": "Mighty Mistress", "sitename": "mightymistress", "sitename_pretty": "Mightymistress", 'url': "https://www.21sextreme.com/en/video/Anything-for-Discipline-Part-2/92921"},
        'expected': {'studio': "Mighty Mistress", 'fqdn': 'www.21sextreme.com', 'studio_path': 'mightymistress'}
    },
    {
        'input': {"serie_name": "Old Young Lesbian Love", "network_name": "21 Sextreme", "mainChannelName": None, "sitename": "oldyounglesbianlove", "sitename_pretty": "Oldyounglesbianlove", 'url': "https://21sextreme.com/en/video/The-Subject-of-Her-Desire-Scene-01/183745"},
        'expected': {'studio': "Old Young Lesbian Love", 'fqdn': 'www.21sextreme.com', 'studio_path': 'oldyounglesbianlove'}
    },
    {
        'input': {"serie_name": "Pee And Blow", "network_name": "21 Sextreme", "mainChannelName": None, "sitename": "21sextreme", "sitename_pretty": "21 Sextreme", 'url': "https://www.21sextreme.com/en/video/V-like-Veronika/85126"},
        'expected': {'studio': 'Pee And Blow', 'fqdn': 'www.21sextreme.com', 'studio_path': 'peeandblow'}
    },
    {
        'input': {"serie_name": "Speculum Plays", "network_name": "21 Sextreme", "mainChannelName": "Speculum Plays", "sitename": "speculumplays", "sitename_pretty": "Speculumplays", 'url': "https://www.21sextreme.com/en/video/Private-with-Leanna/85321"},
        'expected': {'studio': "Speculum Plays", 'fqdn': 'www.21sextreme.com', 'studio_path': 'speculumplays'}
    },
    {
        'input': {"serie_name": "Teach Me Fisting", "network_name": "21 Sextreme", "mainChannelName": "Teach Me Fisting", "sitename": "teachmefisting", "sitename_pretty": "Teachmefisting", 'url': "https://www.21sextreme.com/en/video/21sextreme/Two-Petite-Kinky-Blondes/144358"},
        'expected': {'studio': 'Teach Me Fisting', 'fqdn': 'www.21sextreme.com', 'studio_path': 'teachmefisting'}
    },
    {
        'input': {"serie_name": "Tranny From Brazil", "network_name": "21 Sextreme", "mainChannelName": "Tranny From Brazil", "sitename": "transfrombrazil", "sitename_pretty": "Transfrombrazil", "url": "https://www.21sextreme.com/en/video/21sextreme/Looks-are-decieving/93836"},
        'expected': {'studio': 'Tranny From Brazil', 'fqdn': 'www.21sextreme.com', 'studio_path': 'transfrombrazil'}
    },
    {
        'input': {"serie_name": "Tranny Smuts", "network_name": "21 Sextreme", "mainChannelName": "Tranny Smuts", "sitename": "transsmuts", "sitename_pretty": "Transsmuts", "url": "https://www.21sextreme.com/en/video/21sextreme/Luana-the-Pro/97827"},
        'expected': {'studio': 'Tranny Smuts', 'fqdn': 'www.21sextreme.com', 'studio_path': 'transsmuts'}
    },
    {
        'input': {"serie_name": "Zoliboy", "network_name": "21 Sextreme", "mainChannelName": "Zoliboy", "sitename": "zoliboy", "sitename_pretty": "Zoliboy", "url": "https://www.21sextreme.com/en/video/21sextreme/Nuttfill-And-Chill/131801"},
        'expected': {'studio': 'Zoliboy', 'fqdn': 'www.21sextreme.com', 'studio_path': 'zoliboy'}
    },
    {
        'input': {"serie_name": "Solo", "network_name": "21 Sextury", "mainChannelName": None, "sitename": "21sextury", "sitename_pretty": "21 Sextury", "url": "https://www.21sextury.com/en/video/Tina-Kay/148053"},
        'expected': {'studio': '21 Sextury', 'fqdn': 'www.21sextury.com', 'studio_path': '21sextury'}
    },
    {
        'input': {"serie_name": "Aletta Ocean Empire", "network_name": "21 Sextury", "mainChannelName": "Aletta Ocean Empire", "sitename": "alettaoceanempire", "sitename_pretty": "Alettaoceanempire", "url": "https://www.21sextury.com/en/video/21sextury/Treats-for-the-Fan/85811"},
        'expected': {'studio': 'Aletta Ocean Empire', 'fqdn': 'www.21sextury.com', 'studio_path': 'alettaoceanempire'}
    },
    {
        'input': {"serie_name": "Anal Queen Alysa", "network_name": "21 Sextury", "mainChannelName": "Anal Queen Alysa", "sitename": "analqueenalysa", "sitename_pretty": "Analqueenalysa", "url": "https://www.21sextury.com/en/video/In-Need-of-a-Third/96567"},
        'expected': {'studio': 'Anal Queen Alysa', 'fqdn': 'www.21sextury.com', 'studio_path': 'analqueenalysa'}
    },
    {
        'input': {"serie_name": "Anal Teen Angels", "network_name": "21 Sextury", "mainChannelName": None, "sitename": "analteenangels", "sitename_pretty": "Analteenangels", "url": "https://21sextury.com/en/video/21sextury/Treats-to-My-Handyman/181607"},
        'expected': {'studio': 'Anal Teen Angels', 'fqdn': 'www.21sextury.com', 'studio_path': 'analteenangels'}
    },
    {
        'input': {"serie_name": "Asshole fever", "network_name": "21 Sextury", "mainChannelName": None, "sitename": "assholefever", "sitename_pretty": "Assholefever", "url": "https://21sextury.com/en/video/21sextury/Buttfuck-Fanatic/231740"},
        'expected': {'studio': 'Asshole Fever', 'fqdn': 'www.21sextury.com', 'studio_path': 'assholefever'}
    },
    {
        'input': {"serie_name": "Blue Angel Live", "network_name": "21 Sextury", "mainChannelName": "Blue Angel Live", "sitename": "blueangellive", "sitename_pretty": "Blueangellive", "url": "https://www.21sextury.com/en/video/NudeFightClub-backstage-with-Blue-Angel-and-Ruth-Medina/93096"},
        'expected': {'studio': 'Blue Angel Live', 'fqdn': 'www.21sextury.com', 'studio_path': 'blueangellive'}
    },
    {
        'input': {"serie_name": "Butt Plays", "network_name": "21 Sextury", "mainChannelName": None, "sitename": "dpfanatics", "sitename_pretty": "Dpfanatics", "url": "https://www.21sextury.com/en/video/Her-Special-Guests-/167551"},
        'expected': {'studio': 'Butt Plays', 'fqdn': 'www.21sextury.com', 'studio_path': 'dpfanatics'}
    },
    {
        'input': {"serie_name": "Cheating Whore Wives", "network_name": "21 Sextury", "mainChannelName": "Cheating Whore Wives", "sitename": "cheatingwhorewives", "sitename_pretty": "Cheatingwhorewives", "url": "https://www.21sextury.com/en/video/21sextury/Being-bored/83248"},
        'expected': {'studio': 'Cheating Whore Wives', 'fqdn': 'www.21sextury.com', 'studio_path': 'cheatingwhorewives'}
    },
    {
        'input': {"serie_name": "Club Sandy", "network_name": "21 Sextury", "mainChannelName": "Club Sandy", "sitename": "clubsandy", "sitename_pretty": "Clubsandy", "url": "https://www.21sextury.com/en/video/Relieve-My-Stress/131480"},
        'expected': {'studio': 'Club Sandy', 'fqdn': 'www.21sextury.com', 'studio_path': 'clubsandy'}
    },
    {
        'input': {"serie_name": "Cuties Galore", "network_name": "21 Sextury", "mainChannelName": "Cuties Galore", "sitename": "cutiesgalore", "sitename_pretty": "Cutiesgalore", "url": "https://www.21sextury.com/en/video/cutiesgalore/CutiesGalore-presents-Sasha/95928"},
        'expected': {'studio': 'Cuties Galore', 'fqdn': 'www.21sextury.com', 'studio_path': 'cutiesgalore'}
    },
    {
        'input': {"serie_name": "Deepthroat Frenzy", "network_name": "21 Sextury", "mainChannelName": "DP Fanatics", "sitename": "dpfanatics", "sitename_pretty": "Dpfanatics", "url": "https://www.21sextury.com/en/video/cutiesgalore/CutiesGalore-presents-Sasha/95928"},
        'expected': {'studio': 'Deepthroat Frenzy', 'fqdn': 'www.21sextury.com', 'studio_path': 'dpfanatics'}
    },
    {
        'input': {"serie_name": "DPFanatics", "network_name": "21 Sextury", "mainChannelName": None, "sitename": "dpfanatics", "sitename_pretty": "Dpfanatics", "url": "https://dpfanatics.com/en/video/dpfanatics/Shes-Not-Camera-Shy/229951"},
        'expected': {'studio': 'DP Fanatics', 'fqdn': 'www.21sextury.com', 'studio_path': 'cutiesgalore'}
    },
    {
        'input': {"serie_name": "Footsie Babes", "network_name": "21 Sextury", "mainChannelName": None, "sitename": "footsiebabes", "sitename_pretty": "Footsiebabes", "url": "https://21sextury.com/en/video/21sextury/Those-Amusing-Toes/209850"},
        'expected': {'studio': 'Footsie Babes', 'fqdn': 'www.21sextury.com', 'studio_path': 'footsiebabes'}
    },
    {
        'input': {"serie_name": "Gapeland", "network_name": "21 Sextury", "mainChannelName": "Gapeland", "sitename": "gapeland", "sitename_pretty": "Gapeland", "url": "https://www.21sextury.com/en/video/Having-A-Teen-Girlfriend/144354"},
        'expected': {'studio': 'Gapeland', 'fqdn': 'www.21sextury.com', 'studio_path': 'gapeland'}
    },
    {
        'input': {"serie_name": "Gapeland", "network_name": "21 Sextury", "mainChannelName": "Gapeland", "sitename": "gapeland", "sitename_pretty": "Gapeland", "url": "https://www.21sextury.com/en/video/Having-A-Teen-Girlfriend/144354"},
        'expected': {'studio': 'Gapeland', 'fqdn': 'www.21sextury.com', 'studio_path': 'gapeland'}
    },
    {
        'input': {"serie_name": "Hot Milf Club", "network_name": "21 Sextury", "mainChannelName": "Hot Milf Club", "sitename": "hotmilfclub", "sitename_pretty": "Hotmilfclub", "url": "https://www.21sextury.com/en/video/Hot-MILF-Vivian/95534"},
        'expected': {'studio': 'Hot Milf Club', 'fqdn': 'www.21sextury.com', 'studio_path': 'hotmilfclub'}
    },
    {
        'input': {"serie_name": "Lets Play Lez", "network_name": "21 Sextury", "mainChannelName": "Lets Play Lez", "sitename": "letsplaylez", "sitename_pretty": "Letsplaylez", "url": "https://www.21sextury.com/en/video/Wild-plays-with-Maryel-and-Kendra-Star/97475"},
        'expected': {'studio': 'Lets Play Lez', 'fqdn': 'www.21sextury.com', 'studio_path': 'letsplaylez'}
    },
    {
        'input': {"serie_name": "Lezcuties", "network_name": "21 Sextury", "mainChannelName": None, "sitename": "lezcuties", "sitename_pretty": "Lezcuties", "url": "https://21sextury.com/en/video/lezcuties/Glam-Up-Dress-Down/207262"},
        'expected': {'studio': 'Lez Cuties', 'fqdn': 'www.21sextury.com', 'studio_path': 'lezcuties'}
    },
    {
        'input': {"serie_name": "Nude Fight Club", "network_name": "21 Sextury", "mainChannelName": "Nude Fight Club", "sitename": "nudefightclub", "sitename_pretty": "Nudefightclub", "url": "https://www.21sextury.com/en/video/Favourite-Matches/93035"},
        'expected': {'studio': 'Nude Fight Club', 'fqdn': 'www.21sextury.com', 'studio_path': 'nudefightclub'}
    },
    {
        'input': {"serie_name": "Only Swallows", "network_name": "21 Sextury", "mainChannelName": "Only Swallows", "sitename": "onlyswallows", "sitename_pretty": "Onlyswallows", "url": "https://www.21sextury.com/en/video/Come-in-Kami/84238"},
        'expected': {'studio': 'Only Swallows', 'fqdn': 'www.21sextury.com', 'studio_path': 'onlyswallows'}
    },
    {
        'input': {"serie_name": "Pix and Video", "network_name": "21 Sextury", "mainChannelName": None, "sitename": "pixandvideo", "sitename_pretty": "Pixandvideo", "url": "https://www.21sextury.com/en/video/Summertime-Love/170402"},
        'expected': {'studio': 'Pix and Video', 'fqdn': 'www.21sextury.com', 'studio_path': 'pixandvideo'}
    },
    {
        'input': {"serie_name": "Sex With Kathia Nobili", "network_name": "21 Sextury", "mainChannelName": "Sex With Kathia Nobili", "sitename": "sexwithkathianobili", "sitename_pretty": "Sexwithkathianobili", "url": "https://www.21sextury.com/en/video/Brothel-Tour/92914"},
        'expected': {'studio': 'Sex With Kathia Nobili', 'fqdn': 'www.21sextury.com', 'studio_path': 'sexwithkathianobili'}
    },
    {
        'input': {"serie_name": "Sweet Sophie Moone", "network_name": "21 Sextury", "mainChannelName": "Sweet Sophie Moone", "sitename": "sweetsophiemoone", "sitename_pretty": "Sweetsophiemoone", "url": "https://www.21sextury.com/en/video/Brothel-Tour/92914"},
        'expected': {'studio': 'Sweet Sophie Moone', 'fqdn': 'www.21sextury.com', 'studio_path': 'sweetsophiemoone'}
    },
    {
        'input': {"serie_name": "Active Duty", "network_name": "asgmax", "mainChannelName": None, "sitename": "activeduty", "sitename_pretty": "ActiveDuty.com", "url": "https://www.activeduty.com/en/video/activeduty/Damien-Dominates-Private-Evans/228706"},
        'expected': {'studio': 'Active Duty', 'fqdn': 'www.activeduty.com', 'studio_path': 'activeduty'}
    },
    {
        'input': {"serie_name": "Active Duty", "network_name": "asgmax", "mainChannelName": None, "sitename": "activeduty", "sitename_pretty": "ActiveDuty.com", "url": "https://www.activeduty.com/en/video/activeduty/Damien-Dominates-Private-Evans/228706"},
        'expected': {'studio': 'Active Duty', 'fqdn': 'www.activeduty.com', 'studio_path': 'activeduty'}
    },
    {
        'input': {"serie_name": "Yoga Girls", "network_name": "Zero Tolerance Films", "mainChannelName": None, "sitename": "addicted2girls", "sitename_pretty": "Addicted2Girls", "url": "https://www.addicted2girls.com/en/video/addicted2girls/Yoga-Girls-5---Scene-4/209414"},
        'expected': {'studio': 'Addicted 2 Girls', 'fqdn': 'www.addicted2girls.com', 'studio_path': 'addicted2girls'}
    },
    {
        'input': {"serie_name": "Accidental Gangbang", "network_name": "Adult Time Originals", "mainChannelName": None, "sitename": "accidentalgangbang", "sitename_pretty": "Accidentalgangbang", "url": "https://accidentalgangbang.com/en/video/accidentalgangbang/In-Laws-In-Need/216290"},
        'expected': {'studio': 'Accidental Gangbang', 'fqdn': 'www.accidentalgangbang.com', 'studio_path': 'accidentalgangbang'}
    },
    {
        'input': {"serie_name": "Feed Me", "network_name": "Adult Time Originals", "mainChannelName": None, "sitename": "feedme", "sitename_pretty": "Feedme", "url": "https://members.adulttime.com/en/video/feedme/Feed-Me---Episode-1/230853"},
        'expected': {'studio': 'Adult Time Originals', 'fqdn': 'members.adulttime.com', 'studio_path': 'feedme'}
    },
    {
        'input': {"serie_name": "Sweet Sweet Sally Mae", "network_name": "Adult Time Films", "mainChannelName": None, "sitename": "adulttime", "sitename_pretty": "Adult Time", "url": "https://adulttime.com/en/video/adulttime/Sally-Mae-The-Revenge-of-the-Twin-Dragons-Part-1/207741"},
        'expected': {'studio': 'Adult Time Films', 'fqdn': 'members.adulttime.com', 'studio_path': 'adulttime'}
    },
    {
        'input': {"serie_name": "Family Siblings", "network_name": "Adult Time Originals", "mainChannelName": None, "sitename": "AdultTimePilots", "sitename_pretty": "AdultTimePilots", "url": "https://adulttimepilots.com/en/video/adulttimepilots/The-Stepsisterhood-Of-Unraveling-Pants/215293"},
        'expected': {'studio': 'Family Siblings', 'fqdn': 'members.adulttime.com', 'studio_path': 'adulttimepilots'}
    },
    {
        'input': {"serie_name": "Jerk Buddies", "network_name": "Adult Time Originals", "mainChannelName": None, "sitename": "jerkbuddies", "sitename_pretty": "Jerkbuddies", "url": "https://www.heteroflexible.com/en/video/jerkbuddies/Get-Outta-Here-Dude-This-Rooms-Taken/218599"},
        'expected': {'studio': 'HeteroFlexible', 'fqdn': 'www.heteroflexible.com', 'studio_path': 'jerkbuddies'}
    },
    {
        'input': {"serie_name": "IsThisReal", "network_name": "Is This Real", "mainChannelName": None, "sitename": "isthisreal", "sitename_pretty": "Isthisreal", "url": "https://www.isthisreal.com/en/video/isthisreal/Fucked-Up-Therapy-Sessions/169739"},
        'expected': {'studio': 'Is This Real?!', 'fqdn': 'www.isthisreal.com', 'studio_path': 'isthisreal'}
    },
    {
        'input': {"serie_name": "Joymii", "network_name": "Joymii", "mainChannelName": None, "sitename": "joymii", "sitename_pretty": "Joymii", "url": "https://joymii.com/en/video/joymii/Dinner/227922"},
        'expected': {'studio': 'Joymii', 'fqdn': 'www.joymii.com', 'studio_path': 'joymii'}
    },
    {
        'input': {"serie_name": "Modern-Day Sins", "network_name": "ModernDaySins", "mainChannelName": None, "sitename": "moderndaysins", "sitename_pretty": "ModernDaySins", "url": "https://www.moderndaysins.com/en/video/moderndaysins/Tit-For-Tat/230413"},
        'expected': {'studio': 'Modern-Day Sins', 'fqdn': 'www.moderndaysins.com', 'studio_path': 'moderndaysins'}
    }
]

class TestAlgolia(unittest.TestCase):
    def test_determine_studio_name_from_json(self):
        """
        Test the correct studio is determined
        """
        for params in params_list:
            with self.subTest(params):
                studio = determine_studio_name_from_json(params['input'])

                self.assertEqual(studio, params['expected']['studio'])

    def test_determine_fqdn(self):
        """
        Test the correct FQDN is determined
        """
        for params in params_list:
            with self.subTest(params):
                fqdn = determine_fqdn(params['input']['sitename'], params['input']['network_name'])

                self.assertEqual(fqdn, params['expected']['fqdn'])
