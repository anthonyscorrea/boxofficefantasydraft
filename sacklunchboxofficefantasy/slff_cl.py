#!/usr/bin/env python
#
# import modules used here -- sys is a very standard one
# coding=utf-8
import sys

sys.path.insert(0, "..")
import sys, argparse, logging
from time import sleep
import slack_blockkit as sbk
from slack_blockkit import Slack
import random
from operator import itemgetter
from functools import partial
from consolemenu import *
from consolemenu.items import *
import csv
from slff_models import SlFilm
from operator import itemgetter
import os

import yaml

ENABLE_SLACK = os.getenv("ENABLE_SLACK")=="True"
DRAFT_URL = os.getenv("DRAFT_URL")
STATUS_URL = os.getenv("STATUS_URL")

print(sys.path)


def timer(
    seconds, seconds_elapsed_funcs={}, seconds_remaining_funcs={}, tick_duration=1
):
    seconds_remaining = seconds
    seconds_elapsed = 0
    while seconds_remaining > -1:
        if seconds_elapsed_funcs.get(seconds_elapsed):
            if isinstance(seconds_elapsed_funcs[seconds_elapsed], list):
                for f in seconds_elapsed_funcs[seconds_elapsed]:
                    f()
            else:
                seconds_elapsed_funcs[seconds_elapsed]()
        if seconds_remaining_funcs.get(seconds_remaining):
            if isinstance(seconds_remaining_funcs[seconds_remaining], list):
                for f in seconds_remaining_funcs:
                    f()
            else:
                seconds_remaining_funcs[seconds_remaining]()

        seconds_elapsed += 1
        seconds_remaining -= 1
        sleep(1)

    pass

def remaining_budgets_block (draft_manager):
	teams=draft_manager.teams_with_budget
	section=sbk.Section(text='*Remaining Budgets:*')
	fields = [sbk.Field(f"*{team['owner_name']}:* ${team['budget']}M") for team in teams]
	blocks=[sbk.Divider(),section, sbk.SectionWithFields(fields=fields), sbk.Divider()]
	return blocks

def team_films_block(draft_manager):
    teams = draft_manager.teams
    section = sbk.Section(text="*Teams:*")

    # fields = [sbk.Field(f"*{team['owner_name']}:* " + ', '.join(["{title} (${purchase_price}M)".format(**film) for film in team['films']])) for team in teams.values()]
    def divide_chunks(l, n):
        # looping till length l
        for i in range(0, len(l), n):
            yield l[i : i + n]

    fields = [
        sbk.Field(
            f"*{team['owner_name']} (${draft_manager.get_team_budget(team['owner_id'])}M):* "
            + ", ".join(
                [
                    "{title} (${purchase_price}M)".format(**film)
                    for film in team["films"]
                ]
            )
        )
        for team in draft_manager.teams_with_films
    ]
    blocks = [
        sbk.Divider(),
        section,
        *[
            sbk.SectionWithFields(fields=fields_subset)
            for fields_subset in divide_chunks(fields, 10)
        ],
        sbk.Divider(),
    ]
    return blocks


def films_block(films, title=None):
    if title:
        section = sbk.Section(text=title)
    fields = [sbk.Field(film["title"]) for film in films]

    def divide_chunks(l, n):
        # looping till length l
        for i in range(0, len(l), n):
            yield l[i : i + n]

    blocks = [
        section,
        *[
            sbk.SectionWithFields(fields=fields_subset)
            for fields_subset in divide_chunks(fields, 10)
        ],
    ]
    # for subset in divide_chunks(draft_manager.remaining_films, 10):
    # blocks = divide_chunks(blocks, 10)
    return blocks


def send_team_films(draft_manager, **kwargs):
    blocks = team_films_block(draft_manager)
    say(blocks=blocks, service=draft_manager.status_service)


def send_remaining_budgets(draft_manager, **kwargs):
    blocks = remaining_budgets_block(draft_manager)
    say(blocks=blocks, service=draft_manager.status_service)


def send_remaining_films(draft_manager, **kwargs):
    blocks = films_block(draft_manager.remaining_films, title="*Remaining Films:*")
    say(blocks=blocks, service=draft_manager.status_service)


def send_drafted_films(draft_manager, **kwargs):
    blocks = drafted_films_block(draft_manager, title="*Draft Films*")
    say(blocks=blocks, service=draft_manager.status_service)


def draftpick_to_slack(film, service, blocks=[], blocks_suffix=[]):
    d = {k: (", ".join(v) if isinstance(v, list) else v) for k, v in dict(film).items()}

    # if all([k in d.keys() for k in ['owner_id', 'team_name']]):
    main_text = []
    if d.get("title"):
        main_text.append("*{title}*")
    if d.get("release_date"):
        main_text.append("{release_date:%B %-m}\n")
    if d.get("plot"):
        main_text.append("{plot}\n")
    if d.get("genre"):
        main_text.append("{genre}")
    if d.get("actors"):
        main_text.append("_Starring {actors}_")
    if d.get("actors"):
        main_text.append(
            "<http://youtu.be/{youtube_id}|Trailer>, <https://www.imdb.com/title/{imdb_id}|IMDB>"
        )
    main_text = "\n".join(main_text).format(**d)

    blocks.append(sbk.Divider())

    if film.get("poster_url"):
        blocks.append(
            sbk.SectionWithImage(image_url=film["poster_url"], section_text=main_text)
        )
    else:
        blocks.append(sbk.Section(main_text))

    blocks.append(sbk.Divider())

    blocks += blocks_suffix

    r = service.post(blocks=blocks, text="New draft starting!")
    return r


def choose_from_menu(menu_items, message):
    choice_i = -1
    while not 1 < choice_i <= len(menu_items):
        while not chosen:
            try:
                choice_i = int(
                    input(
                        message
                        + "\n".join(
                            [
                                message,
                                *[
                                    "{int_id:>6}) {owner_name}".format(**menu_items)
                                    for menu_item in menu_items.values()
                                ],
                                "Enter number: ",
                            ]
                        )
                    )
                )
                winner = {
                    i: menu_items for i, menu_items in enumerate(menu_items.values())
                }.get(choice_i)
                winning_bid = int(input("Draft amount: "))
                if (
                    input(
                        f"Accept winner of {winner['owner_name']} for ${winning_bid}M? y/n: "
                    )
                    == "y"
                ):
                    chosen = True
            except:
                pass
    return (winner, winning_bid)


# Gather our code in a main() function


def say(m=None, type=None, service=None, **kwargs):
    if not service:
        raise SyntaxError('Function Requires "service" Argrument')
    if type == "draftpick":
        if ENABLE_SLACK:
            draftpick_to_slack(film=kwargs.get("film"), blocks=[], service=service)
        # print (f"New draft for \"{film['title']}\"")
        print(kwargs.get("film")["title"])
        if kwargs:
            print("\t\t" + str(kwargs))
    else:
        if ENABLE_SLACK:
            service.post(m, **kwargs)
        if m:
            print(m)
        if kwargs:
            print("\t\t" + str(kwargs))


def determine_winner(teams, film):
    winner_i = -1
    while not 1 <= winner_i <= len(teams):
        try:
            winner_i = int(
                input(
                    f"Who wins the bidding for {film['title']}?\n"
                    + "\n".join(
                        ["{int_id:>6}) {owner_name}".format(**team) for team in teams]
                    )
                    + "\nEnter number: "
                )
            )
            winner = {team["int_id"]: team for team in teams}.get(winner_i)
            winning_bid = int(input("Draft amount: "))
            are_you_sure = input(
                f"Are you sure ({winner['owner_name']}, ${winning_bid}M)? (y)es/(n)o/(r)edo: "
            )
            if are_you_sure == "n":
                winner_i = -1
            elif are_you_sure == "r":
                return (None, None)
            if winner["budget"] < winning_bid:
                print("Insufficient budget!")
                winner_i = -1
        except Exception as e:
            raise e
            pass
    return winner, winning_bid


class DraftManager:
    def __init__(
        self,
        teams,
        films,
        owners,
        service,
        status_service,
        seasons=None,
        inprogress_fname="temp.yml",
        budget=100,
        prebid_time=None,
        bid_time=None,
        **kwargs,
    ):
        self.prebid_time = prebid_time
        self.bid_time = bid_time
        self.inprogress_fname = inprogress_fname
        self.service = service
        self.status_service = status_service
        self.starting_budget = budget

        self._load(teams=teams, films=films, owners=owners, seasons=seasons, drafts=[])
        if kwargs["load_from_inprogress"]:
            self.load_from_inprogress(inprogress_fname)

    def _load(self, teams, films, owners, drafts, seasons=None):
        self.teams = {team["team_uid"]: team for team in teams}
        self.films = {film["mojo_id"]: film for film in films}
        self.owners = {owner["owner_id"]: owner for owner in owners}
        self.teams = {team["owner_id"]: team for team in teams}
        self.drafts = drafts

        for i, team in enumerate(self.teams.values(), start=1):
            team.update(self.owners.get(team["owner_id"]))
            team["int_id"] = i

    def load_from_inprogress(self, inprogress_fname):
        with open(inprogress_fname, "r") as f:
            y = yaml.load(f)
            self._load(
                teams=y["teams"],
                films=y["films"],
                owners=y["owners"],
                drafts=y["drafts"],
            )

    def reset_draft(self):
        self.drafts = []

    @property
    def remaining_films(self):
        return [
            film
            for film in self.films.values()
            if film["mojo_id"]
            not in [drafted_film["mojo_id"] for drafted_film in self.drafts]
        ]

    @property
    def drafted_films(self):
        return [
            film
            for film in self.films.values()
            if film["mojo_id"]
            in [drafted_film["mojo_id"] for drafted_film in self.drafts]
        ]

    def manual_draft_pick(self):
        l_titles = [film["title"] for film in self.films.values()]
        l_films = [film for film in self.films.values()]

        selection = SelectionMenu.get_selection(l_titles)
        if selection == len(l_titles):
            return
        self.draft_movie(l_films[selection])

    def random_draft_movie(self, **kwargs):
        mojo_id = random.choice([film["mojo_id"] for film in self.remaining_films])
        film = self.films[mojo_id]
        self.draft_movie(film)

    def draft_movie(self, film, **kwargs):
        prebid_time = kwargs.get("prebid_time", self.prebid_time)
        bid_time = kwargs.get("bid_time", self.bid_time)

        winner = None
        while not winner:
            say(
                "The next film up for draft:",
                text="Incoming draft nominee",
                service=self.service,
            )
            say(film=film, type="draftpick", service=self.service)
            say(f"{prebid_time} seconds until bidding begins", service=self.service)
            sleep(prebid_time)
            # say(f"*Start bidding!* (You will have {time_to_bid} seconds to bid)")

            halfway = int(bid_time / 2)

            timer(
                bid_time,
                seconds_elapsed_funcs={
                    0: partial(
                        say,
                        f"*Start bidding!* ({bid_time} seconds to bid)",
                        text="Bidding starting",
                        service=self.service,
                    ),
                    halfway: partial(
                        say,
                        f"*Halfway* ({halfway} seconds left to bid)",
                        text="Halfway",
                        service=self.service,
                    ),
                },
                seconds_remaining_funcs={
                    # 3: partial(say, "3"),
                    4: partial(say, "Going once!", service=self.service),
                    2: partial(say, "Going twice!", service=self.service),
                    0: partial(
                        say, "*Sold!*", text="Bidding closed", service=self.service
                    ),
                },
            )

            winner, winning_bid = determine_winner(
                teams=[team for team in self.teams_with_budget if team["budget"]],
                film=film,
            )
        say(
            f"*{winner['owner_name']}* wins \"{film['title']}\" with bid of ${winning_bid}M",
            blocks=[sbk.Divider()],
            blocks_prefix=[sbk.Divider()],
            service=self.service,
        )

        say(f"Head to #draftstatusboard for more info", service=self.service)

        self.drafts.append(
            dict(
                mojo_id=film["mojo_id"],
                purchase_price=winning_bid,
                team_id=winner["team_id"],
                owner_id=winner["owner_id"],
            )
        )

        # statusboard update
        send_remaining_films(self)
        send_team_films(self)
        say(f"Head back to #draft", service=self.status_service)

        with open(self.inprogress_fname, "w") as f:
            yaml.dump(self.asdict(), f)

            # with open('output/inprogress_remainingfilms.csv', 'w') as f:
            # w=csv.DictWriter(f, fieldnames=['title', 'genre', 'actors', 'release_date'], extrasaction='ignore')
            # w.writeheader()
            # w.writerows(self.remaining_films)

            # with open('output/inprogress_draftedfilms.csv', 'wb') as f:
            # 	w=csv.DictWriter(f, fieldnames=['title', 'purchase_price', 'drafter'], extrasaction='ignore')
            # 	w.writeheader()
            # w.writerows(self.drafted_films)

    def get_team_budget(self, owner_id):
        r = self.starting_budget - sum(
            [
                draft["purchase_price"]
                for draft in self.drafts
                if draft["owner_id"] == owner_id
            ]
        )
        return r

    @property
    def teams_with_budget(self):
        return [
            dict(**team, budget=self.get_team_budget(team["owner_id"]))
            for team in self.teams.values()
        ]

    @property
    def teams_with_films(self):
        return [
            dict(
                **team,
                budget=self.get_team_budget(team["owner_id"]),
                films=self.get_team_films(team["owner_id"]),
                drafts=self.get_team_drafts(team["owner_id"]),
            )
            for team in self.teams.values()
        ]

    def get_team_films(self, owner_id):
        return [
            dict(**self.films[draft["mojo_id"]], purchase_price=draft["purchase_price"])
            for draft in self.drafts
            if draft["owner_id"] == owner_id
        ]

    def get_team_drafts(self, owner_id):
        return [draft for draft in self.drafts if draft["owner_id"] == owner_id]

    def status(self):
        print(f"Films remaining ({len(self.remaining_films)}):")
        for film in self.remaining_films:
            print(f"\t{film['title']}")
        print(f"Films drafted ({len(self.drafted_films)}):")
        for film in self.drafted_films:
            print(f"\t{film['title']}")
        print("Teams:")
        for team in self.teams.values():
            print(f"\t{team['owner_id']}: ${self.get_team_budget(team['owner_id'])}")

    def asdict(self):
        return dict(
            teams=list(self.teams.values()),
            drafts=self.drafts,
            owners=list(self.owners.values()),
            films=list(self.films.values()),
        )

    def print_yt_list(self):
        print(
            "http://www.youtube.com/watch_videos?video_ids={}".format(
                ",".join([film["youtube_id"] for film in self.films.values()])
            )
        )


def main(args, loglevel):
    logging.basicConfig(format="%(levelname)s: %(message)s", level=loglevel)

    if args.test_arg:
        print("argument received!!")

    with open(
        "/Users/asc/Projects/boxofficefantasydraft/data/input/2019.yml", "r"
    ) as f:
        y = yaml.load(f)

    inprogress_fname = args.inprogress_file

    try:
        inprogress_f = open(inprogress_fname, "r")
    except FileNotFoundError:
        inprogress_f = open(inprogress_fname, "w")

    inprogress_f.close()

    slack = Slack(
        hook_url=args.draft_url,
        channel_url=DRAFT_URL,
    )
    slack_statusboard = Slack(
        hook_url=args.status_url,
        channel_url=STATUS_URL,
    )

    # premenu = ConsoleMenu("Welcome to the Sack Lunch Fantasy Box Office Draft!")
    #
    load_from_inprogress = args.load_inprogress

    draft_manager = DraftManager(
        **y,
        budget=args.budget,
        prebid_time=args.prebid_time,
        bid_time=args.bid_time,
        inprogress_fname=args.inprogress_file,
        service=slack,
        status_service=slack_statusboard,
        load_from_inprogress=load_from_inprogress,
    )

    menu = ConsoleMenu("Sack Lunch Movie Draft", "Select option:")

    submenu = ConsoleMenu("This is the submenu")

    subfunctionitems = [
        FunctionItem(f"Reset Draft", partial(draft_manager.reset_draft)),
        FunctionItem(
            f"Load from inprogress.yml",
            partial(draft_manager.load_from_inprogress, inprogress_fname),
        ),
    ]

    for subfunctionitem in subfunctionitems:
        submenu.append_item(subfunctionitem)

        # FunctionItem( )
    function_items = []
    function_items = [
        FunctionItem(
            f"Send random movie for draft", partial(draft_manager.random_draft_movie)
        ),
        FunctionItem(
            f"Send manual movie for draft", partial(draft_manager.manual_draft_pick)
        ),
        FunctionItem(f"Draft status", draft_manager.status),
        FunctionItem(
            f"Send Remaining Budgets", partial(send_remaining_budgets, draft_manager)
        ),
        FunctionItem(
            f"Send Remaining Films", partial(send_remaining_films, draft_manager)
        ),
        FunctionItem(
            f"Send Remaining Team Films", partial(send_team_films, draft_manager)
        ),
        # FunctionItem(f"Load From inprogress", partial(draft_manager.load_from_inprogress, inprogress_fname)),
        FunctionItem(f"Print youtube playlist", partial(draft_manager.print_yt_list)),
        SubmenuItem(f"Draft Options", submenu, menu=menu)
        # FunctionItem(f"Send Drafted Films", partial(send_drafted_films, draft_manager))
    ]

    for function_item in function_items:
        menu.append_item(function_item)

    menu.show()
    pass


# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Does a thing to some stuff.",
        epilog="As an alternative to the commandline, params can be placed in a file, one per line, and specified on the commandline like '%(prog)s @params.conf'.",
        fromfile_prefix_chars="@",
    )
    # parser.add_argument("draft_file",help="pass ARG to the program",metavar="ARG",required=False)
    parser.add_argument(
        "-t" "," "--teams",
        help="YAML file to list of teams for draft",
        nargs=1,
        type=str,  # any type/callable can be used here
        default="input/teams.yml",
    )

    parser.add_argument(
        "--inprogress-file",
        type=str,  # any type/callable can be used here
        default="/Users/asc/Projects/boxofficefantasydraft/data/output/inprogress.yml",
    )

    parser.add_argument(
        "--draft-url",
        type=str,
        default=DRAFT_URL,
    )
    parser.add_argument(
        "--status-url",
        type=str,
        default=STATUS_URL,
    )

    parser.add_argument("--bid-time", type=int, default=60)

    parser.add_argument("--prebid-time", type=int, default=5)

    parser.add_argument("--budget", type=int, default=100)

    parser.add_argument("--load-inprogress", default=False, action="store_true")

    parser.add_argument("--test-arg", default=False, action="store_true")

    parser.add_argument(
        "-v", "--verbose", help="increase output verbosity", action="store_true"
    )
    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    main(args, loglevel)
