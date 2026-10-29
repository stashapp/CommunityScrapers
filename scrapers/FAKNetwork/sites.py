# All series fetched from the API on 2026-10-03
# https://api.faknetworks.com/v1/series?lang=<en|es|pt>&page=1&take=1000

from typing import cast

from py_common.types import ScrapedStudio
from py_common.util import dig


def to_scraped_studio(
    api_object: dict, product: str, lang: str = "en"
) -> ScrapedStudio:
    slug = api_object["slug"]
    # A series newer than this table: its name is known, its network isn't
    unknown: ScrapedStudio = {"name": api_object["title"]}

    series_id = dig(slug_index, product, slug)
    if series_id is None:
        return unknown

    studio = dig(studio_map, series_id, lang, default=unknown)
    return cast(ScrapedStudio, {key: value for key, value in studio.items() if value})


slug_index = {
    "fakings": {
        "fuck-me-fool": 102,
        "follame-tonto": 102,
        "me-fode-idiota": 102,
        "big-rubber-cocks": 104,
        "pollazas-de-goma": 104,
        "paus-de-borraxa": 104,
        "free-couples": 105,
        "parejitas-libres": 105,
        "casais-liberais": 105,
        "exchange-student-girls": 106,
        "alumnas-de-intercambio": 106,
        "alunas-de-intercmbio": 106,
        "fakings-series": 108,
        "serie-fakings": 108,
        "fuck-them": 109,
        "follatelos": 109,
        "fuder-com-eles": 109,
        "swingers-life": 110,
        "vidas-liberales": 110,
        "vidas-liberais": 110,
        "very-voyeur": 111,
        "muy-voyeur": 111,
        "muito-voyeur": 111,
        "milf-club": 112,
        "club-maduras": 112,
        "clube-de-coroas": 112,
        "the-naughty-bet": 113,
        "porno-dolares": 113,
        "dolares-porn": 113,
        "my-first-dp": 115,
        "mi-primera-dp": 115,
        "minha-primeira-dp": 115,
        "fakins-wild-party": 116,
        "fiestas-fakings": 116,
        "festas-fakings": 116,
        "ainaras-diary": 117,
        "diario-de-ainara": 117,
        "fakings-castings": 118,
        "castings-de-fakings": 118,
        "casting-de-fakings": 118,
        "i-sell-my-girlfriend": 119,
        "vendo-a-mi-novia": 119,
        "vendo-minha-namorada": 119,
        "fakings-academy": 120,
        "la-escuela-de-fakings": 120,
        "a-escola-de-fakings": 120,
        "im-a-webcam-girl": 121,
        "soy-webcamer": 121,
        "sou-cmera-web": 121,
        "busted": 157,
        "pilladas": 157,
        "cacadas": 157,
        "first-fakings": 159,
        "perverting-couples": 160,
        "pervirtiendo-parejas": 160,
        "casais-pervertidos": 160,
        "next-door-girl": 162,
        "es-tu-vecina": 162,
        "ela-e-sua-vizinha": 162,
        "nerd-buster": 163,
        "los-cazatolas": 163,
        "os-cacadores": 163,
        "talk-to-them": 168,
        "hable-con-ellas": 168,
        "fale-com-elas": 168,
        "trans-fakings": 187,
        "free-pussy-day": 192,
        "el-dia-del-cono-gratis": 192,
        "o-dia-da-buceta-gratis": 192,
        "my-first-anal": 193,
        "mi-primer-anal": 193,
        "meu-primeiro-anal": 193,
        "fakings-pornstars": 195,
        "fakings-old-stars": 195,
        "estrelas-porns-fakings": 195,
        "curvy-girls": 196,
        "chicas-curvis": 196,
        "garotas-com-curvas": 196,
        "newbies-or-so-they-say-": 197,
        "novatas": 197,
        "novatas-ou-isso-dizem": 197,
        "parejasnet": 199,
        "elephant-tails": 200,
        "rabos-de-caballo": 200,
        "rabos-de-elefante": 200,
        "quarantine-stories": 201,
        "historias-de-cuarentena": 201,
        "historias-de-quarentena": 201,
        "loverfans": 207,
        "liverfans": 207,
        "la-porno-house": 208,
        "blind-date": 210,
        "citas-a-ciegas": 210,
        "encontros-s-cegas": 210,
        "ivan-amor": 212,
        "dilf-club": 215,
        "club-puretas": 215,
    },
    "madlifes": {
        "i-edicion-20152016": 132,
        "ii-torneo-2017": 135,
        "i-fiesta-madlifes": 170,
        "ii-fiesta-madlifes": 171,
        "iii-fiesta-madlifes": 172,
        "iv-fiesta-madlifes": 173,
        "v-fiesta-madlifes": 174,
        "vi-fiesta-madlifes": 175,
        "vii-fiesta-madlifes": 176,
        "viii-fiesta-madlifes": 179,
        "fiestas-madlifes-2018": 182,
        "fiestas-madlifes-2019": 189,
    },
    "pepeporn": {
        "nuestra-primera-porno": 136,
        "valgo-para-el-porno": 137,
        "fantasias-cumplidas": 138,
        "amor-propio": 139,
        "las-becerradas-de-pepe": 150,
        "18-anitos": 151,
        "pareja-de-celosos": 152,
        "maduritos-y-maduritas": 153,
        "porno-en-casa": 203,
        "follate-a-mi-pareja": 205,
        "quiero-ser-cornudo": 206,
    },
    "madgays": {
        "i-reality-madgays": 177,
        "heteropajas": 178,
        "telepillados": 180,
        "polvazos-actores-consagrados": 183,
        "ii-reality": 184,
        "amigos-de-martin-mazza": 185,
        "enclavegay-2018": 186,
        "my-first-casting": 188,
        "mi-primer-casting": 188,
        "meu-primeiro-casting": 188,
        "hotgay-2019": 190,
        "gaypaja": 191,
        "enclavegay-2019": 198,
    },
    "loverfans": {
        "loverfans": 202,
    },
    "nigged": {
        "girls-get-nigged": 211,
        "negrateadas": 211,
        "escurecidos": 211,
        "a-present-for-my-wf": 213,
        "un-regalo-para-mi-mujer": 213,
        "um-presente-para-minha-mulher": 213,
        "help-my-mamma": 214,
        "ayuda-a-mi-madre": 214,
        "ajuda-a-minha-me": 214,
        "my-hidden-secret": 216,
        "mi-gran-secreto": 216,
        "nigged-party": 217,
        "merienda-de-negros": 217,
        "coffee-bonbon": 218,
        "bombon-de-licor": 218,
        "bombom-de-cafe": 218,
        "oh-my-nigged": 219,
        "mira-mi-negro": 219,
        "porno-solidario": 228,
    },
    "pornermates": {
        "el-diario-de-apolonia-lapiedra": 220,
        "nacho-vidal-empotrador": 221,
        "mas-de-2-no-son-multitud": 222,
        "ellas-se-lo-montan-tu-solo-miras": 223,
        "tengo-una-amiga-que-quiere-ser-pornstar": 224,
        "destroyers-made-in-spain": 225,
        "divas-tenian-que-estar-aqui": 226,
        "estamos-in-love": 227,
    },
    "morenolust": {
        "ninisex": 229,
        "parodies": 230,
        "parodias": 230,
        "immature-shenanigans": 231,
        "travesuras-inmaduras": 231,
        "convenios-imaturos": 231,
        "back-after-behind": 232,
        "tras-tras-por-detras": 232,
        "volta-atras-atras": 232,
        "dating-young-girls": 233,
        "citas-jovencitas": 233,
        "namorar-raparigas": 233,
        "the-tough-ones-and-the-mature-ones": 234,
        "las-duras-y-las-maduras": 234,
        "os-duroes-e-os-maduros": 234,
        "mermaids-on-earth-trans": 235,
        "sirenas-en-tierra-trans": 235,
        "sereias-na-terra-trans": 235,
        "brown-sugar-with-cane-interracial": 236,
        "azucar-moreno-con-cana-interracial": 236,
        "acucar-mascavo-com-cana-interracial": 236,
        "hot-tourism": 237,
        "turismo-hot": 237,
        "turismo-quente": 237,
        "group-and-exchanges": 238,
        "grupal-e-intercambios": 238,
        "em-grupo-e-intercambios": 238,
        "country-style-skewer": 239,
        "pinchito-campestre": 239,
        "espetinho-campestre": 239,
        "caught-and-castings": 240,
        "pilladas-y-castings": 240,
        "apanhadas-e-castings": 240,
        "hotties": 241,
        "jacas": 241,
        "pibones": 241,
        "xxl": 242,
        "xxg": 242,
        "fetishes": 244,
        "fetiches": 244,
        "couples": 245,
        "parejas": 245,
        "casais": 245,
    },
    "roccovids": {
        "orgies-and-gangbangs": 247,
        "orgias-y-gangbangs": 247,
        "orgias-e-gangbangs": 247,
        "rocco-lesbians": 248,
        "rocco-lesbicos": 248,
        "rocco-anal": 249,
        "rocco-vip": 250,
        "bbc-big-black-cock": 251,
        "bbc-grande-galo-preto": 251,
        "bts-behind-the-camera": 252,
        "bts-detras-de-camara": 252,
        "bts-atras-da-camera": 252,
    },
}


studio_map: dict[int, dict[str, ScrapedStudio]] = {
    102: {
        "en": {
            "name": "Fuck me, fool!",
            "aliases": "Follame Tonto, Me fode, idiota",
            "urls": ["https://www.fakings.com/en/serie/fuck-me-fool"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Follame Tonto",
            "aliases": "Fuck me, fool!, Me fode, idiota",
            "urls": ["https://www.fakings.com/es/serie/follame-tonto"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Me fode, idiota",
            "aliases": "Fuck me, fool!, Follame Tonto",
            "urls": ["https://www.fakings.com/pt/serie/me-fode-idiota"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    104: {
        "en": {
            "name": "Big Rubber Cocks",
            "aliases": "Pollazas de Goma, Paus de borraxa",
            "urls": ["https://www.fakings.com/en/serie/big-rubber-cocks"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Pollazas de Goma",
            "aliases": "Big Rubber Cocks, Paus de borraxa",
            "urls": ["https://www.fakings.com/es/serie/pollazas-de-goma"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Paus de borraxa",
            "aliases": "Big Rubber Cocks, Pollazas de Goma",
            "urls": ["https://www.fakings.com/pt/serie/paus-de-borraxa"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    105: {
        "en": {
            "name": "Free Couples",
            "aliases": "Parejitas Libres, Casais liberais",
            "urls": ["https://www.fakings.com/en/serie/free-couples"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Parejitas Libres",
            "aliases": "Free Couples, Casais liberais",
            "urls": ["https://www.fakings.com/es/serie/parejitas-libres"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Casais liberais",
            "aliases": "Free Couples, Parejitas Libres",
            "urls": ["https://www.fakings.com/pt/serie/casais-liberais"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    106: {
        "en": {
            "name": "Exchange Student Girls",
            "aliases": "Alumnas De Intercambio, Alunas de intercâmbio",
            "urls": ["https://www.fakings.com/en/serie/exchange-student-girls"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Alumnas De Intercambio",
            "aliases": "Exchange Student Girls, Alunas de intercâmbio",
            "urls": ["https://www.fakings.com/es/serie/alumnas-de-intercambio"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Alunas de intercâmbio",
            "aliases": "Exchange Student Girls, Alumnas De Intercambio",
            "urls": ["https://www.fakings.com/pt/serie/alunas-de-intercmbio"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    108: {
        "en": {
            "name": "FAKings Series",
            "aliases": "Serie FAKings, Série FAKings",
            "urls": ["https://www.fakings.com/en/serie/fakings-series"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Serie FAKings",
            "aliases": "FAKings Series, Série FAKings",
            "urls": ["https://www.fakings.com/es/serie/fakings-series"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Série FAKings",
            "aliases": "FAKings Series, Serie FAKings",
            "urls": ["https://www.fakings.com/pt/serie/serie-fakings"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    109: {
        "en": {
            "name": "Fuck them!",
            "aliases": "Follatelos, Fuder com eles",
            "urls": ["https://www.fakings.com/en/serie/fuck-them"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Follatelos",
            "aliases": "Fuck them!, Fuder com eles",
            "urls": ["https://www.fakings.com/es/serie/follatelos"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Fuder com eles",
            "aliases": "Fuck them!, Follatelos",
            "urls": ["https://www.fakings.com/pt/serie/fuder-com-eles"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    110: {
        "en": {
            "name": "Swingers Life:",
            "aliases": "Vidas Liberales, Vidas Liberais",
            "urls": ["https://www.fakings.com/en/serie/swingers-life"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Vidas Liberales",
            "aliases": "Swingers Life:, Vidas Liberais",
            "urls": ["https://www.fakings.com/es/serie/vidas-liberales"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Vidas Liberais",
            "aliases": "Swingers Life:, Vidas Liberales",
            "urls": ["https://www.fakings.com/pt/serie/vidas-liberais"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    111: {
        "en": {
            "name": "Very Voyeur",
            "aliases": "Muy Voyeur, Muito voyeur",
            "urls": ["https://www.fakings.com/en/serie/very-voyeur"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Muy Voyeur",
            "aliases": "Very Voyeur, Muito voyeur",
            "urls": ["https://www.fakings.com/es/serie/muy-voyeur"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Muito voyeur",
            "aliases": "Very Voyeur, Muy Voyeur",
            "urls": ["https://www.fakings.com/pt/serie/muito-voyeur"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    112: {
        "en": {
            "name": "MILF Club",
            "aliases": "Club Maduras, Clube de coroas",
            "urls": ["https://www.fakings.com/en/serie/milf-club"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Club Maduras",
            "aliases": "MILF Club, Clube de coroas",
            "urls": ["https://www.fakings.com/es/serie/club-maduras"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Clube de coroas",
            "aliases": "MILF Club, Club Maduras",
            "urls": ["https://www.fakings.com/pt/serie/clube-de-coroas"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    113: {
        "en": {
            "name": "The Naughty Bet",
            "aliases": "Porno Dolares, Dólares pornô",
            "urls": ["https://www.fakings.com/en/serie/the-naughty-bet"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Porno Dolares",
            "aliases": "The Naughty Bet, Dólares pornô",
            "urls": ["https://www.fakings.com/es/serie/porno-dolares"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Dólares pornô",
            "aliases": "The Naughty Bet, Porno Dolares",
            "urls": ["https://www.fakings.com/pt/serie/dolares-porn"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    115: {
        "en": {
            "name": "My first DP",
            "aliases": "Mi primera DP, Minha primeira DP",
            "urls": ["https://www.fakings.com/en/serie/my-first-dp"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Mi primera DP",
            "aliases": "My first DP, Minha primeira DP",
            "urls": ["https://www.fakings.com/es/serie/mi-primera-dp"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Minha primeira DP",
            "aliases": "My first DP, Mi primera DP",
            "urls": ["https://www.fakings.com/pt/serie/minha-primeira-dp"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    116: {
        "en": {
            "name": "FAKins Wild Party",
            "aliases": "Fiestas FAKings, Festas FAKings",
            "urls": ["https://www.fakings.com/en/serie/fakins-wild-party"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Fiestas FAKings",
            "aliases": "FAKins Wild Party, Festas FAKings",
            "urls": ["https://www.fakings.com/es/serie/fiestas-fakings"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Festas FAKings",
            "aliases": "FAKins Wild Party, Fiestas FAKings",
            "urls": ["https://www.fakings.com/pt/serie/festas-fakings"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    117: {
        "en": {
            "name": "Ainara's Diary",
            "aliases": "Diario de Ainara, Diário de Ainara",
            "urls": ["https://www.fakings.com/en/serie/ainaras-diary"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Diario de Ainara",
            "aliases": "Ainara's Diary, Diário de Ainara",
            "urls": ["https://www.fakings.com/es/serie/diario-de-ainara"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Diário de Ainara",
            "aliases": "Ainara's Diary, Diario de Ainara",
            "urls": ["https://www.fakings.com/pt/serie/diario-de-ainara"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    118: {
        "en": {
            "name": "FAKings Castings",
            "aliases": "Castings de FAKings, Casting de FAKings",
            "urls": ["https://www.fakings.com/en/serie/fakings-castings"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Castings de FAKings",
            "aliases": "FAKings Castings, Casting de FAKings",
            "urls": ["https://www.fakings.com/es/serie/castings-de-fakings"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Casting de FAKings",
            "aliases": "FAKings Castings, Castings de FAKings",
            "urls": ["https://www.fakings.com/pt/serie/casting-de-fakings"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    119: {
        "en": {
            "name": "I sell my girlfriend",
            "aliases": "Vendo a mi Novia, Vendo minha namorada",
            "urls": ["https://www.fakings.com/en/serie/i-sell-my-girlfriend"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Vendo a mi Novia",
            "aliases": "I sell my girlfriend, Vendo minha namorada",
            "urls": ["https://www.fakings.com/es/serie/vendo-a-mi-novia"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Vendo minha namorada",
            "aliases": "I sell my girlfriend, Vendo a mi Novia",
            "urls": ["https://www.fakings.com/pt/serie/vendo-minha-namorada"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    120: {
        "en": {
            "name": "FAKings Academy",
            "aliases": "La escuela de fakings, A escola de FAKings",
            "urls": ["https://www.fakings.com/en/serie/fakings-academy"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "La escuela de fakings",
            "aliases": "FAKings Academy, A escola de FAKings",
            "urls": ["https://www.fakings.com/es/serie/la-escuela-de-fakings"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "A escola de FAKings",
            "aliases": "FAKings Academy, La escuela de fakings",
            "urls": ["https://www.fakings.com/pt/serie/a-escola-de-fakings"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    121: {
        "en": {
            "name": "I'm a Webcam girl.",
            "aliases": "Soy webcamer, Sou câmera web",
            "urls": ["https://www.fakings.com/en/serie/im-a-webcam-girl"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Soy webcamer",
            "aliases": "I'm a Webcam girl., Sou câmera web",
            "urls": ["https://www.fakings.com/es/serie/soy-webcamer"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Sou câmera web",
            "aliases": "I'm a Webcam girl., Soy webcamer",
            "urls": ["https://www.fakings.com/pt/serie/sou-cmera-web"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    132: {
        "en": {
            "name": "1ST TOURNAMENT: 2016",
            "aliases": "I TORNEO: 2016",
            "urls": ["https://www.madlifes.com/en/serie/i-edicion-20152016"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "es": {
            "name": "I TORNEO: 2016",
            "aliases": "",
            "urls": ["https://www.madlifes.com/es/serie/i-edicion-20152016"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "pt": {
            "name": "I TORNEO: 2016",
            "aliases": "",
            "urls": ["https://www.madlifes.com/pt/serie/i-edicion-20152016"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
    },
    135: {
        "en": {
            "name": "2ND TOURNAMENT: 2017",
            "aliases": "II TORNEO: 2017",
            "urls": ["https://www.madlifes.com/en/serie/ii-torneo-2017"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "es": {
            "name": "II TORNEO: 2017",
            "aliases": "",
            "urls": ["https://www.madlifes.com/es/serie/ii-torneo-2017"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "pt": {
            "name": "II TORNEO: 2017",
            "aliases": "",
            "urls": ["https://www.madlifes.com/pt/serie/ii-torneo-2017"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
    },
    136: {
        "en": {
            "name": "Our First Porn",
            "aliases": "Nuestra Primera Porno",
            "urls": ["https://www.pepeporn.com/en/serie/nuestra-primera-porno"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "es": {
            "name": "Nuestra Primera Porno",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/es/serie/nuestra-primera-porno"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "pt": {
            "name": "Nuestra Primera Porno",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/pt/serie/nuestra-primera-porno"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
    },
    137: {
        "en": {
            "name": "Am I good for porn?",
            "aliases": "¿Valgo para el Porno?",
            "urls": ["https://www.pepeporn.com/en/serie/valgo-para-el-porno"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "es": {
            "name": "¿Valgo para el Porno?",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/es/serie/valgo-para-el-porno"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "pt": {
            "name": "¿Valgo para el Porno?",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/pt/serie/valgo-para-el-porno"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
    },
    138: {
        "en": {
            "name": "Fulfilled Fantasies",
            "aliases": "Fantasias Cumplidas",
            "urls": ["https://www.pepeporn.com/en/serie/fantasias-cumplidas"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "es": {
            "name": "Fantasias Cumplidas",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/es/serie/fantasias-cumplidas"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "pt": {
            "name": "Fantasias Cumplidas",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/pt/serie/fantasias-cumplidas"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
    },
    139: {
        "en": {
            "name": "Amor Propio",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/en/serie/amor-propio"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "es": {
            "name": "Amor Propio",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/es/serie/amor-propio"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "pt": {
            "name": "Amor Propio",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/pt/serie/amor-propio"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
    },
    150: {
        "en": {
            "name": "Las Becerradas de Pepe",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/en/serie/las-becerradas-de-pepe"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "es": {
            "name": "Las Becerradas de Pepe",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/es/serie/las-becerradas-de-pepe"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "pt": {
            "name": "Las Becerradas de Pepe",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/pt/serie/las-becerradas-de-pepe"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
    },
    151: {
        "en": {
            "name": "18 years old",
            "aliases": "18 añitos",
            "urls": ["https://www.pepeporn.com/en/serie/18-anitos"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "es": {
            "name": "18 añitos",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/es/serie/18-anitos"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "pt": {
            "name": "18 añitos",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/pt/serie/18-anitos"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
    },
    152: {
        "en": {
            "name": "Jealous couple",
            "aliases": "Pareja de celosos",
            "urls": ["https://www.pepeporn.com/en/serie/pareja-de-celosos"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "es": {
            "name": "Pareja de celosos",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/es/serie/pareja-de-celosos"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "pt": {
            "name": "Pareja de celosos",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/pt/serie/pareja-de-celosos"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
    },
    153: {
        "en": {
            "name": "Maduritos and Maduritas",
            "aliases": "Maduritos y Maduritas",
            "urls": ["https://www.pepeporn.com/en/serie/maduritos-y-maduritas"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "es": {
            "name": "Maduritos y Maduritas",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/es/serie/maduritos-y-maduritas"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "pt": {
            "name": "Maduritos y Maduritas",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/pt/serie/maduritos-y-maduritas"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
    },
    157: {
        "en": {
            "name": "Busted!",
            "aliases": "Cazadas, Caçadas",
            "urls": ["https://www.fakings.com/en/serie/busted"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Cazadas",
            "aliases": "Busted!, Caçadas",
            "urls": ["https://www.fakings.com/es/serie/pilladas"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Caçadas",
            "aliases": "Busted!, Cazadas",
            "urls": ["https://www.fakings.com/pt/serie/cacadas"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    159: {
        "en": {
            "name": "First FAKings !!",
            "aliases": "First FAKings",
            "urls": ["https://www.fakings.com/en/serie/first-fakings"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "First FAKings",
            "aliases": "First FAKings !!",
            "urls": ["https://www.fakings.com/es/serie/first-fakings"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "First FAKings",
            "aliases": "First FAKings !!",
            "urls": ["https://www.fakings.com/pt/serie/first-fakings"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    160: {
        "en": {
            "name": "Perverting couples",
            "aliases": "Pervirtiendo Parejas, Casais pervertidos",
            "urls": ["https://www.fakings.com/en/serie/perverting-couples"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Pervirtiendo Parejas",
            "aliases": "Perverting couples, Casais pervertidos",
            "urls": ["https://www.fakings.com/es/serie/pervirtiendo-parejas"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Casais pervertidos",
            "aliases": "Perverting couples, Pervirtiendo Parejas",
            "urls": ["https://www.fakings.com/pt/serie/casais-pervertidos"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    162: {
        "en": {
            "name": "Next door girl",
            "aliases": "Es tu vecina, Ela é sua vizinha",
            "urls": ["https://www.fakings.com/en/serie/next-door-girl"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Es tu vecina",
            "aliases": "Next door girl, Ela é sua vizinha",
            "urls": ["https://www.fakings.com/es/serie/es-tu-vecina"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Ela é sua vizinha",
            "aliases": "Next door girl, Es tu vecina",
            "urls": ["https://www.fakings.com/pt/serie/ela-e-sua-vizinha"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    163: {
        "en": {
            "name": "NERD BUSTER!",
            "aliases": "Los Cazatolas, Os caçadores",
            "urls": ["https://www.fakings.com/en/serie/nerd-buster"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Los Cazatolas",
            "aliases": "NERD BUSTER!, Os caçadores",
            "urls": ["https://www.fakings.com/es/serie/los-cazatolas"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Os caçadores",
            "aliases": "NERD BUSTER!, Los Cazatolas",
            "urls": ["https://www.fakings.com/pt/serie/os-cacadores"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    168: {
        "en": {
            "name": "Talk to them",
            "aliases": "Hable con ellas, Fale com elas",
            "urls": ["https://www.fakings.com/en/serie/talk-to-them"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Hable con ellas",
            "aliases": "Talk to them, Fale com elas",
            "urls": ["https://www.fakings.com/es/serie/hable-con-ellas"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Fale com elas",
            "aliases": "Talk to them, Hable con ellas",
            "urls": ["https://www.fakings.com/pt/serie/fale-com-elas"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    170: {
        "en": {
            "name": "I Fiesta Madlifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/en/serie/i-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "es": {
            "name": "I Fiesta Madlifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/es/serie/i-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "pt": {
            "name": "I Fiesta Madlifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/pt/serie/i-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
    },
    171: {
        "en": {
            "name": "II Madlifes Party",
            "aliases": "II Fiesta Madlifes",
            "urls": ["https://www.madlifes.com/en/serie/ii-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "es": {
            "name": "II Fiesta Madlifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/es/serie/ii-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "pt": {
            "name": "II Fiesta Madlifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/pt/serie/ii-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
    },
    172: {
        "en": {
            "name": "III MadLifes Party",
            "aliases": "III Fiesta MadLifes",
            "urls": ["https://www.madlifes.com/en/serie/iii-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "es": {
            "name": "III Fiesta MadLifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/es/serie/iii-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "pt": {
            "name": "III Fiesta MadLifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/pt/serie/iii-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
    },
    173: {
        "en": {
            "name": "IV MadLifes Party",
            "aliases": "IV Fiesta MadLifes",
            "urls": ["https://www.madlifes.com/en/serie/iv-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "es": {
            "name": "IV Fiesta MadLifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/es/serie/iv-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "pt": {
            "name": "IV Fiesta MadLifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/pt/serie/iv-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
    },
    174: {
        "en": {
            "name": "V MadLifes Party",
            "aliases": "V Fiesta MadLifes",
            "urls": ["https://www.madlifes.com/en/serie/v-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "es": {
            "name": "V Fiesta MadLifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/es/serie/v-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "pt": {
            "name": "V Fiesta MadLifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/pt/serie/v-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
    },
    175: {
        "en": {
            "name": "VI MadLifes Party",
            "aliases": "VI Fiesta MadLifes",
            "urls": ["https://www.madlifes.com/en/serie/vi-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "es": {
            "name": "VI Fiesta MadLifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/es/serie/vi-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "pt": {
            "name": "VI Fiesta MadLifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/pt/serie/vi-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
    },
    176: {
        "en": {
            "name": "VII MadLifes Party",
            "aliases": "VII Fiesta MadLifes",
            "urls": ["https://www.madlifes.com/en/serie/vii-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "es": {
            "name": "VII Fiesta MadLifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/es/serie/vii-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "pt": {
            "name": "VII Fiesta MadLifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/pt/serie/vii-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
    },
    177: {
        "en": {
            "name": "I Reality",
            "aliases": "",
            "urls": ["https://www.madgays.com/en/serie/i-reality-madgays"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "es": {
            "name": "I Reality",
            "aliases": "",
            "urls": ["https://www.madgays.com/es/serie/i-reality-madgays"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "pt": {
            "name": "I Reality",
            "aliases": "",
            "urls": ["https://www.madgays.com/pt/serie/i-reality-madgays"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
    },
    178: {
        "en": {
            "name": "Heteropajas",
            "aliases": "",
            "urls": ["https://www.madgays.com/en/serie/heteropajas"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "es": {
            "name": "Heteropajas",
            "aliases": "",
            "urls": ["https://www.madgays.com/es/serie/heteropajas"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "pt": {
            "name": "Heteropajas",
            "aliases": "",
            "urls": ["https://www.madgays.com/pt/serie/heteropajas"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
    },
    179: {
        "en": {
            "name": "VIII MadLifes Party",
            "aliases": "VIII Fiesta MadLifes",
            "urls": ["https://www.madlifes.com/en/serie/viii-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "es": {
            "name": "VIII Fiesta MadLifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/es/serie/viii-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "pt": {
            "name": "VIII Fiesta MadLifes",
            "aliases": "",
            "urls": ["https://www.madlifes.com/pt/serie/viii-fiesta-madlifes"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
    },
    180: {
        "en": {
            "name": "Telepillados",
            "aliases": "",
            "urls": ["https://www.madgays.com/en/serie/telepillados"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "es": {
            "name": "Telepillados",
            "aliases": "",
            "urls": ["https://www.madgays.com/es/serie/telepillados"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "pt": {
            "name": "Telepillados",
            "aliases": "",
            "urls": ["https://www.madgays.com/pt/serie/telepillados"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
    },
    182: {
        "en": {
            "name": "MadLifes Festivities - 2018",
            "aliases": "Fiestas MadLifes - 2018",
            "urls": ["https://www.madlifes.com/en/serie/fiestas-madlifes-2018"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "es": {
            "name": "Fiestas MadLifes - 2018",
            "aliases": "",
            "urls": ["https://www.madlifes.com/es/serie/fiestas-madlifes-2018"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "pt": {
            "name": "Fiestas MadLifes - 2018",
            "aliases": "",
            "urls": ["https://www.madlifes.com/pt/serie/fiestas-madlifes-2018"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
    },
    183: {
        "en": {
            "name": "Polvazos Actores Consagrados",
            "aliases": "",
            "urls": ["https://www.madgays.com/en/serie/polvazos-actores-consagrados"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "es": {
            "name": "Polvazos Actores Consagrados",
            "aliases": "",
            "urls": ["https://www.madgays.com/es/serie/polvazos-actores-consagrados"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "pt": {
            "name": "Polvazos Actores Consagrados",
            "aliases": "",
            "urls": ["https://www.madgays.com/pt/serie/polvazos-actores-consagrados"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
    },
    184: {
        "en": {
            "name": "II  Reality",
            "aliases": "",
            "urls": ["https://www.madgays.com/en/serie/ii-reality"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "es": {
            "name": "II  Reality",
            "aliases": "",
            "urls": ["https://www.madgays.com/es/serie/ii-reality"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "pt": {
            "name": "II  Reality",
            "aliases": "",
            "urls": ["https://www.madgays.com/pt/serie/ii-reality"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
    },
    185: {
        "en": {
            "name": "Amigos Martin Mazza",
            "aliases": "",
            "urls": ["https://www.madgays.com/en/serie/amigos-de-martin-mazza"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "es": {
            "name": "Amigos Martin Mazza",
            "aliases": "",
            "urls": ["https://www.madgays.com/es/serie/amigos-de-martin-mazza"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "pt": {
            "name": "Amigos Martin Mazza",
            "aliases": "",
            "urls": ["https://www.madgays.com/pt/serie/amigos-de-martin-mazza"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
    },
    186: {
        "en": {
            "name": "EnClaveGay 2018",
            "aliases": "",
            "urls": ["https://www.madgays.com/en/serie/enclavegay-2018"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "es": {
            "name": "EnClaveGay 2018",
            "aliases": "",
            "urls": ["https://www.madgays.com/es/serie/enclavegay-2018"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "pt": {
            "name": "EnClaveGay 2018",
            "aliases": "",
            "urls": ["https://www.madgays.com/pt/serie/enclavegay-2018"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
    },
    187: {
        "en": {
            "name": "Trans FAKings",
            "aliases": "",
            "urls": ["https://www.fakings.com/en/serie/trans-fakings"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Trans FAKings",
            "aliases": "",
            "urls": ["https://www.fakings.com/es/serie/trans-fakings"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Trans FAKings",
            "aliases": "",
            "urls": ["https://www.fakings.com/pt/serie/trans-fakings"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    188: {
        "en": {
            "name": "My first casting",
            "aliases": "Mi primer casting, Meu primeiro casting",
            "urls": ["https://www.madgays.com/en/serie/my-first-casting"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "es": {
            "name": "Mi primer casting",
            "aliases": "My first casting, Meu primeiro casting",
            "urls": ["https://www.madgays.com/es/serie/mi-primer-casting"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "pt": {
            "name": "Meu primeiro casting",
            "aliases": "My first casting, Mi primer casting",
            "urls": ["https://www.madgays.com/pt/serie/meu-primeiro-casting"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
    },
    189: {
        "en": {
            "name": "MadLifes Festivities - 2019",
            "aliases": "Fiestas MadLifes - 2019",
            "urls": ["https://www.madlifes.com/en/serie/fiestas-madlifes-2019"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "es": {
            "name": "Fiestas MadLifes - 2019",
            "aliases": "",
            "urls": ["https://www.madlifes.com/es/serie/fiestas-madlifes-2019"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
        "pt": {
            "name": "Fiestas MadLifes - 2019",
            "aliases": "",
            "urls": ["https://www.madlifes.com/pt/serie/fiestas-madlifes-2019"],
            "parent": {
                "name": "MadLifes",
                "urls": ["https://www.madlifes.com"],
            },
        },
    },
    190: {
        "en": {
            "name": "HotGay 2019",
            "aliases": "",
            "urls": ["https://www.madgays.com/en/serie/hotgay-2019"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "es": {
            "name": "HotGay 2019",
            "aliases": "",
            "urls": ["https://www.madgays.com/es/serie/hotgay-2019"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "pt": {
            "name": "HotGay 2019",
            "aliases": "",
            "urls": ["https://www.madgays.com/pt/serie/hotgay-2019"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
    },
    191: {
        "en": {
            "name": "Gaypajas",
            "aliases": "",
            "urls": ["https://www.madgays.com/en/serie/gaypaja"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "es": {
            "name": "Gaypajas",
            "aliases": "",
            "urls": ["https://www.madgays.com/es/serie/gaypaja"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "pt": {
            "name": "Gaypajas",
            "aliases": "",
            "urls": ["https://www.madgays.com/pt/serie/gaypaja"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
    },
    192: {
        "en": {
            "name": "FREE pussy day",
            "aliases": "El día del coño GRATIS, O dia da buceta GRATIS",
            "urls": ["https://www.fakings.com/en/serie/free-pussy-day"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "El día del coño GRATIS",
            "aliases": "FREE pussy day, O dia da buceta GRATIS",
            "urls": ["https://www.fakings.com/es/serie/el-dia-del-cono-gratis"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "O dia da buceta GRATIS",
            "aliases": "FREE pussy day, El día del coño GRATIS",
            "urls": ["https://www.fakings.com/pt/serie/o-dia-da-buceta-gratis"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    193: {
        "en": {
            "name": "My first anal",
            "aliases": "Mi primer anal, Meu primeiro anal",
            "urls": ["https://www.fakings.com/en/serie/my-first-anal"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Mi primer anal",
            "aliases": "My first anal, Meu primeiro anal",
            "urls": ["https://www.fakings.com/es/serie/mi-primer-anal"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Meu primeiro anal",
            "aliases": "My first anal, Mi primer anal",
            "urls": ["https://www.fakings.com/pt/serie/meu-primeiro-anal"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    195: {
        "en": {
            "name": "FAKings PornStars",
            "aliases": "Estrelas pornôs FAKings",
            "urls": ["https://www.fakings.com/en/serie/fakings-pornstars"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "FAKings PornStars",
            "aliases": "Estrelas pornôs FAKings",
            "urls": ["https://www.fakings.com/es/serie/fakings-old-stars"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Estrelas pornôs FAKings",
            "aliases": "FAKings PornStars",
            "urls": ["https://www.fakings.com/pt/serie/estrelas-porns-fakings"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    196: {
        "en": {
            "name": "Curvy Girls",
            "aliases": "Chicas Curvis, Garotas com curvas",
            "urls": ["https://www.fakings.com/en/serie/curvy-girls"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Chicas Curvis",
            "aliases": "Curvy Girls, Garotas com curvas",
            "urls": ["https://www.fakings.com/es/serie/chicas-curvis"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Garotas com curvas",
            "aliases": "Curvy Girls, Chicas Curvis",
            "urls": ["https://www.fakings.com/pt/serie/garotas-com-curvas"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    197: {
        "en": {
            "name": "Newbies... or so they say ;)",
            "aliases": "Novatas... O eso dicen ;), Novatas… ou isso dizem",
            "urls": ["https://www.fakings.com/en/serie/newbies-or-so-they-say-"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Novatas... O eso dicen ;)",
            "aliases": "Newbies... or so they say ;), Novatas… ou isso dizem",
            "urls": ["https://www.fakings.com/es/serie/novatas"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Novatas… ou isso dizem",
            "aliases": "Newbies... or so they say ;), Novatas... O eso dicen ;)",
            "urls": ["https://www.fakings.com/pt/serie/novatas-ou-isso-dizem"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    198: {
        "en": {
            "name": "EnClaveGay 2019",
            "aliases": "",
            "urls": ["https://www.madgays.com/en/serie/enclavegay-2019"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "es": {
            "name": "EnClaveGay 2019",
            "aliases": "",
            "urls": ["https://www.madgays.com/es/serie/enclavegay-2019"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
        "pt": {
            "name": "EnClaveGay 2019",
            "aliases": "",
            "urls": ["https://www.madgays.com/pt/serie/enclavegay-2019"],
            "parent": {
                "name": "MadGays",
                "urls": ["https://www.madgays.com"],
            },
        },
    },
    199: {
        "en": {
            "name": "Parejas.NET",
            "aliases": "",
            "urls": ["https://www.fakings.com/en/serie/parejasnet"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Parejas.NET",
            "aliases": "",
            "urls": ["https://www.fakings.com/es/serie/parejasnet"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Parejas.NET",
            "aliases": "",
            "urls": ["https://www.fakings.com/pt/serie/parejasnet"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    200: {
        "en": {
            "name": "MEGA COCKS",
            "aliases": "MEGA RABOS",
            "urls": ["https://www.fakings.com/en/serie/elephant-tails"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "MEGA RABOS",
            "aliases": "MEGA COCKS",
            "urls": ["https://www.fakings.com/es/serie/rabos-de-caballo"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "MEGA RABOS",
            "aliases": "MEGA COCKS",
            "urls": ["https://www.fakings.com/pt/serie/rabos-de-elefante"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    201: {
        "en": {
            "name": "Quarantine Stories",
            "aliases": "Historias de Cuarentena, Histórias de quarentena",
            "urls": ["https://www.fakings.com/en/serie/quarantine-stories"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Historias de Cuarentena",
            "aliases": "Quarantine Stories, Histórias de quarentena",
            "urls": ["https://www.fakings.com/es/serie/historias-de-cuarentena"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Histórias de quarentena",
            "aliases": "Quarantine Stories, Historias de Cuarentena",
            "urls": ["https://www.fakings.com/pt/serie/historias-de-quarentena"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    202: {
        "en": {
            "name": "LoverFANS",
            "aliases": "LoverFans",
            "urls": ["https://www.loverfans.com/en/serie/loverfans"],
            "parent": {
                "name": "Loverfans",
                "urls": ["https://www.loverfans.com"],
            },
        },
        "es": {
            "name": "LoverFANS",
            "aliases": "LoverFans",
            "urls": ["https://www.loverfans.com/es/serie/loverfans"],
            "parent": {
                "name": "Loverfans",
                "urls": ["https://www.loverfans.com"],
            },
        },
        "pt": {
            "name": "LoverFans",
            "aliases": "LoverFANS",
            "urls": ["https://www.loverfans.com/pt/serie/loverfans"],
            "parent": {
                "name": "Loverfans",
                "urls": ["https://www.loverfans.com"],
            },
        },
    },
    203: {
        "en": {
            "name": "Recorded at home",
            "aliases": "Grabado en casa",
            "urls": ["https://www.pepeporn.com/en/serie/porno-en-casa"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "es": {
            "name": "Grabado en casa",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/es/serie/porno-en-casa"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "pt": {
            "name": "Grabado en casa",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/pt/serie/porno-en-casa"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
    },
    205: {
        "en": {
            "name": "Fuck my partner",
            "aliases": "Follate a mi pareja",
            "urls": ["https://www.pepeporn.com/en/serie/follate-a-mi-pareja"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "es": {
            "name": "Follate a mi pareja",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/es/serie/follate-a-mi-pareja"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "pt": {
            "name": "Follate a mi pareja",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/pt/serie/follate-a-mi-pareja"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
    },
    206: {
        "en": {
            "name": "I Want to Be a Cuckold",
            "aliases": "Quiero ser Cornudo",
            "urls": ["https://www.pepeporn.com/en/serie/quiero-ser-cornudo"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "es": {
            "name": "Quiero ser Cornudo",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/es/serie/quiero-ser-cornudo"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
        "pt": {
            "name": "Quiero ser Cornudo",
            "aliases": "",
            "urls": ["https://www.pepeporn.com/pt/serie/quiero-ser-cornudo"],
            "parent": {
                "name": "PepePorn",
                "urls": ["https://www.pepeporn.com"],
            },
        },
    },
    207: {
        "en": {
            "name": "LoverFans",
            "aliases": "LiverFans",
            "urls": ["https://www.fakings.com/en/serie/loverfans"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "LoverFans",
            "aliases": "LiverFans",
            "urls": ["https://www.fakings.com/es/serie/loverfans"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "LiverFans",
            "aliases": "LoverFans",
            "urls": ["https://www.fakings.com/pt/serie/liverfans"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    208: {
        "en": {
            "name": "La Porno House",
            "aliases": "",
            "urls": ["https://www.fakings.com/en/serie/la-porno-house"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "La Porno House",
            "aliases": "",
            "urls": ["https://www.fakings.com/es/serie/la-porno-house"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "La Porno House",
            "aliases": "",
            "urls": ["https://www.fakings.com/pt/serie/la-porno-house"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    210: {
        "en": {
            "name": "Blind date",
            "aliases": "Citas a ciegas, Encontros às cegas",
            "urls": ["https://www.fakings.com/en/serie/blind-date"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Citas a ciegas",
            "aliases": "Blind date, Encontros às cegas",
            "urls": ["https://www.fakings.com/es/serie/citas-a-ciegas"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Encontros às cegas",
            "aliases": "Blind date, Citas a ciegas",
            "urls": ["https://www.fakings.com/pt/serie/encontros-s-cegas"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    211: {
        "en": {
            "name": "Girls get nigged",
            "aliases": "Negrateadas, Escurecidos",
            "urls": ["https://www.nigged.com/en/serie/girls-get-nigged"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
        "es": {
            "name": "Negrateadas",
            "aliases": "Girls get nigged, Escurecidos",
            "urls": ["https://www.nigged.com/es/serie/negrateadas"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
        "pt": {
            "name": "Escurecidos",
            "aliases": "Girls get nigged, Negrateadas",
            "urls": ["https://www.nigged.com/pt/serie/escurecidos"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
    },
    212: {
        "en": {
            "name": "Ivan Amor",
            "aliases": "Ivan amor",
            "urls": ["https://www.fakings.com/en/serie/ivan-amor"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Ivan Amor",
            "aliases": "Ivan amor",
            "urls": ["https://www.fakings.com/es/serie/ivan-amor"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Ivan amor",
            "aliases": "Ivan Amor",
            "urls": ["https://www.fakings.com/pt/serie/ivan-amor"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    213: {
        "en": {
            "name": "A present for my wife",
            "aliases": "Un regalo para mi mujer, Um presente para minha mulher",
            "urls": ["https://www.nigged.com/en/serie/a-present-for-my-wf"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
        "es": {
            "name": "Un regalo para mi mujer",
            "aliases": "A present for my wife, Um presente para minha mulher",
            "urls": ["https://www.nigged.com/es/serie/un-regalo-para-mi-mujer"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
        "pt": {
            "name": "Um presente para minha mulher",
            "aliases": "A present for my wife, Un regalo para mi mujer",
            "urls": ["https://www.nigged.com/pt/serie/um-presente-para-minha-mulher"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
    },
    214: {
        "en": {
            "name": "Help my mamma",
            "aliases": "Ayuda a mi madre, Ajuda a minha mãe",
            "urls": ["https://www.nigged.com/en/serie/help-my-mamma"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
        "es": {
            "name": "Ayuda a mi madre",
            "aliases": "Help my mamma, Ajuda a minha mãe",
            "urls": ["https://www.nigged.com/es/serie/ayuda-a-mi-madre"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
        "pt": {
            "name": "Ajuda a minha mãe",
            "aliases": "Help my mamma, Ayuda a mi madre",
            "urls": ["https://www.nigged.com/pt/serie/ajuda-a-minha-me"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
    },
    215: {
        "en": {
            "name": "DILF Club",
            "aliases": "Club Puretas",
            "urls": ["https://www.fakings.com/en/serie/dilf-club"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "es": {
            "name": "Club Puretas",
            "aliases": "DILF Club",
            "urls": ["https://www.fakings.com/es/serie/club-puretas"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
        "pt": {
            "name": "Club Puretas",
            "aliases": "DILF Club",
            "urls": ["https://www.fakings.com/pt/serie/club-puretas"],
            "parent": {
                "name": "FAKings",
                "urls": ["https://www.fakings.com"],
            },
        },
    },
    216: {
        "en": {
            "name": "My hidden secret",
            "aliases": "Mi gran secreto",
            "urls": ["https://www.nigged.com/en/serie/my-hidden-secret"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
        "es": {
            "name": "Mi gran secreto",
            "aliases": "My hidden secret",
            "urls": ["https://www.nigged.com/es/serie/mi-gran-secreto"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
        "pt": {
            "name": "Mi gran secreto",
            "aliases": "My hidden secret",
            "urls": ["https://www.nigged.com/pt/serie/mi-gran-secreto"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
    },
    217: {
        "en": {
            "name": "Nigged party",
            "aliases": "Merienda de Negros",
            "urls": ["https://www.nigged.com/en/serie/nigged-party"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
        "es": {
            "name": "Merienda de Negros",
            "aliases": "Nigged party",
            "urls": ["https://www.nigged.com/es/serie/merienda-de-negros"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
        "pt": {
            "name": "Merienda de Negros",
            "aliases": "Nigged party",
            "urls": ["https://www.nigged.com/pt/serie/merienda-de-negros"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
    },
    218: {
        "en": {
            "name": "Coffee Bonbon",
            "aliases": "Bombón de Café, Bombom de Café",
            "urls": ["https://www.nigged.com/en/serie/coffee-bonbon"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
        "es": {
            "name": "Bombón de Café",
            "aliases": "Coffee Bonbon, Bombom de Café",
            "urls": ["https://www.nigged.com/es/serie/bombon-de-licor"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
        "pt": {
            "name": "Bombom de Café",
            "aliases": "Coffee Bonbon, Bombón de Café",
            "urls": ["https://www.nigged.com/pt/serie/bombom-de-cafe"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
    },
    219: {
        "en": {
            "name": "Oh my nigged",
            "aliases": "Mira mi negro",
            "urls": ["https://www.nigged.com/en/serie/oh-my-nigged"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
        "es": {
            "name": "Mira mi negro",
            "aliases": "Oh my nigged",
            "urls": ["https://www.nigged.com/es/serie/mira-mi-negro"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
        "pt": {
            "name": "Mira mi negro",
            "aliases": "Oh my nigged",
            "urls": ["https://www.nigged.com/pt/serie/mira-mi-negro"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
    },
    220: {
        "en": {
            "name": "The Diary of Apolonia Lapiedra",
            "aliases": "El Diario de Apolonia Lapiedra",
            "urls": [
                "https://www.pornermates.com/en/serie/el-diario-de-apolonia-lapiedra"
            ],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
        "es": {
            "name": "El Diario de Apolonia Lapiedra",
            "aliases": "",
            "urls": [
                "https://www.pornermates.com/es/serie/el-diario-de-apolonia-lapiedra"
            ],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
        "pt": {
            "name": "El Diario de Apolonia Lapiedra",
            "aliases": "",
            "urls": [
                "https://www.pornermates.com/pt/serie/el-diario-de-apolonia-lapiedra"
            ],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
    },
    221: {
        "en": {
            "name": "Nacho Vidal: Embedder",
            "aliases": "Nacho Vidal: Empotrador",
            "urls": ["https://www.pornermates.com/en/serie/nacho-vidal-empotrador"],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
        "es": {
            "name": "Nacho Vidal: Empotrador",
            "aliases": "",
            "urls": ["https://www.pornermates.com/es/serie/nacho-vidal-empotrador"],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
        "pt": {
            "name": "Nacho Vidal: Empotrador",
            "aliases": "",
            "urls": ["https://www.pornermates.com/pt/serie/nacho-vidal-empotrador"],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
    },
    222: {
        "en": {
            "name": "More than 2 are NOT crowds",
            "aliases": "Mas de 2 NO son multitud",
            "urls": ["https://www.pornermates.com/en/serie/mas-de-2-no-son-multitud"],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
        "es": {
            "name": "Mas de 2 NO son multitud",
            "aliases": "",
            "urls": ["https://www.pornermates.com/es/serie/mas-de-2-no-son-multitud"],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
        "pt": {
            "name": "Mas de 2 NO son multitud",
            "aliases": "",
            "urls": ["https://www.pornermates.com/pt/serie/mas-de-2-no-son-multitud"],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
    },
    223: {
        "en": {
            "name": "They set it up... you just watch",
            "aliases": "Ellas se lo montan... tu solo miras",
            "urls": [
                "https://www.pornermates.com/en/serie/ellas-se-lo-montan-tu-solo-miras"
            ],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
        "es": {
            "name": "Ellas se lo montan... tu solo miras",
            "aliases": "",
            "urls": [
                "https://www.pornermates.com/es/serie/ellas-se-lo-montan-tu-solo-miras"
            ],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
        "pt": {
            "name": "Ellas se lo montan... tu solo miras",
            "aliases": "",
            "urls": [
                "https://www.pornermates.com/pt/serie/ellas-se-lo-montan-tu-solo-miras"
            ],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
    },
    224: {
        "en": {
            "name": "I have a friend who wants to be a Pornstar",
            "aliases": "Tengo una amiga que quiere ser PornStar",
            "urls": [
                "https://www.pornermates.com/en/serie/tengo-una-amiga-que-quiere-ser-pornstar"
            ],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
        "es": {
            "name": "Tengo una amiga que quiere ser PornStar",
            "aliases": "",
            "urls": [
                "https://www.pornermates.com/es/serie/tengo-una-amiga-que-quiere-ser-pornstar"
            ],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
        "pt": {
            "name": "Tengo una amiga que quiere ser PornStar",
            "aliases": "",
            "urls": [
                "https://www.pornermates.com/pt/serie/tengo-una-amiga-que-quiere-ser-pornstar"
            ],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
    },
    225: {
        "en": {
            "name": "Destroyers Made in Spain",
            "aliases": "",
            "urls": ["https://www.pornermates.com/en/serie/destroyers-made-in-spain"],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
        "es": {
            "name": "Destroyers Made in Spain",
            "aliases": "",
            "urls": ["https://www.pornermates.com/es/serie/destroyers-made-in-spain"],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
        "pt": {
            "name": "Destroyers Made in Spain",
            "aliases": "",
            "urls": ["https://www.pornermates.com/pt/serie/destroyers-made-in-spain"],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
    },
    226: {
        "en": {
            "name": "DIVAS... They had to be here",
            "aliases": "DIVAS... Tenían que estar aquí",
            "urls": [
                "https://www.pornermates.com/en/serie/divas-tenian-que-estar-aqui"
            ],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
        "es": {
            "name": "DIVAS... Tenían que estar aquí",
            "aliases": "",
            "urls": [
                "https://www.pornermates.com/es/serie/divas-tenian-que-estar-aqui"
            ],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
        "pt": {
            "name": "DIVAS... Tenían que estar aquí",
            "aliases": "",
            "urls": [
                "https://www.pornermates.com/pt/serie/divas-tenian-que-estar-aqui"
            ],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
    },
    227: {
        "en": {
            "name": "We Are In Love",
            "aliases": "Estamos In Love",
            "urls": ["https://www.pornermates.com/en/serie/estamos-in-love"],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
        "es": {
            "name": "Estamos In Love",
            "aliases": "",
            "urls": ["https://www.pornermates.com/es/serie/estamos-in-love"],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
        "pt": {
            "name": "Estamos In Love",
            "aliases": "",
            "urls": ["https://www.pornermates.com/pt/serie/estamos-in-love"],
            "parent": {
                "name": "PornerMates",
                "urls": ["https://www.pornermates.com"],
            },
        },
    },
    228: {
        "en": {
            "name": "Solidarity porn",
            "aliases": "Porno solidario",
            "urls": ["https://www.nigged.com/en/serie/porno-solidario"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
        "es": {
            "name": "Porno solidario",
            "aliases": "",
            "urls": ["https://www.nigged.com/es/serie/porno-solidario"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
        "pt": {
            "name": "Porno solidario",
            "aliases": "",
            "urls": ["https://www.nigged.com/pt/serie/porno-solidario"],
            "parent": {
                "name": "Nigged",
                "urls": ["https://www.nigged.com"],
            },
        },
    },
    229: {
        "en": {
            "name": "_NiNiSeX_",
            "aliases": "",
            "urls": ["https://www.morenolust.com/en/serie/ninisex"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "es": {
            "name": "_NiNiSeX_",
            "aliases": "",
            "urls": ["https://www.morenolust.com/es/serie/ninisex"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "pt": {
            "name": "_NiNiSeX_",
            "aliases": "",
            "urls": ["https://www.morenolust.com/pt/serie/ninisex"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
    },
    230: {
        "en": {
            "name": "Parodies",
            "aliases": "Parodias, Paródias",
            "urls": ["https://www.morenolust.com/en/serie/parodies"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "es": {
            "name": "Parodias",
            "aliases": "Parodies, Paródias",
            "urls": ["https://www.morenolust.com/es/serie/parodias"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "pt": {
            "name": "Paródias",
            "aliases": "Parodies, Parodias",
            "urls": ["https://www.morenolust.com/pt/serie/parodias"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
    },
    231: {
        "en": {
            "name": "Immature shenanigans",
            "aliases": "Travesuras inmaduras, Convênios imaturos",
            "urls": ["https://www.morenolust.com/en/serie/immature-shenanigans"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "es": {
            "name": "Travesuras inmaduras",
            "aliases": "Immature shenanigans, Convênios imaturos",
            "urls": ["https://www.morenolust.com/es/serie/travesuras-inmaduras"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "pt": {
            "name": "Convênios imaturos",
            "aliases": "Immature shenanigans, Travesuras inmaduras",
            "urls": ["https://www.morenolust.com/pt/serie/convenios-imaturos"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
    },
    232: {
        "en": {
            "name": "Back after behind",
            "aliases": "Tras tras por detrás, Volta atrás atrás",
            "urls": ["https://www.morenolust.com/en/serie/back-after-behind"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "es": {
            "name": "Tras tras por detrás",
            "aliases": "Back after behind, Volta atrás atrás",
            "urls": ["https://www.morenolust.com/es/serie/tras-tras-por-detras"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "pt": {
            "name": "Volta atrás atrás",
            "aliases": "Back after behind, Tras tras por detrás",
            "urls": ["https://www.morenolust.com/pt/serie/volta-atras-atras"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
    },
    233: {
        "en": {
            "name": "Dating young girls",
            "aliases": "Citas jovencitas, Namorar raparigas",
            "urls": ["https://www.morenolust.com/en/serie/dating-young-girls"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "es": {
            "name": "Citas jovencitas",
            "aliases": "Dating young girls, Namorar raparigas",
            "urls": ["https://www.morenolust.com/es/serie/citas-jovencitas"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "pt": {
            "name": "Namorar raparigas",
            "aliases": "Dating young girls, Citas jovencitas",
            "urls": ["https://www.morenolust.com/pt/serie/namorar-raparigas"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
    },
    234: {
        "en": {
            "name": "The tough ones and the mature ones",
            "aliases": "Las duras y las maduras, Os durões e os maduros",
            "urls": [
                "https://www.morenolust.com/en/serie/the-tough-ones-and-the-mature-ones"
            ],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "es": {
            "name": "Las duras y las maduras",
            "aliases": "The tough ones and the mature ones, Os durões e os maduros",
            "urls": ["https://www.morenolust.com/es/serie/las-duras-y-las-maduras"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "pt": {
            "name": "Os durões e os maduros",
            "aliases": "The tough ones and the mature ones, Las duras y las maduras",
            "urls": ["https://www.morenolust.com/pt/serie/os-duroes-e-os-maduros"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
    },
    235: {
        "en": {
            "name": "Mermaids on Earth (trans)",
            "aliases": "Sirenas en tierra (trans), Sereias na Terra (trans)",
            "urls": ["https://www.morenolust.com/en/serie/mermaids-on-earth-trans"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "es": {
            "name": "Sirenas en tierra (trans)",
            "aliases": "Mermaids on Earth (trans), Sereias na Terra (trans)",
            "urls": ["https://www.morenolust.com/es/serie/sirenas-en-tierra-trans"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "pt": {
            "name": "Sereias na Terra (trans)",
            "aliases": "Mermaids on Earth (trans), Sirenas en tierra (trans)",
            "urls": ["https://www.morenolust.com/pt/serie/sereias-na-terra-trans"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
    },
    236: {
        "en": {
            "name": "Brown sugar with cane (interracial)",
            "aliases": "Azúcar moreno con caña (interracial), Açúcar mascavo com cana (interracial)",
            "urls": [
                "https://www.morenolust.com/en/serie/brown-sugar-with-cane-interracial"
            ],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "es": {
            "name": "Azúcar moreno con caña (interracial)",
            "aliases": "Brown sugar with cane (interracial), Açúcar mascavo com cana (interracial)",
            "urls": [
                "https://www.morenolust.com/es/serie/azucar-moreno-con-cana-interracial"
            ],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "pt": {
            "name": "Açúcar mascavo com cana (interracial)",
            "aliases": "Brown sugar with cane (interracial), Azúcar moreno con caña (interracial)",
            "urls": [
                "https://www.morenolust.com/pt/serie/acucar-mascavo-com-cana-interracial"
            ],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
    },
    237: {
        "en": {
            "name": "Hot tourism",
            "aliases": "Turismo hot, Turismo quente",
            "urls": ["https://www.morenolust.com/en/serie/hot-tourism"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "es": {
            "name": "Turismo hot",
            "aliases": "Hot tourism, Turismo quente",
            "urls": ["https://www.morenolust.com/es/serie/turismo-hot"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "pt": {
            "name": "Turismo quente",
            "aliases": "Hot tourism, Turismo hot",
            "urls": ["https://www.morenolust.com/pt/serie/turismo-quente"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
    },
    238: {
        "en": {
            "name": "Group and exchanges",
            "aliases": "Grupal e intercambios, Em grupo e intercâmbios",
            "urls": ["https://www.morenolust.com/en/serie/group-and-exchanges"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "es": {
            "name": "Grupal e intercambios",
            "aliases": "Group and exchanges, Em grupo e intercâmbios",
            "urls": ["https://www.morenolust.com/es/serie/grupal-e-intercambios"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "pt": {
            "name": "Em grupo e intercâmbios",
            "aliases": "Group and exchanges, Grupal e intercambios",
            "urls": ["https://www.morenolust.com/pt/serie/em-grupo-e-intercambios"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
    },
    239: {
        "en": {
            "name": "Country-style skewer",
            "aliases": "Pinchito campestre, Espetinho campestre",
            "urls": ["https://www.morenolust.com/en/serie/country-style-skewer"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "es": {
            "name": "Pinchito campestre",
            "aliases": "Country-style skewer, Espetinho campestre",
            "urls": ["https://www.morenolust.com/es/serie/pinchito-campestre"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "pt": {
            "name": "Espetinho campestre",
            "aliases": "Country-style skewer, Pinchito campestre",
            "urls": ["https://www.morenolust.com/pt/serie/espetinho-campestre"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
    },
    240: {
        "en": {
            "name": "Caught and Castings",
            "aliases": "Pilladas y castings, Apanhadas e castings",
            "urls": ["https://www.morenolust.com/en/serie/caught-and-castings"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "es": {
            "name": "Pilladas y castings",
            "aliases": "Caught and Castings, Apanhadas e castings",
            "urls": ["https://www.morenolust.com/es/serie/pilladas-y-castings"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "pt": {
            "name": "Apanhadas e castings",
            "aliases": "Caught and Castings, Pilladas y castings",
            "urls": ["https://www.morenolust.com/pt/serie/apanhadas-e-castings"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
    },
    241: {
        "en": {
            "name": "Hotties",
            "aliases": "Pibones",
            "urls": ["https://www.morenolust.com/en/serie/hotties"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "es": {
            "name": "Pibones",
            "aliases": "Hotties",
            "urls": ["https://www.morenolust.com/es/serie/jacas"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "pt": {
            "name": "Pibones",
            "aliases": "Hotties",
            "urls": ["https://www.morenolust.com/pt/serie/pibones"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
    },
    242: {
        "en": {
            "name": "XXL",
            "aliases": "XXG",
            "urls": ["https://www.morenolust.com/en/serie/xxl"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "es": {
            "name": "XXL",
            "aliases": "XXG",
            "urls": ["https://www.morenolust.com/es/serie/xxl"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "pt": {
            "name": "XXG",
            "aliases": "XXL",
            "urls": ["https://www.morenolust.com/pt/serie/xxg"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
    },
    244: {
        "en": {
            "name": "Fetishes",
            "aliases": "Fetiches",
            "urls": ["https://www.morenolust.com/en/serie/fetishes"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "es": {
            "name": "Fetiches",
            "aliases": "Fetishes",
            "urls": ["https://www.morenolust.com/es/serie/fetiches"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "pt": {
            "name": "Fetiches",
            "aliases": "Fetishes",
            "urls": ["https://www.morenolust.com/pt/serie/fetiches"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
    },
    245: {
        "en": {
            "name": "Couples",
            "aliases": "Parejas, Casais",
            "urls": ["https://www.morenolust.com/en/serie/couples"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "es": {
            "name": "Parejas",
            "aliases": "Couples, Casais",
            "urls": ["https://www.morenolust.com/es/serie/parejas"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
        "pt": {
            "name": "Casais",
            "aliases": "Couples, Parejas",
            "urls": ["https://www.morenolust.com/pt/serie/casais"],
            "parent": {
                "name": "MorenoLust",
                "urls": ["https://www.morenolust.com"],
            },
        },
    },
    # Rocco Vids has no site of its own: its scenes are listed on the other network sites
    247: {
        "en": {
            "name": "Orgies and GangBangs",
            "aliases": "Orgías y GangBangs, Orgias e GangBangs",
            "parent": {"name": "Rocco Vids"},
        },
        "es": {
            "name": "Orgías y GangBangs",
            "aliases": "Orgies and GangBangs, Orgias e GangBangs",
            "parent": {"name": "Rocco Vids"},
        },
        "pt": {
            "name": "Orgias e GangBangs",
            "aliases": "Orgies and GangBangs, Orgías y GangBangs",
            "parent": {"name": "Rocco Vids"},
        },
    },
    248: {
        "en": {
            "name": "Rocco Lesbians",
            "aliases": "Rocco Lésbicos",
            "parent": {"name": "Rocco Vids"},
        },
        "es": {
            "name": "Rocco Lésbicos",
            "aliases": "Rocco Lesbians",
            "parent": {"name": "Rocco Vids"},
        },
        "pt": {
            "name": "Rocco Lésbicos",
            "aliases": "Rocco Lesbians",
            "parent": {"name": "Rocco Vids"},
        },
    },
    249: {
        "en": {
            "name": "Rocco Anal",
            "parent": {"name": "Rocco Vids"},
        },
        "es": {
            "name": "Rocco Anal",
            "parent": {"name": "Rocco Vids"},
        },
        "pt": {
            "name": "Rocco Anal",
            "parent": {"name": "Rocco Vids"},
        },
    },
    250: {
        "en": {
            "name": "Rocco Vip",
            "parent": {"name": "Rocco Vids"},
        },
        "es": {
            "name": "Rocco Vip",
            "parent": {"name": "Rocco Vids"},
        },
        "pt": {
            "name": "Rocco Vip",
            "parent": {"name": "Rocco Vids"},
        },
    },
    251: {
        "en": {
            "name": "BBC - Big Black Cock",
            "aliases": "BBC - Grande Galo Preto",
            "parent": {"name": "Rocco Vids"},
        },
        "es": {
            "name": "BBC - Big Black Cock",
            "aliases": "BBC - Grande Galo Preto",
            "parent": {"name": "Rocco Vids"},
        },
        "pt": {
            "name": "BBC - Grande Galo Preto",
            "aliases": "BBC - Big Black Cock",
            "parent": {"name": "Rocco Vids"},
        },
    },
    252: {
        "en": {
            "name": "BTS - Behind the camera",
            "aliases": "BTS - Detrás de cámara, BTS - Atrás da câmera",
            "parent": {"name": "Rocco Vids"},
        },
        "es": {
            "name": "BTS - Detrás de cámara",
            "aliases": "BTS - Behind the camera, BTS - Atrás da câmera",
            "parent": {"name": "Rocco Vids"},
        },
        "pt": {
            "name": "BTS - Atrás da câmera",
            "aliases": "BTS - Behind the camera, BTS - Detrás de cámara",
            "parent": {"name": "Rocco Vids"},
        },
    },
}
