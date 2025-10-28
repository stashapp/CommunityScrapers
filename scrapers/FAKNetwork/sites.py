# All series fetched from the API on 2025-07-04
# English: https://api.faknetworks.com/v1/series?lang=en&page=1&take=1000
# Spanish: https://api.faknetworks.com/v1/series?lang=es&page=1&take=1000
# Portuguese: https://api.faknetworks.com/v1/series?lang=es&page=1&take=1000

from py_common.util import dig


def to_scraped_studio(api_object: dict, lang="en"):
    studio_id = api_object["id"]
    return dig(studio_map, studio_id, lang, default={"name": "Unknown"})


studio_map = {
    213: {
        "en": {
            "name": "A present for my wife",
            "aliases": ["Un regalo para mi mujer", "Um presente para minha mulher"],
            "url": "https://www.nigged.com/en/serie/a-present-for-my-wf",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
        "es": {
            "name": "Un regalo para mi mujer",
            "aliases": ["Um presente para minha mulher", "A present for my wife"],
            "url": "https://www.nigged.com/es/serie/un-regalo-para-mi-mujer",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
        "pt": {
            "name": "Um presente para minha mulher",
            "aliases": ["Un regalo para mi mujer", "A present for my wife"],
            "url": "https://www.nigged.com/pt/serie/um-presente-para-minha-mulher",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
    },
    214: {
        "en": {
            "name": "Help my mamma",
            "aliases": ["Ayuda a mi madre", "Ajuda a minha mãe"],
            "url": "https://www.nigged.com/en/serie/help-my-mamma",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
        "es": {
            "name": "Ayuda a mi madre",
            "aliases": ["Help my mamma", "Ajuda a minha mãe"],
            "url": "https://www.nigged.com/es/serie/ayuda-a-mi-madre",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
        "pt": {
            "name": "Ajuda a minha mãe",
            "aliases": ["Help my mamma", "Ayuda a mi madre"],
            "url": "https://www.nigged.com/pt/serie/ajuda-a-minha-me",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
    },
    215: {
        "en": {
            "name": "DILF Club",
            "aliases": ["Club Puretas"],
            "url": "https://www.fakings.com/en/serie/dilf-club",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Club Puretas",
            "aliases": ["DILF Club"],
            "url": "https://www.fakings.com/es/serie/club-puretas",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Club Puretas",
            "aliases": ["DILF Club"],
            "url": "https://www.fakings.com/pt/serie/club-puretas",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    216: {
        "en": {
            "name": "My hidden secret",
            "aliases": ["Mi gran secreto"],
            "url": "https://www.nigged.com/en/serie/my-hidden-secret",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
        "es": {
            "name": "Mi gran secreto",
            "aliases": ["My hidden secret"],
            "url": "https://www.nigged.com/es/serie/mi-gran-secreto",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
        "pt": {
            "name": "Mi gran secreto",
            "aliases": ["My hidden secret"],
            "url": "https://www.nigged.com/pt/serie/mi-gran-secreto",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
    },
    217: {
        "en": {
            "name": "Nigged party",
            "aliases": ["Merienda de Negros"],
            "url": "https://www.nigged.com/en/serie/nigged-party",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
        "es": {
            "name": "Merienda de Negros",
            "aliases": ["Nigged party"],
            "url": "https://www.nigged.com/es/serie/merienda-de-negros",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
        "pt": {
            "name": "Merienda de Negros",
            "aliases": ["Nigged party"],
            "url": "https://www.nigged.com/pt/serie/merienda-de-negros",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
    },
    218: {
        "en": {
            "name": "Coffee liqueur",
            "aliases": ["Bombón de licor"],
            "url": "https://www.nigged.com/en/serie/coffee-liqueur",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
        "es": {
            "name": "Bombón de licor",
            "aliases": ["Coffee liqueur"],
            "url": "https://www.nigged.com/es/serie/bombon-de-licor",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
        "pt": {
            "name": "Bombón de licor",
            "aliases": ["Coffee liqueur"],
            "url": "https://www.nigged.com/pt/serie/bombon-de-licor",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
    },
    219: {
        "en": {
            "name": "Oh my nigged",
            "aliases": ["Mira mi negro"],
            "url": "https://www.nigged.com/en/serie/oh-my-nigged",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
        "es": {
            "name": "Mira mi negro",
            "aliases": ["Oh my nigged"],
            "url": "https://www.nigged.com/es/serie/mira-mi-negro",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
        "pt": {
            "name": "Mira mi negro",
            "aliases": ["Oh my nigged"],
            "url": "https://www.nigged.com/pt/serie/mira-mi-negro",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
    },
    220: {
        "en": {
            "name": "The Diary of Apolonia Lapiedra",
            "aliases": ["El Diario de Apolonia Lapiedra"],
            "url": "https://www.pornermates.com/en/serie/el-diario-de-apolonia-lapiedra",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
        "es": {
            "name": "El Diario de Apolonia Lapiedra",
            "aliases": ["The Diary of Apolonia Lapiedra"],
            "url": "https://www.pornermates.com/es/serie/el-diario-de-apolonia-lapiedra",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
        "pt": {
            "name": "El Diario de Apolonia Lapiedra",
            "aliases": ["The Diary of Apolonia Lapiedra"],
            "url": "https://www.pornermates.com/pt/serie/el-diario-de-apolonia-lapiedra",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
    },
    221: {
        "en": {
            "name": "Nacho Vidal: Embedder",
            "aliases": ["Nacho Vidal: Empotrador"],
            "url": "https://www.pornermates.com/en/serie/nacho-vidal-empotrador",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
        "es": {
            "name": "Nacho Vidal: Empotrador",
            "aliases": ["Nacho Vidal: Embedder"],
            "url": "https://www.pornermates.com/es/serie/nacho-vidal-empotrador",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
        "pt": {
            "name": "Nacho Vidal: Empotrador",
            "aliases": ["Nacho Vidal: Embedder"],
            "url": "https://www.pornermates.com/pt/serie/nacho-vidal-empotrador",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
    },
    222: {
        "en": {
            "name": "More than 2 are NOT crowds",
            "aliases": ["Mas de 2 NO son multitud"],
            "url": "https://www.pornermates.com/en/serie/mas-de-2-no-son-multitud",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
        "es": {
            "name": "Mas de 2 NO son multitud",
            "aliases": ["More than 2 are NOT crowds"],
            "url": "https://www.pornermates.com/es/serie/mas-de-2-no-son-multitud",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
        "pt": {
            "name": "Mas de 2 NO son multitud",
            "aliases": ["More than 2 are NOT crowds"],
            "url": "https://www.pornermates.com/pt/serie/mas-de-2-no-son-multitud",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
    },
    223: {
        "en": {
            "name": "They set it up... you just watch",
            "aliases": ["Ellas se lo montan... tu solo miras"],
            "url": "https://www.pornermates.com/en/serie/ellas-se-lo-montan-tu-solo-miras",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
        "es": {
            "name": "Ellas se lo montan... tu solo miras",
            "aliases": ["They set it up... you just watch"],
            "url": "https://www.pornermates.com/es/serie/ellas-se-lo-montan-tu-solo-miras",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
        "pt": {
            "name": "Ellas se lo montan... tu solo miras",
            "aliases": ["They set it up... you just watch"],
            "url": "https://www.pornermates.com/pt/serie/ellas-se-lo-montan-tu-solo-miras",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
    },
    224: {
        "en": {
            "name": "I have a friend who wants to be a Pornstar",
            "aliases": ["Tengo una amiga que quiere ser PornStar"],
            "url": "https://www.pornermates.com/en/serie/tengo-una-amiga-que-quiere-ser-pornstar",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
        "es": {
            "name": "Tengo una amiga que quiere ser PornStar",
            "aliases": ["I have a friend who wants to be a Pornstar"],
            "url": "https://www.pornermates.com/es/serie/tengo-una-amiga-que-quiere-ser-pornstar",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
        "pt": {
            "name": "Tengo una amiga que quiere ser PornStar",
            "aliases": ["I have a friend who wants to be a Pornstar"],
            "url": "https://www.pornermates.com/pt/serie/tengo-una-amiga-que-quiere-ser-pornstar",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
    },
    225: {
        "en": {
            "name": "Destroyers Made in Spain",
            "aliases": [],
            "url": "https://www.pornermates.com/en/serie/destroyers-made-in-spain",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
        "es": {
            "name": "Destroyers Made in Spain",
            "aliases": [],
            "url": "https://www.pornermates.com/es/serie/destroyers-made-in-spain",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
        "pt": {
            "name": "Destroyers Made in Spain",
            "aliases": [],
            "url": "https://www.pornermates.com/pt/serie/destroyers-made-in-spain",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
    },
    226: {
        "en": {
            "name": "DIVAS... They had to be here",
            "aliases": ["DIVAS... Tenían que estar aquí"],
            "url": "https://www.pornermates.com/en/serie/divas-tenian-que-estar-aqui",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
        "es": {
            "name": "DIVAS... Tenían que estar aquí",
            "aliases": ["DIVAS... They had to be here"],
            "url": "https://www.pornermates.com/es/serie/divas-tenian-que-estar-aqui",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
        "pt": {
            "name": "DIVAS... Tenían que estar aquí",
            "aliases": ["DIVAS... They had to be here"],
            "url": "https://www.pornermates.com/pt/serie/divas-tenian-que-estar-aqui",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
    },
    227: {
        "en": {
            "name": "We Are In Love",
            "aliases": ["Estamos In Love"],
            "url": "https://www.pornermates.com/en/serie/estamos-in-love",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
        "es": {
            "name": "Estamos In Love",
            "aliases": ["We Are In Love"],
            "url": "https://www.pornermates.com/es/serie/estamos-in-love",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
        "pt": {
            "name": "Estamos In Love",
            "aliases": ["We Are In Love"],
            "url": "https://www.pornermates.com/pt/serie/estamos-in-love",
            "parent": {"name": "PornerMates", "url": "https://www.pornermates.com"},
        },
    },
    228: {
        "en": {
            "name": "Solidarity porn",
            "aliases": ["Porno solidario"],
            "url": "https://www.nigged.com/en/serie/porno-solidario",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
        "es": {
            "name": "Porno solidario",
            "aliases": ["Solidarity porn"],
            "url": "https://www.nigged.com/es/serie/porno-solidario",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
        "pt": {
            "name": "Porno solidario",
            "aliases": ["Solidarity porn"],
            "url": "https://www.nigged.com/pt/serie/porno-solidario",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
    },
    210: {
        "en": {
            "name": "Blind date",
            "aliases": ["Citas a ciegas", "Encontros às cegas"],
            "url": "https://www.fakings.com/en/serie/blind-date",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Citas a ciegas",
            "aliases": ["Blind date", "Encontros às cegas"],
            "url": "https://www.fakings.com/es/serie/citas-a-ciegas",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Encontros às cegas",
            "aliases": ["Citas a ciegas", "Blind date"],
            "url": "https://www.fakings.com/pt/serie/encontros-s-cegas",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    189: {
        "en": {
            "name": "MadLifes Festivities - 2019",
            "aliases": ["Fiestas MadLifes - 2019"],
            "url": "https://www.madlifes.com/en/serie/fiestas-madlifes-2019",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "es": {
            "name": "Fiestas MadLifes - 2019",
            "aliases": ["MadLifes Festivities - 2019"],
            "url": "https://www.madlifes.com/es/serie/fiestas-madlifes-2019",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "pt": {
            "name": "Fiestas MadLifes - 2019",
            "aliases": ["MadLifes Festivities - 2019"],
            "url": "https://www.madlifes.com/pt/serie/fiestas-madlifes-2019",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
    },
    205: {
        "en": {
            "name": "Fuck my partner",
            "aliases": ["Follate a mi pareja"],
            "url": "https://www.pepeporn.com/en/serie/follate-a-mi-pareja",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "es": {
            "name": "Follate a mi pareja",
            "aliases": ["Fuck my partner"],
            "url": "https://www.pepeporn.com/es/serie/follate-a-mi-pareja",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "pt": {
            "name": "Follate a mi pareja",
            "aliases": ["Fuck my partner"],
            "url": "https://www.pepeporn.com/pt/serie/follate-a-mi-pareja",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
    },
    203: {
        "en": {
            "name": "Recorded at home",
            "aliases": ["Grabado en casa"],
            "url": "https://www.pepeporn.com/en/serie/porno-en-casa",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "es": {
            "name": "Grabado en casa",
            "aliases": ["Recorded at home"],
            "url": "https://www.pepeporn.com/es/serie/porno-en-casa",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "pt": {
            "name": "Grabado en casa",
            "aliases": ["Recorded at home"],
            "url": "https://www.pepeporn.com/pt/serie/porno-en-casa",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
    },
    211: {
        "en": {
            "name": "Girls get nigged",
            "aliases": ["Escurecidos", "Negrateadas"],
            "url": "https://www.nigged.com/en/serie/girls-get-nigged",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
        "es": {
            "name": "Negrateadas",
            "aliases": ["Girls get nigged", "Escurecidos"],
            "url": "https://www.nigged.com/es/serie/negrateadas",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
        "pt": {
            "name": "Escurecidos",
            "aliases": ["Girls get nigged", "Negrateadas"],
            "url": "https://www.nigged.com/pt/serie/escurecidos",
            "parent": {"name": "Nigged", "url": "https://www.nigged.com"},
        },
    },
    197: {
        "en": {
            "name": "Newbies... or so they say ;)",
            "aliases": ["Novatas… ou isso dizem", "Novatas... O eso dicen ;)"],
            "url": "https://www.fakings.com/en/serie/newbies-or-so-they-say-",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Novatas... O eso dicen ;)",
            "aliases": ["Novatas… ou isso dizem", "Newbies... or so they say ;)"],
            "url": "https://www.fakings.com/es/serie/novatas",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Novatas… ou isso dizem",
            "aliases": ["Newbies... or so they say ;)", "Novatas... O eso dicen ;)"],
            "url": "https://www.fakings.com/pt/serie/novatas-ou-isso-dizem",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    206: {
        "en": {
            "name": "I Want to Be a Cuckold",
            "aliases": ["Quiero ser Cornudo"],
            "url": "https://www.pepeporn.com/en/serie/quiero-ser-cornudo",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "es": {
            "name": "Quiero ser Cornudo",
            "aliases": ["I Want to Be a Cuckold"],
            "url": "https://www.pepeporn.com/es/serie/quiero-ser-cornudo",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "pt": {
            "name": "Quiero ser Cornudo",
            "aliases": ["I Want to Be a Cuckold"],
            "url": "https://www.pepeporn.com/pt/serie/quiero-ser-cornudo",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
    },
    201: {
        "en": {
            "name": "Quarantine Stories",
            "aliases": ["Historias de Cuarentena", "Histórias de quarentena"],
            "url": "https://www.fakings.com/en/serie/quarantine-stories",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Historias de Cuarentena",
            "aliases": ["Histórias de quarentena", "Quarantine Stories"],
            "url": "https://www.fakings.com/es/serie/historias-de-cuarentena",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Histórias de quarentena",
            "aliases": ["Historias de Cuarentena", "Quarantine Stories"],
            "url": "https://www.fakings.com/pt/serie/historias-de-quarentena",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    212: {
        "en": {
            "name": "Ivan Amor",
            "aliases": ["Ivan amor"],
            "url": "https://www.fakings.com/en/serie/ivan-amor",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Ivan Amor",
            "aliases": ["Ivan amor"],
            "url": "https://www.fakings.com/es/serie/ivan-amor",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Ivan amor",
            "aliases": ["Ivan Amor"],
            "url": "https://www.fakings.com/pt/serie/ivan-amor",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    200: {
        "en": {
            "name": "Horsedicks",
            "aliases": ["Rabos de Caballo", "Rabo-de-cavalo"],
            "url": "https://www.fakings.com/en/serie/horsedicks",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Rabos de Caballo",
            "aliases": ["Rabo-de-cavalo", "Horsedicks"],
            "url": "https://www.fakings.com/es/serie/rabos-de-caballo",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Rabo-de-cavalo",
            "aliases": ["Horsedicks", "Rabos de Caballo"],
            "url": "https://www.fakings.com/pt/serie/rabo-de-cavalo",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    192: {
        "en": {
            "name": "FREE pussy day",
            "aliases": ["O dia da buceta GRATIS", "El día del coño GRATIS"],
            "url": "https://www.fakings.com/en/serie/free-pussy-day",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "El día del coño GRATIS",
            "aliases": ["FREE pussy day", "O dia da buceta GRATIS"],
            "url": "https://www.fakings.com/es/serie/el-dia-del-cono-gratis",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Odia da buceta GRATIS",
            "aliases": ["FREE pussy day", "El día del coño GRATIS"],
            "url": "https://www.fakings.com/pt/serie/o-dia-da-buceta-gratis",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    199: {
        "en": {
            "name": "Parejas.NET",
            "aliases": [],
            "url": "https://www.fakings.com/en/serie/parejasnet",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Parejas.NET",
            "aliases": [],
            "url": "https://www.fakings.com/es/serie/parejasnet",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Parejas.NET",
            "aliases": [],
            "url": "https://www.fakings.com/pt/serie/parejasnet",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    196: {
        "en": {
            "name": "Curvy Girls",
            "aliases": ["Garotas com curvas", "Chicas Curvis"],
            "url": "https://www.fakings.com/en/serie/curvy-girls",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Chicas Curvis",
            "aliases": ["Curvy Girls", "Garotas com curvas"],
            "url": "https://www.fakings.com/es/serie/chicas-curvis",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Garotas com curvas",
            "aliases": ["Curvy Girls", "Chicas Curvis"],
            "url": "https://www.fakings.com/pt/serie/garotas-com-curvas",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    162: {
        "en": {
            "name": "Next door girl",
            "aliases": ["Es tu vecina", "Ela é sua vizinha"],
            "url": "https://www.fakings.com/en/serie/next-door-girl",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Es tu vecina",
            "aliases": ["Next door girl", "Ela é sua vizinha"],
            "url": "https://www.fakings.com/es/serie/es-tu-vecina",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Ela é sua vizinha",
            "aliases": ["Next door girl", "Es tu vecina"],
            "url": "https://www.fakings.com/pt/serie/ela-e-sua-vizinha",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    182: {
        "en": {
            "name": "MadLifes Festivities - 2018",
            "aliases": ["Fiestas MadLifes - 2018"],
            "url": "https://www.madlifes.com/en/serie/fiestas-madlifes-2018",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "es": {
            "name": "Fiestas MadLifes - 2018",
            "aliases": ["MadLifes Festivities - 2018"],
            "url": "https://www.madlifes.com/es/serie/fiestas-madlifes-2018",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "pt": {
            "name": "Fiestas MadLifes - 2018",
            "aliases": ["MadLifes Festivities - 2018"],
            "url": "https://www.madlifes.com/pt/serie/fiestas-madlifes-2018",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
    },
    135: {
        "en": {
            "name": "2ND TOURNAMENT: 2017",
            "aliases": ["II TORNEO: 2017"],
            "url": "https://www.madlifes.com/en/serie/ii-torneo-2017",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "es": {
            "name": "II TORNEO: 2017",
            "aliases": ["2ND TOURNAMENT: 2017"],
            "url": "https://www.madlifes.com/es/serie/ii-torneo-2017",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "pt": {
            "name": "II TORNEO: 2017",
            "aliases": ["2ND TOURNAMENT: 2017"],
            "url": "https://www.madlifes.com/pt/serie/ii-torneo-2017",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
    },
    132: {
        "en": {
            "name": "1ST TOURNAMENT: 2016",
            "aliases": ["I TORNEO: 2016"],
            "url": "https://www.madlifes.com/en/serie/i-edicion-20152016",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "es": {
            "name": "I TORNEO: 2016",
            "aliases": ["1ST TOURNAMENT: 2016"],
            "url": "https://www.madlifes.com/es/serie/i-edicion-20152016",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "pt": {
            "name": "I TORNEO: 2016",
            "aliases": ["1ST TOURNAMENT: 2016"],
            "url": "https://www.madlifes.com/pt/serie/i-edicion-20152016",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
    },
    179: {
        "en": {
            "name": "VIII MadLifes Party",
            "aliases": ["VIII Fiesta MadLifes"],
            "url": "https://www.madlifes.com/en/serie/viii-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "es": {
            "name": "VIII Fiesta MadLifes",
            "aliases": ["VIII MadLifes Party"],
            "url": "https://www.madlifes.com/es/serie/viii-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "pt": {
            "name": "VIII Fiesta MadLifes",
            "aliases": ["VIII MadLifes Party"],
            "url": "https://www.madlifes.com/pt/serie/viii-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
    },
    208: {
        "en": {
            "name": "The Porno House",
            "aliases": ["La Porno House"],
            "url": "https://www.fakings.com/en/serie/la-porno-house",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "La Porno House",
            "aliases": ["The Porno House"],
            "url": "https://www.fakings.com/es/serie/la-porno-house",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "La Porno House",
            "aliases": ["The Porno House"],
            "url": "https://www.fakings.com/pt/serie/la-porno-house",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    195: {
        "en": {
            "name": "FAKings PornStars",
            "aliases": ["Estrelas pornôs FAKings"],
            "url": "https://www.fakings.com/en/serie/fakings-pornstars",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "FAKings PornStars",
            "aliases": ["Estrelas pornôs FAKings"],
            "url": "https://www.fakings.com/es/serie/fakings-old-stars",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Estrelas pornôs FAKings",
            "aliases": ["FAKings PornStars"],
            "url": "https://www.fakings.com/pt/serie/estrelas-porns-fakings",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    176: {
        "en": {
            "name": "VII MadLifes Party",
            "aliases": ["VII Fiesta MadLifes"],
            "url": "https://www.madlifes.com/en/serie/vii-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "es": {
            "name": "VII Fiesta MadLifes",
            "aliases": ["VII MadLifes Party"],
            "url": "https://www.madlifes.com/es/serie/vii-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "pt": {
            "name": "VII Fiesta MadLifes",
            "aliases": ["VII MadLifes Party"],
            "url": "https://www.madlifes.com/pt/serie/vii-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
    },
    175: {
        "en": {
            "name": "VI MadLifes Party",
            "aliases": ["VI Fiesta MadLifes"],
            "url": "https://www.madlifes.com/en/serie/vi-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "es": {
            "name": "VI Fiesta MadLifes",
            "aliases": ["VI MadLifes Party"],
            "url": "https://www.madlifes.com/es/serie/vi-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "pt": {
            "name": "VI Fiesta MadLifes",
            "aliases": ["VI MadLifes Party"],
            "url": "https://www.madlifes.com/pt/serie/vi-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
    },
    174: {
        "en": {
            "name": "V MadLifes Party",
            "aliases": ["V Fiesta MadLifes"],
            "url": "https://www.madlifes.com/en/serie/v-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "es": {
            "name": "V Fiesta MadLifes",
            "aliases": ["V MadLifes Party"],
            "url": "https://www.madlifes.com/es/serie/v-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "pt": {
            "name": "V Fiesta MadLifes",
            "aliases": ["V MadLifes Party"],
            "url": "https://www.madlifes.com/pt/serie/v-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
    },
    173: {
        "en": {
            "name": "IV MadLifes Party",
            "aliases": ["IV Fiesta MadLifes"],
            "url": "https://www.madlifes.com/en/serie/iv-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "es": {
            "name": "IV Fiesta MadLifes",
            "aliases": ["IV MadLifes Party"],
            "url": "https://www.madlifes.com/es/serie/iv-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "pt": {
            "name": "IV Fiesta MadLifes",
            "aliases": ["IV MadLifes Party"],
            "url": "https://www.madlifes.com/pt/serie/iv-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
    },
    172: {
        "en": {
            "name": "III MadLifes Party",
            "aliases": ["III Fiesta MadLifes"],
            "url": "https://www.madlifes.com/en/serie/iii-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "es": {
            "name": "III Fiesta MadLifes",
            "aliases": ["III MadLifes Party"],
            "url": "https://www.madlifes.com/es/serie/iii-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "pt": {
            "name": "III Fiesta MadLifes",
            "aliases": ["III MadLifes Party"],
            "url": "https://www.madlifes.com/pt/serie/iii-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
    },
    171: {
        "en": {
            "name": "II Madlifes Party",
            "aliases": ["II Fiesta Madlifes"],
            "url": "https://www.madlifes.com/en/serie/ii-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "es": {
            "name": "II Fiesta Madlifes",
            "aliases": ["II Madlifes Party"],
            "url": "https://www.madlifes.com/es/serie/ii-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "pt": {
            "name": "II Fiesta Madlifes",
            "aliases": ["II Madlifes Party"],
            "url": "https://www.madlifes.com/pt/serie/ii-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
    },
    157: {
        "en": {
            "name": "Busted!",
            "aliases": ["Caçadas", "Cazadas"],
            "url": "https://www.fakings.com/en/serie/busted",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Cazadas",
            "aliases": ["Caçadas", "Busted!"],
            "url": "https://www.fakings.com/es/serie/pilladas",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Caçadas",
            "aliases": ["Cazadas", "Busted!"],
            "url": "https://www.fakings.com/pt/serie/cacadas",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    170: {
        "en": {
            "name": "I Fiesta Madlifes",
            "aliases": [],
            "url": "https://www.madlifes.com/en/serie/i-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "es": {
            "name": "I Fiesta Madlifes",
            "aliases": [],
            "url": "https://www.madlifes.com/es/serie/i-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
        "pt": {
            "name": "I Fiesta Madlifes",
            "aliases": [],
            "url": "https://www.madlifes.com/pt/serie/i-fiesta-madlifes",
            "parent": {"name": "MadLifes", "url": "https://www.madlifes.com"},
        },
    },
    109: {
        "en": {
            "name": "Fuck them!",
            "aliases": ["Fuder com eles", "Follatelos"],
            "url": "https://www.fakings.com/en/serie/fuck-them",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Follatelos",
            "aliases": ["Fuder com eles", "Fuck them!"],
            "url": "https://www.fakings.com/es/serie/follatelos",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Fuder com eles",
            "aliases": ["Follatelos", "Fuck them!"],
            "url": "https://www.fakings.com/pt/serie/fuder-com-eles",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    193: {
        "en": {
            "name": "My first anal",
            "aliases": ["Mi primer anal", "Meu primeiro anal"],
            "url": "https://www.fakings.com/en/serie/my-first-anal",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Mi primer anal",
            "aliases": ["My first anal", "Meu primeiro anal"],
            "url": "https://www.fakings.com/es/serie/mi-primer-anal",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Meu primeiro anal",
            "aliases": ["My first anal", "Mi primer anal"],
            "url": "https://www.fakings.com/pt/serie/meu-primeiro-anal",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    112: {
        "en": {
            "name": "MILF Club",
            "aliases": ["Clube de coroas", "Club Maduras"],
            "url": "https://www.fakings.com/en/serie/milf-club",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Club Maduras",
            "aliases": ["MILF Club", "Clube de coroas"],
            "url": "https://www.fakings.com/es/serie/club-maduras",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Clube de coroas",
            "aliases": ["MILF Club", "Club Maduras"],
            "url": "https://www.fakings.com/pt/serie/clube-de-coroas",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    108: {
        "en": {
            "name": "Arnaldo Series",
            "aliases": ["FAKings Series", "Arnaldo séries"],
            "url": "https://www.fakings.com/en/serie/arnaldo-series",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "FAKings Series",
            "aliases": ["Arnaldo Series", "Arnaldo séries"],
            "url": "https://www.fakings.com/es/serie/arnaldo-series",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Arnaldo séries",
            "aliases": ["Arnaldo Series", "FAKings Series"],
            "url": "https://www.fakings.com/pt/serie/arnaldo-series",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    105: {
        "en": {
            "name": "Free Couples",
            "aliases": ["Casais liberais", "Parejitas Libres"],
            "url": "https://www.fakings.com/en/serie/free-couples",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Parejitas Libres",
            "aliases": ["Casais liberais", "Free Couples"],
            "url": "https://www.fakings.com/es/serie/parejitas-libres",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Casais liberais",
            "aliases": ["Parejitas Libres", "Free Couples"],
            "url": "https://www.fakings.com/pt/serie/casais-liberais",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    118: {
        "en": {
            "name": "FAKings Castings",
            "aliases": ["Casting de FAKings", "Castings de FAKings"],
            "url": "https://www.fakings.com/en/serie/fakings-castings",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Castings de FAKings",
            "aliases": ["Casting de FAKings", "FAKings Castings"],
            "url": "https://www.fakings.com/es/serie/castings-de-fakings",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Casting de FAKings",
            "aliases": ["Castings de FAKings", "FAKings Castings"],
            "url": "https://www.fakings.com/pt/serie/casting-de-fakings",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    207: {
        "en": {
            "name": "LoverFans",
            "aliases": ["LiverFans"],
            "url": "https://www.fakings.com/en/serie/loverfans",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "LoverFans",
            "aliases": ["LiverFans"],
            "url": "https://www.fakings.com/es/serie/loverfans",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "LiverFans",
            "aliases": ["LoverFans"],
            "url": "https://www.fakings.com/pt/serie/liverfans",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    159: {
        "en": {
            "name": "First FAKings !!",
            "aliases": ["First FAKings"],
            "url": "https://www.fakings.com/en/serie/first-fakings",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "First FAKings",
            "aliases": ["First FAKings !!"],
            "url": "https://www.fakings.com/es/serie/first-fakings",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "First FAKings",
            "aliases": ["First FAKings !!"],
            "url": "https://www.fakings.com/pt/serie/first-fakings",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    168: {
        "en": {
            "name": "Talk to them",
            "aliases": ["Fale com elas", "Hable con ellas"],
            "url": "https://www.fakings.com/en/serie/talk-to-them",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Hable con ellas",
            "aliases": ["Fale com elas", "Talk to them"],
            "url": "https://www.fakings.com/es/serie/hable-con-ellas",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Fale com elas",
            "aliases": ["Hable con ellas", "Talk to them"],
            "url": "https://www.fakings.com/pt/serie/fale-com-elas",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    119: {
        "en": {
            "name": "I sell my girlfriend.",
            "aliases": ["Vendo minha namorada", "Vendo a mi Novia"],
            "url": "https://www.fakings.com/en/serie/i-sell-my-girlfriend",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Vendo a mi Novia",
            "aliases": ["Vendo minha namorada", "I sell my girlfriend."],
            "url": "https://www.fakings.com/es/serie/vendo-a-mi-novia",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Vendo minha namorada",
            "aliases": ["Vendo a mi Novia", "I sell my girlfriend."],
            "url": "https://www.fakings.com/pt/serie/vendo-minha-namorada",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    163: {
        "en": {
            "name": "NERD BUSTER!",
            "aliases": ["Los Cazatolas", "Os caçadores"],
            "url": "https://www.fakings.com/en/serie/nerd-buster",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Los Cazatolas",
            "aliases": ["NERD BUSTER!", "Os caçadores"],
            "url": "https://www.fakings.com/es/serie/los-cazatolas",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Os caçadores",
            "aliases": ["NERD BUSTER!", "Los Cazatolas"],
            "url": "https://www.fakings.com/pt/serie/os-cacadores",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    110: {
        "en": {
            "name": "Swingers Life:",
            "aliases": ["Vidas Liberales", "Vidas Liberais"],
            "url": "https://www.fakings.com/en/serie/swingers-life",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Vidas Liberales",
            "aliases": ["Swingers Life:", "Vidas Liberais"],
            "url": "https://www.fakings.com/es/serie/vidas-liberales",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Vidas Liberais",
            "aliases": ["Swingers Life:", "Vidas Liberales"],
            "url": "https://www.fakings.com/pt/serie/vidas-liberais",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    187: {
        "en": {
            "name": "Trans FAKings",
            "aliases": [],
            "url": "https://www.fakings.com/en/serie/trans-fakings",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Trans FAKings",
            "aliases": [],
            "url": "https://www.fakings.com/es/serie/trans-fakings",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Trans FAKings",
            "aliases": [],
            "url": "https://www.fakings.com/pt/serie/trans-fakings",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    111: {
        "en": {
            "name": "Very Voyeur",
            "aliases": ["Muito voyeur", "Muy Voyeur"],
            "url": "https://www.fakings.com/en/serie/very-voyeur",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Muy Voyeur",
            "aliases": ["Very Voyeur", "Muito voyeur"],
            "url": "https://www.fakings.com/es/serie/muy-voyeur",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Muito voyeur",
            "aliases": ["Muy Voyeur", "Very Voyeur"],
            "url": "https://www.fakings.com/pt/serie/muito-voyeur",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    120: {
        "en": {
            "name": "FAKings Academy",
            "aliases": ["La escuela de fakings", "A escola de FAKings"],
            "url": "https://www.fakings.com/en/serie/fakings-academy",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "La escuela de fakings",
            "aliases": ["A escola de FAKings", "FAKings Academy"],
            "url": "https://www.fakings.com/es/serie/la-escuela-de-fakings",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "A escola de FAKings",
            "aliases": ["FAKings Academy", "La escuela de fakings"],
            "url": "https://www.fakings.com/pt/serie/a-escola-de-fakings",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    113: {
        "en": {
            "name": "The Naughty Bet",
            "aliases": ["Porno Dolares", "Dólares pornô"],
            "url": "https://www.fakings.com/en/serie/the-naughty-bet",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Porno Dolares",
            "aliases": ["Dólares pornô", "The Naughty Bet"],
            "url": "https://www.fakings.com/es/serie/porno-dolares",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Dólares pornô",
            "aliases": ["The Naughty Bet", "Porno Dolares"],
            "url": "https://www.fakings.com/pt/serie/dolares-porn",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    117: {
        "en": {
            "name": "Ainara's Diary",
            "aliases": ["Diario de Ainara", "Diário de Ainara"],
            "url": "https://www.fakings.com/en/serie/ainaras-diary",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Diario de Ainara",
            "aliases": ["Diário de Ainara", "Ainara's Diary"],
            "url": "https://www.fakings.com/es/serie/diario-de-ainara",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Diário de Ainara",
            "aliases": ["Diario de Ainara", "Ainara's Diary"],
            "url": "https://www.fakings.com/pt/serie/diario-de-ainara",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    116: {
        "en": {
            "name": "FAKins Wild Party",
            "aliases": ["Fiestas FAKings", "Festas FAKings"],
            "url": "https://www.fakings.com/en/serie/fakins-wild-party",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Fiestas FAKings",
            "aliases": ["FAKins Wild Party", "Festas FAKings"],
            "url": "https://www.fakings.com/es/serie/fiestas-fakings",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Festas FAKings",
            "aliases": ["Fiestas FAKings", "FAKins Wild Party"],
            "url": "https://www.fakings.com/pt/serie/festas-fakings",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    115: {
        "en": {
            "name": "My first DP",
            "aliases": ["Minha primeira DP", "Mi primera DP"],
            "url": "https://www.fakings.com/en/serie/my-first-dp",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Mi primera DP",
            "aliases": ["My first DP", "Minha primeira DP"],
            "url": "https://www.fakings.com/es/serie/mi-primera-dp",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Minha primeira DP",
            "aliases": ["Mi primera DP", "My first DP"],
            "url": "https://www.fakings.com/pt/serie/minha-primeira-dp",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    102: {
        "en": {
            "name": "Fuck me, fool!",
            "aliases": ["Me fode, idiota", "Follame Tonto"],
            "url": "https://www.fakings.com/en/serie/fuck-me-fool",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Follame Tonto",
            "aliases": ["Me fode, idiota", "Fuck me, fool!"],
            "url": "https://www.fakings.com/es/serie/follame-tonto",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Me fode, idiota",
            "aliases": ["Follame Tonto", "Fuck me, fool!"],
            "url": "https://www.fakings.com/pt/serie/me-fode-idiota",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    160: {
        "en": {
            "name": "Perverting couples",
            "aliases": ["Casais pervertidos", "Pervirtiendo Parejas"],
            "url": "https://www.fakings.com/en/serie/perverting-couples",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Pervirtiendo Parejas",
            "aliases": ["Casais pervertidos", "Perverting couples"],
            "url": "https://www.fakings.com/es/serie/pervirtiendo-parejas",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Casais pervertidos",
            "aliases": ["Perverting couples", "Pervirtiendo Parejas"],
            "url": "https://www.fakings.com/pt/serie/casais-pervertidos",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    104: {
        "en": {
            "name": "Big Rubber Cocks",
            "aliases": ["Paus de borraxa", "Pollazas de Goma"],
            "url": "https://www.fakings.com/en/serie/big-rubber-cocks",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Pollazas de Goma",
            "aliases": ["Paus de borraxa", "Big Rubber Cocks"],
            "url": "https://www.fakings.com/es/serie/pollazas-de-goma",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Paus de borraxa",
            "aliases": ["Pollazas de Goma", "Big Rubber Cocks"],
            "url": "https://www.fakings.com/pt/serie/paus-de-borraxa",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    106: {
        "en": {
            "name": "Exchange Student Girls",
            "aliases": ["Alumnas De Intercambio", "Alunas de intercâmbio"],
            "url": "https://www.fakings.com/en/serie/exchange-student-girls",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Alumnas De Intercambio",
            "aliases": ["Exchange Student Girls", "Alunas de intercâmbio"],
            "url": "https://www.fakings.com/es/serie/alumnas-de-intercambio",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Alunas de intercâmbio",
            "aliases": ["Exchange Student Girls", "Alumnas De Intercambio"],
            "url": "https://www.fakings.com/pt/serie/alunas-de-intercmbio",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    121: {
        "en": {
            "name": "I'm a Webcam girl.",
            "aliases": ["Soy webcamer", "Sou câmera web"],
            "url": "https://www.fakings.com/en/serie/im-a-webcam-girl",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "es": {
            "name": "Soy webcamer",
            "aliases": ["Sou câmeraweb", "I'm a Webcam girl."],
            "url": "https://www.fakings.com/es/serie/soy-webcamer",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
        "pt": {
            "name": "Sou câmera web",
            "aliases": ["Soy webcamer", "I'm a Webcam girl."],
            "url": "https://www.fakings.com/pt/serie/sou-cmera-web",
            "parent": {"name": "FaKings", "url": "https://www.fakings.com"},
        },
    },
    136: {
        "en": {
            "name": "Our First Porn",
            "aliases": ["Nuestra Primera Porno"],
            "url": "https://www.pepeporn.com/en/serie/nuestra-primera-porno",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "es": {
            "name": "Nuestra Primera Porno",
            "aliases": ["Our First Porn"],
            "url": "https://www.pepeporn.com/es/serie/nuestra-primera-porno",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "pt": {
            "name": "Nuestra Primera Porno",
            "aliases": ["Our First Porn"],
            "url": "https://www.pepeporn.com/pt/serie/nuestra-primera-porno",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
    },
    137: {
        "en": {
            "name": "Am I good for porn?",
            "aliases": ["¿Valgo para el Porno?"],
            "url": "https://www.pepeporn.com/en/serie/valgo-para-el-porno",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "es": {
            "name": "¿Valgo para el Porno?",
            "aliases": ["Am I good for porn?"],
            "url": "https://www.pepeporn.com/es/serie/valgo-para-el-porno",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "pt": {
            "name": "¿Valgo para el Porno?",
            "aliases": ["Am I good for porn?"],
            "url": "https://www.pepeporn.com/pt/serie/valgo-para-el-porno",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
    },
    138: {
        "en": {
            "name": "Fulfilled Fantasies",
            "aliases": ["Fantasias Cumplidas"],
            "url": "https://www.pepeporn.com/en/serie/fantasias-cumplidas",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "es": {
            "name": "Fantasias Cumplidas",
            "aliases": ["Fulfilled Fantasies"],
            "url": "https://www.pepeporn.com/es/serie/fantasias-cumplidas",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "pt": {
            "name": "Fantasias Cumplidas",
            "aliases": ["Fulfilled Fantasies"],
            "url": "https://www.pepeporn.com/pt/serie/fantasias-cumplidas",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
    },
    150: {
        "en": {
            "name": "Las Becerradas de Pepe",
            "aliases": [],
            "url": "https://www.pepeporn.com/en/serie/las-becerradas-de-pepe",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "es": {
            "name": "Las Becerradas de Pepe",
            "aliases": [],
            "url": "https://www.pepeporn.com/es/serie/las-becerradas-de-pepe",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "pt": {
            "name": "Las Becerradas de Pepe",
            "aliases": [],
            "url": "https://www.pepeporn.com/pt/serie/las-becerradas-de-pepe",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
    },
    151: {
        "en": {
            "name": "18 years old",
            "aliases": ["18 añitos"],
            "url": "https://www.pepeporn.com/en/serie/18-anitos",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "es": {
            "name": "18 añitos",
            "aliases": ["18 years old"],
            "url": "https://www.pepeporn.com/es/serie/18-anitos",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "pt": {
            "name": "18 añitos",
            "aliases": ["18 years old"],
            "url": "https://www.pepeporn.com/pt/serie/18-anitos",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
    },
    152: {
        "en": {
            "name": "Jealous couple",
            "aliases": ["Pareja de celosos"],
            "url": "https://www.pepeporn.com/en/serie/pareja-de-celosos",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "es": {
            "name": "Pareja de celosos",
            "aliases": ["Jealous couple"],
            "url": "https://www.pepeporn.com/es/serie/pareja-de-celosos",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "pt": {
            "name": "Pareja de celosos",
            "aliases": ["Jealous couple"],
            "url": "https://www.pepeporn.com/pt/serie/pareja-de-celosos",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
    },
    153: {
        "en": {
            "name": "Maduritos and Maduritas",
            "aliases": ["Maduritos y Maduritas"],
            "url": "https://www.pepeporn.com/en/serie/maduritos-y-maduritas",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "es": {
            "name": "Maduritos y Maduritas",
            "aliases": ["Maduritos and Maduritas"],
            "url": "https://www.pepeporn.com/es/serie/maduritos-y-maduritas",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
        "pt": {
            "name": "Maduritos y Maduritas",
            "aliases": ["Maduritos and Maduritas"],
            "url": "https://www.pepeporn.com/pt/serie/maduritos-y-maduritas",
            "parent": {"name": "PepePorn", "url": "https://www.pepeporn.com"},
        },
    },
}
