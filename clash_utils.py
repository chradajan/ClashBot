from concurrent.futures import ThreadPoolExecutor
from config import PRIMARY_CLAN_TAG
from credentials import CLASH_API_KEY
from typing import List, Tuple
import bot_utils
import datetime
import db_utils
import json
import re
import requests


def get_active_members_in_clan(clan_tag: str=PRIMARY_CLAN_TAG) -> dict:
    """Get a dictionary of members currently in a clan.
    
    Args:
        clan_tag(str, optional): Clan to check.
    
    Returns:
        dict: Dictionary of active members.
            {
                player_tag(str): {
                    "tag": str,
                    "name": str,
                    "role": str,
                    "lastSeen": str,
                    "expLevel": int,
                    "trophies": int,
                    "arena": {
                        "id": int,
                        "name": str
                    },
                    "clanRank": int,
                    "previousClanRank": int,
                    "donations": int,
                    "donationsReceived": int,
                    "clanChestPoints": int
                }
            }
    """
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/members", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
            return {}

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    active_members = {}

    for member in json_obj["items"]:
        active_members[member["tag"]] = member

    return active_members


def get_river_race_participants(clan_tag: str=PRIMARY_CLAN_TAG) -> List[dict]:
    """
    Get a list of participants in the current river race.

    Args:
        clan_tag(str, optional): Clan to get participants of.

    Returns:
        List[dict]: List of participants in specified clan's current river race.
            [
                {
                    "tag": str,
                    "name": str,
                    "fame": int,
                    "repairPoints": int,
                    "boatAttacks": int,
                    "decksUsed": int,
                    "decksUsedToday": int
                },
            ]
    """
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if req.status_code != 200:
        return []

    json_obj = req.json()
    return json_obj["clan"]["participants"]


def get_last_river_race_participants(clan_tag: str=PRIMARY_CLAN_TAG) -> List[dict]:
    """
    Get participants in most recently completed river race.

    Args:
        clan_tag(str, optional): Clan to get participants for.

    Returns:
        List[dict]: List of participants in specified clan's most recently completed river race.
            [
                {
                    "tag": str,
                    "name": str,
                    "fame": int,
                    "repairPoints": int,
                    "boatAttacks": int,
                    "decksUsed": int,
                    "decksUsedToday": int
                },
            ]
    """
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/riverracelog?limit=1", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if req.status_code != 200:
        return []

    json_obj = req.json()
    participants = []
    clan_index = 0

    for clan in json_obj["items"][0]["standings"]:
        if clan["clan"]["tag"] == clan_tag:
            break
        else:
            clan_index += 1

    for participant in json_obj["items"][0]["standings"][clan_index]["clan"]["participants"]:
        participants.append(participant)

    return participants


def parse_player_tag(message: str) -> str:
    """
    Parses a string for a valid player tag.

    Args:
        message(str): String to parse.

    Returns:
        str: A valid player tag, or None if one can't be found.
    """
    found_pattern = re.search(r"(#[A-Z0-9]+)", message)
    if found_pattern != None:
        return found_pattern.group(1)
    return None


def get_clash_user_data(message: str, discord_name: str, discord_id: int) -> dict:
    """
    Get a user's relevant Clash Royale information.

    Args:
        message(str): Message that should contain a valid player tag.
        discord_name(str): The user's discord name in the format name#discriminator.
        discord_id(int): Unique Discord id of a member.

    Returns:
        dict: A dictionary of relevant Clash Royale information, or None if an error occurs.
            {
                "player_tag": str,
                "player_name": str,
                "discord_name": str,
                "discord_id": int,
                "clan_role": str,
                "clan_name": str,
                "clan_tag": str
            }
    """
    player_tag = parse_player_tag(message)

    if player_tag == None:
        return None

    req = requests.get(f"https://api.clashroyale.com/v1/players/%23{player_tag[1:]}", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return None

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    user_dict = {
        "player_tag": player_tag,
        "player_name": json_obj["name"],
        "discord_name": discord_name,
        "discord_id": discord_id
    }

    if "clan" in json_obj.keys():
        user_dict["clan_role"] = json_obj["role"]
        user_dict["clan_name"] = json_obj["clan"]["name"]
        user_dict["clan_tag"] = json_obj["clan"]["tag"]
    else:
        user_dict["clan_role"] = "None"
        user_dict["clan_name"] = "None"
        user_dict["clan_tag"] = "None"

    return user_dict


def get_remaining_decks_today(clan_tag: str=PRIMARY_CLAN_TAG) -> List[Tuple[str, str, int]]:
    """
    Retrieve a list of players in a clan who have not used 4 war decks today.

    Args:
        clan_tag(str, optional): Clan to check.

    Returns:
        List[Tuple[str, str, int]]: List of players in the specified clan that haven't used 4 war decks today.
            [(player_name(str), player_tag(str), decks_remaining(int))]
    """
    participants = get_river_race_participants(clan_tag)
    active_members = get_active_members_in_clan(clan_tag)
    decks_remaining_list = []

    if len(active_members) == 0:
        return []

    for participant in participants:
        player_tag = participant["tag"]
        remaining_decks = 4 - participant["decksUsedToday"]
        if (remaining_decks != 0) and (player_tag in active_members):
            decks_remaining_list.append((active_members[player_tag]["name"], participant["tag"], remaining_decks))

    decks_remaining_list.sort(key = lambda x : (x[2], x[0].lower()))

    return decks_remaining_list


def get_remaining_decks_today_dicts(clan_tag: str=PRIMARY_CLAN_TAG) -> dict:
    """
    Retrieve a dict containing detailed information about deck usage today.

    Args:
        clan_tag(str, optional): Clan to check.

    Returns:
        dict: Detailed lists of specified clan's deck usage.
            {
                remaining_decks: int                                                                Maximum number of decks that could still be used today.
                participants: int                                                                   Number of players who have used at least 1 deck today.
                active_members_with_no_decks_used: int                                              Number of players in the clan that have not used decks.
                active_members_with_remaining_decks: List[Tuple[player_name, decks_remaining]]      Members in clan that could still battle.
                active_members_without_remaining_decks: List[Tuple[player_name, decks_remaining]]   Members in clan that have used 4 decks today.
                inactive_members_with_decks_used: List[Tuple[player_name, decks_remaining]]         Members no longer in clan that battled today while in the clan.
                locked_out_active_members: List[Tuple[player_name, decks_remaining]]                Members in clan that are locked out of battling today.
            }
    """
    active_members = get_active_members_in_clan(clan_tag)
    participants = get_river_race_participants(clan_tag)

    if len(participants) == 0 or len(active_members) == 0:
        return {}

    return_info = {
        "remaining_decks": 200,
        "participants": 0,
        "active_members_with_no_decks_used": 0,
        "active_members_with_remaining_decks": [],
        "active_members_without_remaining_decks": [],
        "inactive_members_with_decks_used": [],
        "locked_out_active_members": []
    }

    for participant in participants:
        if participant["decksUsedToday"] > 0:
            return_info["remaining_decks"] -= participant["decksUsedToday"]
            return_info["participants"] += 1

    for participant in participants:
        if participant["tag"] in active_members:
            participant_name = active_members[participant["tag"]]["name"]
            if participant["decksUsedToday"] == 4:
                return_info["active_members_without_remaining_decks"].append((participant_name, 0))
            elif participant["decksUsedToday"] == 0:
                return_info["active_members_with_no_decks_used"] += 1
                if return_info["participants"] == 50:
                    return_info["locked_out_active_members"].append((participant_name, 4))
                else:
                    return_info["active_members_with_remaining_decks"].append((participant_name, 4))
            else:
                return_info["active_members_with_remaining_decks"].append((participant_name, (4 - participant["decksUsedToday"])))
        elif participant["decksUsedToday"] > 0:
            return_info["inactive_members_with_decks_used"].append((participant["name"], (4 - participant["decksUsedToday"])))

    return_info["active_members_with_remaining_decks"].sort(key = lambda x : (x[1], x[0].lower()))
    return_info["active_members_without_remaining_decks"].sort(key = lambda x : (x[1], x[0].lower()))
    return_info["inactive_members_with_decks_used"].sort(key = lambda x : (x[1], x[0].lower()))
    return_info["locked_out_active_members"].sort(key = lambda x : (x[1], x[0].lower()))

    return return_info


def get_deck_usage_today(clan_tag: str=PRIMARY_CLAN_TAG, active_members: dict=None) -> dict:
    """
    Get a list of players in a clan and how many decks each player used today.

    Args:
        clan_tag(str, optional): Clan to check.

    Returns:
        dict{player_tag(str): decks_used(int)}: dict of players and their deck usage today.
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
        usage_list[participant["tag"]] = participant["decksUsedToday"]
        active_members.pop(participant["tag"], None)

    for player_tag in active_members:
        usage_list[player_tag] = 0

    return usage_list


def get_user_decks_used_today(player_tag: str) -> int:
    """
    Return the number of decks used today by a specific player.

    Args:
        player_tag(str): Player tag of player to look up.

    Returns:
        int: Number of decks used today, or 0 if can't find relevant information.
    """
    req = requests.get(f"https://api.clashroyale.com/v1/players/%23{player_tag[1:]}", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if req.status_code != 200:
        return 0

    json_obj = req.json()
    clan_tag = None

    if "clan" in json_obj.keys():
        clan_tag = json_obj["clan"]["tag"]
    else:
        return 0

    participants = get_river_race_participants(clan_tag)

    if len(participants) == 0:
        return 0

    for participant in participants:
        if participant["tag"] != player_tag:
            continue
        else:
            return participant["decksUsedToday"]

    return 0


def get_top_medal_users(top_n: int=3, clan_tag: str=PRIMARY_CLAN_TAG) -> List[Tuple[str, int]]:
    """
    Get the top n users in a clan by medals. Can possible return more than n if players are tied for the same amount of medals.

    Args:
        top_n(int): Number of players to return. More than this may be returned though.
        clan_tag(str, optional): Clan to look for top players in.

    Returns:
        list[tuple(player_name(str), fame(int))]: List of top players and their medals.
    """
    participants = None

    if db_utils.is_war_time():
        participants = get_river_race_participants(clan_tag)
    else:
        participants = get_last_river_race_participants(clan_tag)

    active_members = get_active_members_in_clan(clan_tag)

    if len(active_members) == 0:
        return []

    fame_list = [ (active_members[participant["tag"]]["name"], participant["fame"]) for participant in participants if participant["tag"] in active_members ]
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
    """
    Get a list of players below a specified fame threshold.

    Args:
        threshold(int): Look for players with fame below this threshold.
        clan_tag(str, optional): Clan to look for players below threshold in.

    Returns:
        list[tuple(player_name(str), fame(int))]: List of players below specified fame threshold.
    """
    participants = None

    if db_utils.is_war_time():
        participants = get_river_race_participants(clan_tag)
    else:
        participants = get_last_river_race_participants(clan_tag)

    active_members = get_active_members_in_clan(clan_tag)
    hall_of_shame = []

    for participant in participants:
        if (participant["fame"] < threshold) and (participant["tag"] in active_members):
            hall_of_shame.append((active_members[participant["tag"]]["name"], participant["tag"], participant["fame"]))

    hall_of_shame.sort(key = lambda x : (x[2], x[0].lower()))
    return hall_of_shame


def get_clan_decks_remaining(clan_tag: str=PRIMARY_CLAN_TAG) -> List[Tuple[Tuple[str, str], int]]:
    """
    Get the number of available war decks remaining for all clans in a race with specified clan.

    Args:
        clan_tag(str, optional): Clan to check the race status of.

    Returns:
        List[Tuple[Tuple[clan_tag, clan_name], decks_remaining]]: List of clans in the specified clan's race and their remaining 
        deck count today.
    """
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

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
    """
    Check if a clan has crossed the finish line.

    Args:
        clan_tag(str, optional): Clan to check completion status of.

    Returns:
        bool: Whether the specified clan has accumulated 10,000 fame and crossed the finish line.
    """
    if db_utils.is_colosseum_week():
        return False

    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if req.status_code != 200:
        return False

    json_obj = req.json()

    return json_obj["clan"]["fame"] >= 10000


def calculate_player_win_rate(player_tag: str,
                              fame: int,
                              current_check_time: datetime.datetime,
                              last_check_time: datetime.datetime=None,
                              clan_tag: str=PRIMARY_CLAN_TAG) -> dict:
    """
    Look at a player's battle log and break down their performance in recent river race battles.

    Args:
        player_tag(str): Player to check match history of.
        fame(int): Total fame they've accumulated in the current river race.
        current_check_time(datetime.datetime): Time to set last_check_time after this check.
        last_check_time(datetime.datetime): Ignore battles before his time.
        clan_tag(str): Only consider battles performed for this clan.

    Returns:
        dict{str: int}: Number of wins and losses in each river race battle type for the specified player.
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

    req = requests.get(f"https://api.clashroyale.com/v1/players/%23{player_tag[1:]}/battlelog", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if req.status_code != 200:
        if is_automated:
            db_utils.set_users_last_check_time(player_tag, last_check_time)
        return {}

    battles = req.json()
    river_race_battle_list = []

    for battle in battles:
        battle_time = bot_utils.battletime_to_datetime(battle["battleTime"])
        if (((battle["type"].startswith("riverRace")) or (battle["type"] == "boatBattle")) and
            (battle_time >= last_check_time) and (battle_time < current_check_time) and
            (battle["team"][0]["clan"]["tag"] == clan_tag)):
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


def calculate_match_performance(post_race: bool, clan_tag: str=PRIMARY_CLAN_TAG, active_members: dict=None):
    """
    Get the match performance of each player in the specified clan. Saves results in match_history table.

    Args:
        post_race(bool): Whether this check is occuring during or after the river race.
        clan_tag(str, optional): Check player match performance of players in this clan.
        active_members(dict, optional): Dict of active members if available.
    """
    if active_members is None:
        active_members = get_active_members_in_clan(clan_tag)

    if len(active_members) == 0:
        return

    db_utils.clean_up_db(active_members)
    db_utils.add_unregistered_users(clan_tag, active_members)
    performance_list = []
    participants = None
    check_time = None

    if post_race:
        participants = get_last_river_race_participants(clan_tag)
        check_time = db_utils.get_reset_time()
    else:
        participants = get_river_race_participants(clan_tag)
        check_time = datetime.datetime.now(datetime.timezone.utc)

    if len(participants) == 0:
        return

    for participant in participants:
        performance_list.append(calculate_player_win_rate(participant["tag"], participant["fame"], check_time))

    db_utils.update_match_history(performance_list)
    db_utils.set_last_check_time(check_time)


def calculate_river_race_win_rates(last_check_time: datetime.datetime) -> dict:
    """
    Calculate win rate of clans in current river race based on river race matches played since last_check_time.

    Args:
        last_check_time(datetime.datetime): Only consider battles that have occurred after this time.
    
    Returns:
        dict: {clan_tag(str): win_rate(float)}
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    clan_tag = ""

    def win_rate_helper(tag: str) -> dict:
        return calculate_player_win_rate(tag, 0, now, last_check_time, clan_tag)

    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{PRIMARY_CLAN_TAG[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if req.status_code != 200:
        return {}

    json_obj = req.json()
    clan_averages = {}

    for clan in json_obj["clans"]:
        wins = 0
        total = 0
        clan_tag = clan["tag"]
        active_members = get_active_members_in_clan(clan_tag)

        if len(active_members) == 0:
            clan_averages[clan_tag] = 0
            continue

        args_list = [participant["tag"] for participant in clan["participants"] if participant["tag"] in active_members]

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(win_rate_helper, args_list))

        for result in results:
            temp_wins = result["battle_wins"] + result["special_battle_wins"] + result["duel_match_wins"]
            temp_losses = result["battle_losses"] + result["special_battle_losses"] + result["duel_match_losses"]
            wins += temp_wins
            total += temp_wins + temp_losses

        if total == 0:
            clan_averages[clan_tag] = 0
        else:
            clan_averages[clan_tag] = wins/total

    return clan_averages


def get_clans_in_race(post_race: bool, clan_tag: str=PRIMARY_CLAN_TAG) -> List[dict]:
    """
    Get a list of clans in the specified clan's river race along with their current fame and decks used.

    Args:
        post_race(bool): Whether this check is happening during or after river race.
        clan_tag(str, optional): Clan tag of clan to get river race info for.

    Returns:
        List[{"tag": str, "name": str, "fame": int, "total_decks_used": int, "decks_used_today": int, "completed": bool}]
    """
    if post_race:
        req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/riverracelog?limit=1", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

        if req.status_code != 200:
            return []

        json_obj = req.json()
        clans = [clan["clan"] for clan in json_obj["items"][0]["standings"]]
    else:
        req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

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
    """
    Used to retrieve a cached value for the number of the cards in the game. Gets updated total if 24 hours have passed since last
    check.

    Returns:
        int: Total number of cards in the game.
    """
    if not all(hasattr(get_total_cards, attr) for attr in ["cached_total", "last_check_time"]):
        get_total_cards.cached_total = 0
        get_total_cards.last_check_time = None

    now = datetime.datetime.utcnow()

    if get_total_cards.last_check_time is None or (now - get_total_cards.last_check_time).days > 0:
        req = requests.get(f"https://api.clashroyale.com/v1/cards", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

        if req.status_code == 200:
            get_total_cards.cached_total = len(req.json()["items"])
            get_total_cards.last_check_time = now

    return get_total_cards.cached_total


def get_card_levels(player_tag: str) -> dict:
    """
    Get dict containing info about a player's player/card levels.

    Args:
        player_tag(str): Player to get information about.

    Returns:
        dict: Player level and card level information.
                {
                    "player_tag": str,
                    "player_name": str,
                    "expLevel": int,
                    "trophies": int,
                    "bestTrophies": int,
                    "cards": dict {14: int, 13: int, 12: int, ..., 1: int},
                    "foundCards": int,
                    "totalCards": int
                }
    """
    req = requests.get(f"https://api.clashroyale.com/v1/players/%23{player_tag[1:]}", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if req.status_code != 200:
        return None

    json_obj = req.json()

    clash_data = {
        "player_tag": player_tag,
        "player_name": json_obj["name"],
        "expLevel": json_obj["expLevel"],
        "trophies": json_obj["trophies"],
        "bestTrophies": json_obj["bestTrophies"],
        "cards": {i: 0 for i in range(1, 15)},
        "foundCards": 0,
        "totalCards": get_total_cards()
    }

    for card in json_obj["cards"]:
        card_level = 14 - (card["maxLevel"] - card["level"])
        clash_data["cards"][card_level] += 1
        clash_data["foundCards"] += 1

    return clash_data
