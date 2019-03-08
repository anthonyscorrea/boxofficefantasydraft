__author__ = "asc"

from bs4 import BeautifulSoup
from urllib import request, parse
import locale
import datetime
import logging
import re
from dateutil.parser import parse as dateparse
import omdb
from time import sleep
from sacklunchboxofficefantasy.slff_models import SlFilm

import os, ssl

if not os.environ.get("PYTHONHTTPSVERIFY", "") and getattr(
    ssl, "_create_unverified_context", None
):
    ssl._create_default_https_context = ssl._create_unverified_context

OMDBAPIKEY = os.getenv("OMDBAPIKEY")
# IMDB_URL =

module_logger = logging.getLogger("boxofficefantasydraft.boxofficefantasy")
logging.basicConfig(level=logging.INFO)
module_logger = logging

omdb_client = omdb.OMDBClient(apikey=OMDBAPIKEY)


def generateid(title):
    return (
        "genid_"
        + title.translate(
            str.maketrans(
                "", "", "".join(c for c in map(chr, range(256)) if not c.isalpha())
            )
        ).lower()
    )


def get_boxofficemojo_data(mojo_id, full=True):
    module_logger.debug("Getting Box Office Mojo data for {}".format(mojo_id))
    movie_information = {}
    if full:
        url = f"http://www.boxofficemojo.com/movies/?id={mojo_id}.htm"

        try:
            res = request.urlopen(url)
            soup = BeautifulSoup(res, "html5lib")
            tables = soup.find_all("table")

            movie_information = {
                l.text.split(": ")[0]: l.text.split(": ")[1]
                for l in tables[5].find_all("td")
            }
            movie_information["title"] = soup.title.text

        except Exception as e:
            module_logger.exception(
                "Exception in getting Box Office Mojo data for url {}".format(url)
            )

    else:
        try:
            url = (
                f"http://www.boxofficemojo.com/data/js/moviegross.php?id={mojo_id}.htm"
            )
            documentwrite_java = re.compile(r"document\.write\(\'(.*)\'\)\;")
            page = request.urlopen(url).read().decode()
            page = documentwrite_java.sub(r"\1", page)
            soup = BeautifulSoup(page, "html5lib")
            rows = [i.text for i in soup.find_all("table")[0].find_all("tr")]
            movie_information["title"] = rows[0]
            movie_information["domestic_total_gross"] = rows[1]

        except Exception as e:
            module_logger.exception(
                "Exception in getting Box Office Mojo data for url {}".format(url)
            )

    movie_information["mojo_id"] = mojo_id
    return movie_information


def get_imdb_data(imdb_id="", title="", year=datetime.datetime.today().year, **kwargs):
    module_logger.debug(f"Searching for IMDB {title} ({year})")
    try:
        imdb_info = {}
        if imdb_id:
            imdb_info = omdb_client.imdbid(imdb_id, **kwargs)
        elif title:
            imdb_info = omdb_client.title(title, year=year, **kwargs)
        else:
            imdb_info = omdb_client.search(**kwargs)
    except:
        module_logger.debug(f"No IMDB ID found for {film['title']} ({kwargs}")
    return imdb_info


def populatefromdraft(year, season):
    league = League(
        draftf=f"draft{year}.csv",
        teamf=f"teams{year}.csv",
        season=season,
        year=f"{year}",
    )
    connectioninfo = (
        "home.ascorrea.com",
        "moviefantasy_wp",
        "moviefantasy_wpdb",
        "moviefantasy_wordpress",
    )
    db = Db(connectioninfo)

    tablenames = {
        "imdb": "ASC_boxofficefantasy_imdb",
        "mojo": "ASC_boxofficefantasy_mojo",
        "draft": "ASC_boxofficefantasy_draft",
        "teams": "ASC_boxofficefantasy_teams",
        "score": "ASC_boxofficefantasy_score",
    }

    mojoIDs = [i["mojoID"] for i in league.draft]

    for team in league.teams:
        print(team.teamdefinition)
        # db.addrow(tablenames['teams'], team.teamdefinition)
        pass

    for pick in league.draft:
        print(pick)
        # db.updaterow(tablenames['draft'],pick, "mojoid=\"%s\""%(pick['mojoID']))
        # db.addrow(tablenames['draft'],pick)
        db.addrow(tablenames["score"], {"mojoID": pick["mojoID"], "domesticgross": 0})
        pass

    for f in league.films:
        # imdbdb.addrow(tablenames['imdb'],f.imdb_info)
        # mojodb.addrow(tablenames['mojo']f.boxofficemojo_info)
        pass


def legacy_updatemovieinfo(year, season):
    league = League(
        draftf="draft{0}.csv".format(year),
        teamf="teams{0}.csv".format(year),
        season=season,
        year="{0}".format(year),
    )
    connectioninfo = (
        "home.ascorrea.com",
        "moviefantasy_wp",
        "moviefantasy_wpdb",
        "moviefantasy_wordpress",
    )
    db = Db(connectioninfo)

    tablenames = {
        "imdb": "ASC_boxofficefantasy_imdb",
        "mojo": "ASC_boxofficefantasy_mojo",
        "draft": "ASC_boxofficefantasy_draft",
        "teams": "ASC_boxofficefantasy_teams",
        "score": "ASC_boxofficefantasy_score",
    }

    mojoIDs = [i["mojoID"] for i in league.draft]

    for team in league.teams:
        print(team.teamdefinition)
        # db.addrow(tablenames['teams'], team.teamdefinition)
        pass

    for pick in league.draft:
        print(pick)
        # db.updaterow(tablenames['draft'],pick, "mojoid=\"%s\""%(pick['mojoID']))
        # db.addrow(tablenames['draft'],pick)
        # db.addrow(tablenames['score'],
        #         {'mojoID':pick['mojoID'],'domesticgross':0},
        #         )
        pass

    for f in league.films:
        imdbdb.updaterow(tablenames["imdb"], f.imdb_info, 'mojoid="%s"' % (f.mojo_id))

        mojodb.udpaterow(
            tablenames["mojo"], f.boxofficemojo_info, 'mojoid="%s"' % (f.mojo_id)
        )
        pass


def get_score(mojo_id):
    movie_information = get_boxofficemojo_data(mojo_id, full=False)
    movie_information = SlFilm.parse_data(movie_information)
    return movie_information.get("domestic_total_gross")


def get_boxofficemojo_ids_from_pages(
    year=datetime.datetime.today().year, date_weeks=[]
):
    if year:
        # This will only work for future years, not years in the past
        urf = "https://www.boxofficemojo.com/schedule/?view=bydate&release=theatrical&yr={year}&p=.htm"
        urls = [urf.format(year=year)]
    if date_weeks:
        # this should work for years, weeks in the past
        """
		dateweeks = [("2018-04-06", 4),
		("2018-05-04", 4),
		("2018-06-01", 5),
		("2018-07-06", 4),
		("2018-08-03", 5),
		("2018-09-07", 4),
		("2018-10-05", 4)]
		"""
        urlf = "http://www.boxofficemojo.com/schedule/?view=&release=&date={}&showweeks={}&p=.htm"
        urls = [urlf.format(date, weeks) for date, weeks in date_weeks]

    ids = []

    for url in urls:
        webpage = request.urlopen(url)
        soup = BeautifulSoup(webpage.read(), "html5lib")

        films = [
            dict(
                mojo_id=re.sub(r"\/movies\/\?id=(.*)\.htm", r"\1", link.get("href")),
                title=re.sub(r" \([0-9]{4}\)", r"", str(link.string)),
            )
            for link in soup.find_all("a")
            if "?id=" in link.get("href")
        ]

        for link in soup.find_all("a", href=True):
            l = link["href"]
            if "/movies/?id=" in l:
                ids.append(l.replace("/movies/?id=", "").replace(".htm", ""))
    return films


def new_draft(mojo_ids=None):
    films = []
    if not mojo_ids:
        mojo_ids = get_boxofficemojo_ids_from_pages(2019)

    for mojo_id in mojo_ids:
        boxofficemojo_data = get_boxofficemojo_data(mojo_id)
        f = SlFilm()
        f.import_boxofficemojo_data(boxofficemojo_data)
        films.append(f)

    return films


def filter_draft(films, date_start, date_end, distributors=[], imdb_id=True):
    if not distributors:
        distributors = [
            "Warner Bros. (New Line)",
            "Warner Bros.",
            "Sony / Columbia",
            "Universal",
            "Buena Vista",
            "Paramount",
            "Fox",
            "Lionsgate",
        ]
    if isinstance(date_start, str):
        date_start = dateparse(date_start)
    if isinstance(date_end, str):
        date_end = dateparse(date_end)

    r = [
        film
        for film in films
        if date_start <= film["release_date"] <= date_end
        and film["distributor"] in distributors
    ]
    return r


def output_xl(
    films, output_fname=f"output/{datetime.datetime.today().year}draft.xlsx", keys=[]
):
    import xlsxwriter

    workbook = xlsxwriter.Workbook(output_fname)
    worksheet = workbook.add_worksheet("draftlist")

    # Iterate over the data and write it out row by row.
    mojo_urlf = "http://www.boxofficemojo.com/movies/?id={}.htm"
    imdb_urlf = "https://www.imdb.com/title/{}"
    youtube_urlf = "http://youtu.be/{}"

    if not keys:
        keys = ["title", "genre", "actors"]
    col_names = [k.capitalize().replace("_", " ") for k in keys] + [
        "Release Date",
        "IMDB",
        "Trailer",
        "Box Office Mojo",
        "Website",
        "mojo_id",
    ]

    for col, c in enumerate(col_names):
        worksheet.write(0, col, c)

    for row, film in enumerate(films, start=1):
        for col, k in enumerate(keys):
            if isinstance(film.get(k), list):
                v = ", ".join(film.get(k))
            else:
                v = film.get(k)
            worksheet.write(row, col, v)

        col += 1
        k = "release_date"
        if film.get(k):
            worksheet.write_string(row, col, film.get(k))

        col += 1
        k = "imdb_id"
        worksheet.write_url(
            row,
            col,
            imdb_urlf.format(film["imdb_id"]),
            # string='IMDB'
        )

        col += 1
        worksheet.write_url(
            row,
            col,
            youtube_urlf.format(film["youtube_id"]),
            # string='Trailer'
        )

        col += 1
        worksheet.write_url(
            row,
            col,
            mojo_urlf.format(film["mojo_id"]),
            # string='Box Office Mojo'
        )

        col += 1
        k = "website"
        if film.get(k):
            worksheet.write_url(
                row,
                col,
                url=film.get(k),
                # string='Website'
            )

    workbook.close()


def import_new():
    # new_films=get_boxofficemojo_ids_by_year(2019)
    # with open("2019.yaml", 'w') as f: yaml.dump(films,f, default_flow_style=False)
    import yaml
    import pickle

    # with open('2019slfilms.yaml') as f: films = yaml.load(f)

    # import xlsxwriter
    # f_name = 'out.xlsx'
    # workbook = xlsxwriter.Workbook(f_name)
    # # films_filtered=filter_draft(films, date_start='2019-03-09', date_end='2019-09-06')
    import csv

    with open("input/2019draftlist.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        films = [SlFilm(row) for row in reader]

    for i, film in enumerate(films):
        print(f"{i+1}/{len(films)}")
        imdb_data = get_imdb_data(imdb_id=film["imdb_id"])
        film.import_imdb_data(imdb_data)
        boxofficemojo_data = get_boxofficemojo_data(mojo_id=film["mojo_id"])
        film.import_boxofficemojo_data(boxofficemojo_data)

    with open("output/2019films.yaml", "w") as f:
        yaml.dump([dict(film) for film in films], f)

        #
        # output_xl(films)

        # print()


pass
