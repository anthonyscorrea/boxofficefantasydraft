import sys
import logging
from lib.restricted_dict import RestrictedDictKeyValuetypes
from dateutil.parser import parse as dateparse
from datetime import date, datetime
import re

import json

module_logger = logging.getLogger("boxofficefantasydraft.boxofficefantasy")
logging.basicConfig(level=logging.DEBUG)
module_logger = logging


def clean_key(key):
    key = key.lower().replace(" ", "_")

    aliases = dict(
        released="release_date",
        rated="mpaa_rating",
        production="distributor",
        poster="poster_url",
        box_office="box_office_gross",
        box_office_fantasy_score="boxofficefantasy_score",
        mojoID="mojo_id",
        imdbID="imdb_id",
    )

    if "domestic_total" in key:
        aliases.update({key: "domestic_total_gross"})

    return aliases.get(key, key)


def clean_int_string(s):
    return int(re.sub("[^0-9.]", "", s)) * (int(1e6) if "million" in s else 1)


def clean_title_string(s):
    s = clean_parentheticals(
        s, within_pattern="[0-9]{4}"
    )  # Remove year from title (2016)
    s = re.sub(r" - Box Office Mojo", "", s)  # Remove Box Office Mojo from title (2016)
    return s


def clean_runtime_string(s):
    r = re.search(r"(?:(?P<hours>[0-9]+) hrs?\.? )?(?P<minutes>[0-9]+) min\.?", s)
    i = None
    if r:
        hours = r.group("hours") if r.group("hours") else 0
        minutes = r.group("minutes") if r.group("minutes") else 0
        i = int(hours) * 60 + int(minutes)
    return i


def clean_parentheticals(s, within_pattern=r".*?"):
    s = re.sub(f" \({within_pattern}\)", "", s)
    return s


def parse_data(data={}):
    parsed_data = {clean_key(k): v for k, v in data.items() if (v != "N/A" and v != "")}

    for k, v in parsed_data.items():
        if isinstance(v, str):
            if "In Theaters" in v:
                v = v.replace("In Theaters", "")
                parsed_data["release_date"] = v
                parsed_data.pop(k)

                # title
    k = "title"
    try:
        if parsed_data.get(k):
            parsed_data[k] = clean_title_string(parsed_data[k])
    except Exception as e:
        module_logger.exception(f"Error in parsing {k}")

        # integers
    for k in ["domestic_total_gross", "production_budget", "boxofficefantasy_score"]:
        try:
            if parsed_data.get(k):
                parsed_data[k] = clean_int_string(parsed_data.get(k))
        except Exception as e:
            module_logger.exception(f"Error in parsing {k}")

            # date
    try:
        if parsed_data.get("release_date"):
            if isinstance(parsed_data["release_date"], str):
                parsed_data["release_date"] = dateparse(
                    parsed_data["release_date"]
                ).date()
            elif isinstance(parsed_data, datetime):
                parsed_data["release_date"] = parsed_data["release_date"].date()
    except Exception as e:
        module_logger.exception(f"Error in parsing release_date")

    except Exception as e:
        module_logger.exception(f"Error in parsing production_budget")

        # runtime
    try:
        if parsed_data.get("runtime"):
            parsed_data["runtime"] = clean_runtime_string(parsed_data.get("runtime"))
    except Exception as e:
        module_logger.exception(f"Error in parsing runtime")

        # lists
    for k in ["actors", "genre", "writers"]:
        try:
            if parsed_data.get(k):
                parsed_data[k] = [s.strip() for s in parsed_data.get(k).split(",")]

        except Exception as e:
            module_logger.exception(f"Error in parsing {k}")

    try:
        if parsed_data.get("writer"):
            parsed_data["writer"] = [
                clean_parentheticals(s) for s in parsed_data["writer"]
            ]

    except Exception as e:
        module_logger.exception(f"Error in parsing writers")

    return parsed_data


# class SlObject(RestrictedDictKeyValuetypes):
# 	def __init__(self, allowed_keys_valuetypes, **kwargs):
# 		self._sql_for_key={i[0]:i[2] for i in allowed_keys_valuetypes if len(i)>2 else None}
# 		super().__init__(allowed_keys_valuetypes, **kwargs)
# 		pass
# 	pass


class SlFilm(RestrictedDictKeyValuetypes):
    def __init__(
        self, seq=(), boxofficemojo_data={}, imdb_data={}, raw_data={}, **kwargs
    ):
        # parsed_data=self.parse_data(import)
        # self.imdb_data=parsed_data
        # self.update({k:v for k,v in parsed_data.items() if k in self.allowed_keys})
        # return self
        pass

        super().__init__(
            [
                ("mojo_id", str),
                ("imdb_id", str),
                # box office mojo info
                ("boxofficemojo_data", str),
                ("title", str),
                ("release_date", date),
                ("mpaa_rating", str),
                ("domestic_total_gross", int),
                ("distributor", str),
                # imdb info
                ("imdb_data", str),  # json string with all the imdb info
                ("actors", list),
                ("poster_url", str),
                ("genre", list),
                ("director", str),
                ("writer", list),
                ("plot", str),
                ("runtime", int),
                ("website", str),
                ("production_budget", int),
                ("rating_metacritic", str),
                ("rating_rottentomatoes", str),
                ("rating_imdb", str),
                ("rottetomatoes_id", str),  #
                # score info
                # ("boxofficefantasy_score", int),
                ("season_id", str),
                # youtube
                ("youtube_id", str),
            ],
            seq=seq,
            **kwargs,
        )
        if imdb_data:
            self.import_data(imdb_data)
        if boxofficemojo_data:
            self.import_boxofficemojo_data(boxofficemojo_data)
        if raw_data:
            self.import_data(raw_data)

    def __repr__(self):
        """Representation of the RestrictedDict"""
        return f"SlFilm({self.get('mojo_id')}, \"{self.get('title')}\")"

    def import_imdb_data(self, imdb_data):
        self._imdb_data_raw = imdb_data
        self.import_data(imdb_data, key="imdb_data")
        return self

    def import_boxofficemojo_data(self, boxofficemojo_data):
        self._boxofficemojo_data_raw = boxofficemojo_data
        self.import_data(boxofficemojo_data, key="boxofficemojo_data")
        return self

    def import_data(self, data, key=[]):
        parsed_data = parse_data(data)
        if key:
            self[key] = json.dumps(parsed_data, sort_keys=True, default=str)
        self.update({k: v for k, v in parsed_data.items() if k in self.allowed_keys})
        return self


class SlTeam(RestrictedDictKeyValuetypes):
    def __init__(self, seq=(), **kwargs):
        super().__init__(
            [
                ("team_uid", str),
                ("team_id", str),
                ("team_name", str),
                ("owner_id", str),
                ("season_id", str),
            ],
            seq=seq,
            **kwargs,
        )

    def __repr__(self):
        """Representation of the RestrictedDict"""
        return f"SlFilm({self.get('team_id')}, \"{self.get('team_name')}\")"


class SlDraft(RestrictedDictKeyValuetypes):
    def __init__(self, seq=(), **kwargs):
        super().__init__(
            [
                ("season_id", str),
                ("mojo_id", str),
                ("purchase_price", int),
                ("owner_id", str),
            ],
            seq=seq,
            **kwargs,
        )

    def __repr__(self):
        """Representation of the RestrictedDict"""
        return f"SlDraft({self.get('mojo_id')})"


class SlOwner(RestrictedDictKeyValuetypes):
    def __init__(self, seq=(), **kwargs):
        super().__init__(
            [("owner_id", str), ("owner_name", str), ("owner_emailaddress", str)],
            seq=seq,
            **kwargs,
        )

    def __repr__(self):
        """Representation of the RestrictedDict"""
        return f"SlOwner({self.get('owner_id')}, \"{self.get('owner_name')}\")"


class SlSeason(RestrictedDictKeyValuetypes):
    def __init__(self, seq=(), **kwargs):
        super().__init__(
            [("name", str), ("season_id", str), ("season", str), ("year", str)],
            seq=seq,
            **kwargs,
        )

    def __repr__(self):
        """Representation of the RestrictedDict"""
        return f"SlSeason({self.get('season_id')})"


class SlLeague(RestrictedDictKeyValuetypes):
    def __init__(self, seq=(), **kwargs):
        super().__init__(
            [
                ("teams", list),
                ("films", list),
                ("drafts", list),
                ("seasons", list),
                ("owners", list),
            ],
            seq=seq,
            **kwargs,
        )

    def __repr__(self):
        """Representation of the RestrictedDict"""
        return f"SlLeague"

    def __setitem__(self, key, value):
        if key == "teams":
            value = [SlTeam(u) for u in value]

        if key == "films":
            value = [SlFilm(raw_data=u) for u in value]

        if key == "drafts":
            value = [SlDraft(u) for u in value]

        if key == "seasons":
            value = [SlSeason(u) for u in value]

        if key == "owners":
            value = [SlOwner(u) for u in value]

        super().__setitem__(key, value)

        # def __iter__(self):
        # 	for key in ["films", "teams", 'drafts', 'owners', 'seasons']:
        # 		yield key, getattr(self, key)
