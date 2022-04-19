"""Miscellaneous utility functions that get data from the Clash Royale API."""

import datetime
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple, Union

import requests

# Config
from config.config import PRIMARY_CLAN_TAG
from config.credentials import CLASH_API_KEY

# Utils
import utils.bot_utils as bot_utils
import utils.db_utils as db_utils
from utils.util_types import ClashData, Participant


def get_active_members_in_clan(clan_tag: str=PRIMARY_CLAN_TAG) -> Dict[str, ClashData]:
    """Get a dictionary containing information about members currently in a clan.

    Args:
        clan_tag (optional): Clan to get members of. Defaults to primary clan.

    Returns:
        Dictionary of active members, or empty dict if API request fails. best_trophies, cards, found_cards, total_cards, and
            clan_name fields are all populated but do not contain actual data.
    """
    req = requests.get(url=f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/members",
                       headers={"Accept": "application/json", "authorization": f"Bearer {CLASH_API_KEY}"})

    if req.status_code != 200:
        return {}

    json_obj = req.json()
    active_members = {}

    for member in json_obj['items']:
        active_members[member['tag']] = {
            'player_tag': member['tag'],
            'player_name': member['name'],
            'role': member['role'],
            'exp_level': member['expLevel'],
            'trophies': member['trophies'],
            'best_trophies': -1,
            'cards': {},
            'found_cards': -1,
            'total_cards': -1,
            'clan_name': "",
            'clan_tag': clan_tag
        }

    return active_members


def get_river_race_participants(clan_tag: str=PRIMARY_CLAN_TAG) -> List[Participant]:
    """Get a list of participants in the current river race.

    Args:
        clan_tag (optional): Clan to get participants of. Defaults to primary clan.

    Returns:
        List of participants in specified clan's current river race, or empty list if API request fails.
    """
    req = requests.get(url=f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace",
                       headers={"Accept": "application/json", "authorization": f"Bearer {CLASH_API_KEY}"})

    if req.status_code != 200:
        return []

    json_obj = req.json()
    participants = json_obj["clan"]["participants"]

    for participant in participants:
        participant['player_tag'] = participant.pop('tag')
        participant['player_name'] = participant.pop('name')
        participant['repair_points'] = participant.pop('repairPoints')
        participant['boat_attacks'] = participant.pop('boatAttacks')
        participant['decks_used'] = participant.pop('decksUsed')
        participant['decks_used_today'] = participant.pop('decksUsedToday')

    return participants


def get_last_river_race_participants(clan_tag: str=PRIMARY_CLAN_TAG) -> List[Participant]:
    """Get participants in most recently completed river race.

    Args:
        clan_tag (optional): Clan to get participants of. Defaults to primary clan.

    Returns:
        List of participants in specified clan's most recently completed river race, or empty list if API request fails.
    """
    req = requests.get(url=f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/riverracelog?limit=1",
                       headers={"Accept": "application/json", "authorization": f"Bearer {CLASH_API_KEY}"})

    if req.status_code != 200:
        return []

    json_obj = req.json()
    clan_index = 0

    for clan in json_obj["items"][0]["standings"]:
        if clan["clan"]["tag"] == clan_tag:
            break

        clan_index += 1

    participants = json_obj["items"][0]["standings"][clan_index]["clan"]["participants"]

    for participant in participants:
        participant['player_tag'] = participant.pop('tag')
        participant['player_name'] = participant.pop('name')
        participant['repair_points'] = participant.pop('repairPoints')
        participant['boat_attacks'] = participant.pop('boatAttacks')
        participant['decks_used'] = participant.pop('decksUsed')
        participant['decks_used_today'] = participant.pop('decksUsedToday')

    return participants


def parse_player_tag(message: str) -> str:
    """Parses a string for a valid player tag.

    Args:
        message: String to parse.

    Returns:
        A valid player tag, or None if one can't be found.
    """
    found_pattern = re.search(r"(#[A-Z0-9]+)", message)
    if found_pattern is not None:
        return found_pattern.group(1)

    return None


def get_clash_data(message: str) -> Union[ClashData, None]:
    """Get a user's relevant Clash Royale information.

    Args:
        message: Message that should contain a valid player tag.

    Returns:
        A dictionary of relevant Clash Royale information, or None if an error occurs.
    """
    player_tag = parse_player_tag(message)

    if player_tag is None:
        return None

    req = requests.get(url=f"https://api.clashroyale.com/v1/players/%23{player_tag[1:]}",
                       headers={"Accept": "application/json", "authorization": f"Bearer {CLASH_API_KEY}"})

    if req.status_code != 200:
        return None

    json_obj = req.json()
    user_in_clan = 'clan' in json_obj

    clash_data: ClashData = {
        'player_tag': json_obj['tag'],
        'player_name': json_obj['name'],
        'role': json_obj.get('role', "None"),
        'exp_level': json_obj['expLevel'],
        'trophies': json_obj['trophies'],
        'best_trophies': json_obj['bestTrophies'],
        'cards': {i: 0 for i in range(1, 15)},
        'found_cards': 0,
        'total_cards': get_total_cards(),
        'clan_name': json_obj['clan']['name'] if user_in_clan else "None",
        'clan_tag': json_obj['clan']['tag'] if user_in_clan else "None"
    }

    for card in json_obj['cards']:
        card_level = 14 - (card['maxLevel'] - card['level'])
        clash_data['cards'][card_level] += 1
        clash_data['found_cards'] += 1

    return clash_data


# TODO: also return any active members that are not in participants.
def get_remaining_decks_today(clan_tag: str=PRIMARY_CLAN_TAG) -> List[Tuple[str, str, int]]:
    """Retrieve a list of players in a clan who have not used 4 war decks today.

    Args:
        clan_tag (optional): Clan to get deck usage info from. Defaults to primary clan.

    Returns:
        List of player names, player tags, and remaining decks of users in the specified clan that have not used 4 decks today.
    """
    participants = get_river_race_participants(clan_tag)
    active_members = get_active_members_in_clan(clan_tag)
    decks_remaining_list = []

    if len(active_members) == 0:
        return []

    for participant in participants:
        player_tag = participant['player_tag']
        remaining_decks = 4 - participant['decks_used_today']
        if (remaining_decks != 0) and (player_tag in active_members):
            decks_remaining_list.append((active_members[player_tag]['player_name'], participant['player_tag'], remaining_decks))

    decks_remaining_list.sort(key = lambda x : (x[2], x[0].lower()))
    return decks_remaining_list


def get_remaining_decks_today_dicts(clan_tag: str=PRIMARY_CLAN_TAG) -> Dict[str, Union[int, List[Tuple[str, int]]]]:
    """Retrieve a dict containing detailed information about deck usage today.

    Args:
        clan_tag(str, optional): Clan to get deck usage info from. Defaults to primary clan.

    Returns:
        dict: Detailed lists of specified clan's deck usage.
            {
                remaining_decks int:
                    Maximum number of decks that could still be used today.
                participants: int
                    Number of players who have used at least 1 deck today.
                active_members_with_no_decks_used: int
                    Number of players in the clan that have not used decks.
                active_members_with_remaining_decks: [(player_name, decks_remaining), ...]
                    Members in clan that could still battle.
                active_members_without_remaining_decks: List[(player_name, decks_remaining), ...]
                    Members in clan that have used 4 decks today.
                inactive_members_with_decks_used: [(player_name, decks_remaining), ...]
                    Members no longer in clan that battled today while in the clan.
                locked_out_active_members: [(player_name, decks_remaining), ...]
                    Members in clan that are locked out of battling today.
            }
    """
    active_members = get_active_members_in_clan(clan_tag)
    participants = get_river_race_participants(clan_tag)

    if len(participants) == 0 or len(active_members) == 0:
        return {}

    return_info = {
        'remaining_decks': 200,
        'participants': 0,
        'active_members_with_no_decks_used': 0,
        'active_members_with_remaining_decks': [],
        'active_members_without_remaining_decks': [],
        'inactive_members_with_decks_used': [],
        'locked_out_active_members': []
    }

    for participant in participants:
        if participant['decks_used_today'] > 0:
            return_info['remaining_decks'] -= participant['decks_used_today']
            return_info['participants'] += 1

    for participant in participants:
        if participant['player_tag'] in active_members:
            participant_name = active_members[participant['player_tag']]['player_name']
            if participant['decks_used_today'] == 4:
                return_info['active_members_without_remaining_decks'].append((participant_name, 0))
            elif participant['decks_used_today'] == 0:
                return_info['active_members_with_no_decks_used'] += 1
                if return_info['participants'] == 50:
                    return_info['locked_out_active_members'].append((participant_name, 4))
                else:
                    return_info['active_members_with_remaining_decks'].append((participant_name, 4))
            else:
                return_info['active_members_with_remaining_decks'].append((participant_name, (4 - participant['decks_used_today'])))
        elif participant['decks_used_today'] > 0:
            return_info['inactive_members_with_decks_used'].append((participant['player_name'],
                                                                    (4 - participant['decks_used_today'])))

    return_info['active_members_with_remaining_decks'].sort(key = lambda x : (x[1], x[0].lower()))
    return_info['active_members_without_remaining_decks'].sort(key = lambda x : (x[1], x[0].lower()))
    return_info['inactive_members_with_decks_used'].sort(key = lambda x : (x[1], x[0].lower()))
    return_info['locked_out_active_members'].sort(key = lambda x : (x[1], x[0].lower()))
    return return_info


def get_deck_usage_today(clan_tag: str=PRIMARY_CLAN_TAG, active_members: Dict[str, ClashData]=None) -> Dict[str, int]:
    """Get a list of players in a clan and how many decks each player used today.

    Args:
        clan_tag (optional): Clan to get deck usage info from. Defaults to primary clan.
        active_members (optional): Dictionary of active members. Defaults to retrieving active members in specified clan.

    Returns:
        Dictionary mapping player tags to their deck usage today.
    """
    participants = get_river_race_participants(clan_tag)

    if active_members is None:
        active_members = get_active_members_in_clan(clan_tag)
    else:
        active_members = active_members.copy()

    if (len(participants) == 0) or (len(active_members) == 0):
        return {}

    usage_list = {}

    for participant in participants:
        usage_list[participant['player_tag']] = participant['decks_used_today']
        active_members.pop(participant['player_tag'], None)

    for player_tag in active_members:
        usage_list[player_tag] = 0

    return usage_list


def get_user_decks_used_today(player_tag: str) -> int:
    """Return the number of decks used today by a specific player.

    Args:
        player_tag: Player tag of player to look up.

    Returns:
        Number of decks used today, or 0 if can't find relevant information.
    """
    req = requests.get(url=f"https://api.clashroyale.com/v1/players/%23{player_tag[1:]}",
                       headers={"Accept": "application/json", "authorization": f"Bearer {CLASH_API_KEY}"})

    if req.status_code != 200:
        return 0

    json_obj = req.json()
    clan_tag = None

    if "clan" in json_obj.keys():
        clan_tag = json_obj['clan']['tag']
    else:
        return 0

    participants = get_river_race_participants(clan_tag)

    if len(participants) == 0:
        return 0

    for participant in participants:
        if participant['player_tag'] != player_tag:
            continue

        return participant['decks_used_today']

    return 0


def get_top_medal_users(top_n: int=3, clan_tag: str=PRIMARY_CLAN_TAG) -> List[Tuple[str, int]]:
    """Get the top n users in a clan by medals. Can possible return more than n if players are tied for the same amount of medals.

    Args:
        top_n: Number of players to return. More than this may be returned though. Defaults to 3.
        clan_tag (optional): Clan to look for top players in. Defaults to primary clan.

    Returns:
        List of player names and their medals.
    """
    if db_utils.is_war_time():
        participants = get_river_race_participants(clan_tag)
    else:
        participants = get_last_river_race_participants(clan_tag)

    active_members = get_active_members_in_clan(clan_tag)

    if len(active_members) == 0:
        return []

    fame_list = [(active_members[participant['player_tag']]['player_name'], participant['fame'])
                 for participant in participants
                 if participant['player_tag'] in active_members]

    fame_list.sort(key = lambda x : x[1], reverse = True)

    if len(fame_list) <= top_n:
        return fame_list

    i = top_n - 1
    return_list = fame_list[:top_n]

    while (i + 1 < len(fame_list)) and (fame_list[i][1] == fame_list[i + 1][1]):
        return_list.append(fame_list[i + 1])
        i += 1

    return return_list


def get_hall_of_shame(threshold: int, clan_tag: str=PRIMARY_CLAN_TAG) -> List[Tuple[str, str, int]]:
    """Get a list of players below a specified medal count.

    Args:
        threshold: Look for players with medals below this threshold.
        clan_tag (optional): Clan to look for players below threshold in. Defaults to primary clan.

    Returns:
        List of player names and medals below specified threshold.
    """
    if db_utils.is_war_time():
        participants = get_river_race_participants(clan_tag)
    else:
        participants = get_last_river_race_participants(clan_tag)

    active_members = get_active_members_in_clan(clan_tag)
    hall_of_shame = []

    for participant in participants:
        if (participant['fame'] < threshold) and (participant['player_tag'] in active_members):
            hall_of_shame.append((active_members[participant['player_tag']]['player_name'],
                                  participant['player_tag'],
                                  participant['fame']))

    hall_of_shame.sort(key = lambda x : (x[2], x[0].lower()))
    return hall_of_shame


def get_clan_decks_remaining(clan_tag: str=PRIMARY_CLAN_TAG) -> List[Tuple[Tuple[str, str], int]]:
    """Get the number of available war decks remaining for all clans in a race with specified clan.

    Args:
        clan_tag (optional): Clan to check the race status of. Defaults to primary clan.

    Returns:
        List of ((clan tag, clan name), remaining decks) tuples.
    """
    req = requests.get(url=f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace",
                       headers={"Accept": "application/json", "authorization": f"Bearer {CLASH_API_KEY}"})

    if req.status_code != 200:
        return []

    json_obj = req.json()
    return_list = []

    for clan in json_obj["clans"]:
        decks_remaining = 200

        for participant in clan["participants"]:
            decks_remaining -= participant["decksUsedToday"]

        return_list.append(((clan["tag"], clan["name"]), decks_remaining))

    return_list.sort(key = lambda x : (x[1], x[0][1]))
    return return_list


def river_race_completed(clan_tag: str=PRIMARY_CLAN_TAG) -> bool:
    """Check if a clan has crossed the finish line. Always false during colosseum week.

    Args:
        clan_tag (optional): Clan to check completion status of. Defaults to primary clan.

    Returns:
        Whether the specified clan has accumulated 10,000 fame and crossed the finish line.
    """
    if db_utils.is_colosseum_week():
        return False

    req = requests.get(url=f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace",
                       headers={"Accept": "application/json", "authorization": f"Bearer {CLASH_API_KEY}"})

    if req.status_code != 200:
        return False

    json_obj = req.json()
    return json_obj["clan"]["fame"] >= 10000


# TODO: Use TypedDict
def calculate_player_win_rate(player_tag: str,
                              fame: int,
                              current_check_time: datetime.datetime,
                              last_check_time: datetime.datetime=None,
                              clan_tag: str=PRIMARY_CLAN_TAG) -> Dict[str, int]:
    """Look at a player's battle log and break down their performance in recent river race battles.

    Args:
        player_tag: Player to check match history of.
        fame: Total fame they've accumulated in the current river race.
        current_check_time: Time to set last_check_time after this check.
        last_check_time: Ignore battles before this time. If not provided, get from database.
        clan_tag: Only consider battles performed for this clan. Defaults to primary clan.

    Returns:
        Number of wins and losses in each river race battle type for the specified player.
            {
                "battle_wins": int,
                "battle_losses": int,
                "special_battle_wins": int,
                "special_battle_losses": int,
                "boat_attack_wins": int,
                "boat_attack_losses": int,
                "duel_match_wins": int,
                "duel_match_losses": int,
                "duel_series_wins": int,
                "duel_series_losses": int
            }
    """
    is_automated = False

    if last_check_time is None:
        is_automated = True
        prev_fame, last_check_time = db_utils.get_and_update_match_history_info(player_tag, fame, current_check_time)

        # This should only happen when an unregistered user is added but their information can't be retrieved from the API.
        if prev_fame is None:
            return {}

        # If no fame has been acquired since last check, no point in grabbing battlelog.
        if fame - prev_fame == 0:
            return {}

    req = requests.get(url=f"https://api.clashroyale.com/v1/players/%23{player_tag[1:]}/battlelog",
                       headers={"Accept": "application/json", "authorization": f"Bearer {CLASH_API_KEY}"})

    if req.status_code != 200:
        if is_automated:
            db_utils.set_users_last_check_time(player_tag, last_check_time)
        return {}

    battles = req.json()
    river_race_battle_list = []

    for battle in battles:
        battle_time = bot_utils.battletime_to_datetime(battle["battleTime"])
        if ((battle["type"].startswith("riverRace") or battle["type"] == "boatBattle")
                and last_check_time <= battle_time < current_check_time
                and battle["team"][0]["clan"]["tag"] == clan_tag):
            river_race_battle_list.append(battle)

    player_dict = {"player_tag": player_tag}
    player_dict["battle_wins"] = 0
    player_dict["battle_losses"] = 0
    player_dict["special_battle_wins"] = 0
    player_dict["special_battle_losses"] = 0
    player_dict["boat_attack_wins"] = 0
    player_dict["boat_attack_losses"] = 0
    player_dict["duel_match_wins"] = 0
    player_dict["duel_match_losses"] = 0
    player_dict["duel_series_wins"] = 0
    player_dict["duel_series_losses"] = 0

    for battle in river_race_battle_list:
        if battle["type"] == "riverRacePvP":
            if battle["gameMode"]["name"] == "CW_Battle_1v1":
                if battle["team"][0]["crowns"] > battle["opponent"][0]["crowns"]:
                    player_dict["battle_wins"] += 1
                else:
                    player_dict["battle_losses"] += 1
            else:
                if battle["team"][0]["crowns"] > battle["opponent"][0]["crowns"]:
                    player_dict["special_battle_wins"] += 1
                else:
                    player_dict["special_battle_losses"] += 1

        elif battle["type"] == "boatBattle":
            if battle["boatBattleSide"] == "defender":
                continue

            if battle["boatBattleWon"]:
                player_dict["boat_attack_wins"] += 1
            else:
                player_dict["boat_attack_losses"] += 1

        elif battle["type"].startswith("riverRaceDuel"):
            # During colosseum week, clan fame will exceed 10,000 so this ensures that strikes/reminders go out correctly.
            if is_automated and battle["type"] == "riverRaceDuelColosseum":
                db_utils.set_colosseum_week_status(True)

            # Determine duel series outcome by result of final game
            team_king_hit_points = battle["team"][0].get("kingTowerHitPoints")
            team_princess_list = battle["team"][0].get("princessTowersHitPoints")
            opponent_king_hit_points = battle["opponent"][0].get("kingTowerHitPoints")
            opponent_princess_list = battle["opponent"][0].get("princessTowersHitPoints")
            team_won = None

            if team_king_hit_points is None:
                team_won = False
            elif opponent_king_hit_points is None:
                team_won = True
            elif (team_princess_list is None) and (opponent_princess_list is not None):
                team_won = False
            elif (team_princess_list is not None) and (opponent_princess_list is None):
                team_won = True
            elif len(team_princess_list) < len(opponent_princess_list):
                team_won = False
            elif len(team_princess_list) > len(opponent_princess_list):
                team_won = True

            # Determine how many individual matches were won/lost by number of cards used
            if team_won:
                player_dict["duel_series_wins"] += 1
                player_dict["duel_match_wins"] += 2

                if len(battle["team"][0]["cards"]) == 24:
                    player_dict["duel_match_losses"] += 1
            else:
                player_dict["duel_series_losses"] += 1
                player_dict["duel_match_losses"] += 2

                if len(battle["team"][0]["cards"]) == 24:
                    player_dict["duel_match_wins"] += 1

    return player_dict


def calculate_match_performance(post_race: bool, clan_tag: str=PRIMARY_CLAN_TAG, active_members: Dict[str, ClashData]=None):
    """Get the match performance of each player in the specified clan. Saves results in match_history table.

    Args:
        post_race: Whether this check is occuring during or after the river race.
        clan_tag (optional): Check player match performance of players in this clan. Defaults to primary clan.
        active_members (optional): Dictionary of active members. Gets active members of clan_tag if not provided.
    """
    if active_members is None:
        active_members = get_active_members_in_clan(clan_tag)

    if len(active_members) == 0:
        return

    db_utils.clean_up_db(active_members)
    db_utils.add_unregistered_users(clan_tag, active_members)
    performance_list = []

    if post_race:
        participants = get_last_river_race_participants(clan_tag)
        check_time = db_utils.get_reset_time()
    else:
        participants = get_river_race_participants(clan_tag)
        check_time = datetime.datetime.now(datetime.timezone.utc)

    if len(participants) == 0:
        return

    for participant in participants:
        performance_list.append(calculate_player_win_rate(participant['player_tag'], participant['fame'], check_time))

    db_utils.update_match_history(performance_list)
    db_utils.set_last_check_time(check_time)


def calculate_river_race_win_rates(last_check_time: datetime.datetime) -> Dict[str, float]:
    """Calculate win rate of clans in current river race based on river race matches played since last_check_time.

    Args:
        last_check_time: Only consider battles that have occurred after this time.

    Returns:
        Dictionary mapping clan tags to their win rates.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    clan_tag = ""

    def win_rate_helper(tag: str) -> dict:
        return calculate_player_win_rate(tag, 0, now, last_check_time, clan_tag)

    req = requests.get(url=f"https://api.clashroyale.com/v1/clans/%23{PRIMARY_CLAN_TAG[1:]}/currentriverrace",
                       headers={"Accept": "application/json", "authorization": f"Bearer {CLASH_API_KEY}"})

    if req.status_code != 200:
        return {}

    json_obj = req.json()
    clan_averages = {}

    for clan in json_obj['clans']:
        wins = 0
        total = 0
        clan_tag = clan['tag']
        active_members = get_active_members_in_clan(clan_tag)

        if len(active_members) == 0:
            clan_averages[clan_tag] = 0
            continue

        args_list = [participant['tag'] for participant in clan['participants'] if participant['tag'] in active_members]

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(win_rate_helper, args_list))

        for result in results:
            temp_wins = result['battle_wins'] + result['special_battle_wins'] + result['duel_match_wins']
            temp_losses = result['battle_losses'] + result['special_battle_losses'] + result['duel_match_losses']
            wins += temp_wins
            total += temp_wins + temp_losses

        if total == 0:
            clan_averages[clan_tag] = 0
        else:
            clan_averages[clan_tag] = wins/total

    return clan_averages


# TODO: Use TypedDict
def get_clans_in_race(post_race: bool, clan_tag: str=PRIMARY_CLAN_TAG) -> List[Dict[str, Union[str, int, bool]]]:
    """Get a list of clans in the specified clan's river race along with their current fame and decks used.

    Args:
        post_race: Whether this check is happening during or after river race.
        clan_tag (optional): Clan tag of clan to get river race info for. Defaults to primary clan.

    Returns:
        List of clans in the river race and their relevant information.
            {
                "tag": str,
                "name": str,
                "fame": int,
                "total_decks_used": int,
                "decks_used_today": int,
                "completed": bool
            }
    """
    if post_race:
        req = requests.get(url=f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/riverracelog?limit=1",
                           headers={"Accept": "application/json", "authorization": f"Bearer {CLASH_API_KEY}"})

        if req.status_code != 200:
            return []

        json_obj = req.json()
        clans = [clan["clan"] for clan in json_obj["items"][0]["standings"]]
    else:
        req = requests.get(url=f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace",
                           headers={"Accept": "application/json", "authorization": f"Bearer {CLASH_API_KEY}"})

        if req.status_code != 200:
            return []

        json_obj = req.json()
        clans = json_obj["clans"]

    clans_info = []

    for clan in clans:
        fame = 0
        decks_used_total = 0
        decks_used_today = 0

        for participant in clan["participants"]:
            fame += participant["fame"]
            decks_used_total += participant["decksUsed"]
            decks_used_today += participant["decksUsedToday"]

        clans_info.append({"tag": clan["tag"],
                           "name": clan["name"],
                           "fame": fame,
                           "total_decks_used": decks_used_total,
                           "decks_used_today": decks_used_today,
                           "completed": clan["fame"] >= 10000})

    return clans_info


def get_total_cards() -> int:
    """Get total number of cards available in the game.

    Return a cached value. Cached value is updated when this function is called after 24 hours have passed since the last time the
    total number of cards was calculated.

    Returns:
        Total number of cards in the game.
    """
    if not all(hasattr(get_total_cards, attr) for attr in ["cached_total", "last_check_time"]):
        get_total_cards.cached_total = 0
        get_total_cards.last_check_time = None

    now = datetime.datetime.utcnow()

    if get_total_cards.last_check_time is None or (now - get_total_cards.last_check_time).days > 0:
        req = requests.get(url="https://api.clashroyale.com/v1/cards",
                           headers={"Accept": "application/json", "authorization": f"Bearer {CLASH_API_KEY}"})

        if req.status_code == 200:
            get_total_cards.cached_total = len(req.json()["items"])
            get_total_cards.last_check_time = now

    return get_total_cards.cached_total
