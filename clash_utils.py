from config import PRIMARY_CLAN_TAG
from credentials import CLASH_API_KEY
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
        dict {player_tag(str): player_name(str)}: Dictionary of active members.
    """
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/members", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
            return {}

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    return { member["tag"]: member["name"] for member in json_obj["items"] }


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


def get_remaining_decks_today(clan_tag: str=PRIMARY_CLAN_TAG) -> list:
    """
    Retrieve a list of players in a clan who have not used 4 war decks today.

    Args:
        clan_tag(str, optional): Clan to check.

    Returns:
        list[tuple(str, int)]: List of players in the specified clan that haven't used 4 war decks today.
            [(player_name(str), decks_remaining(int))]
    """
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return []

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    active_members = list(get_active_members_in_clan(clan_tag).values())

    participants = [ (participant["name"], 4 - participant["decksUsedToday"]) for participant in json_obj["clan"]["participants"] if ((participant["decksUsedToday"] < 4) and (participant["name"] in active_members)) ]
    participants.sort(key = lambda x : (x[1], x[0].lower()))

    return participants


def get_deck_usage_today(clan_tag: str=PRIMARY_CLAN_TAG) -> list:
    """
    Get a list of players in a clan and how many decks each player used today.

    Args:
        clan_tag(str, optional): Clan to check.

    Returns:
        dict{player_tag(str): decks_used(int)}: dict of players and their deck usage today.
    """
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return {}

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    active_members = get_active_members_in_clan(clan_tag)

    usage_list = {}

    for participant in json_obj["clan"]["participants"]:
        usage_list[participant["tag"]] = participant["decksUsedToday"]

        if participant["tag"] in active_members:
            active_members.pop(participant["tag"], None)

    for player_tag in active_members:
        usage_list[player_tag] = 0

    return usage_list


def get_deck_usage_today_dict(clan_tag: str=PRIMARY_CLAN_TAG) -> dict:
    """
    Get a list of players in a clan and how many decks each player used today.

    Args:
        clan_tag(str, optional): Clan to check.

    Returns:
        dict{player_name(str): decksUsedToday(int)}: dict of players and their deck usage.
    """
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return {}

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    active_members = get_active_members_in_clan(clan_tag)

    participants = {}

    for participant in json_obj["clan"]["participants"]:
        if participant["tag"] not in active_members:
            continue

        participants[participant["name"]] = participant["decksUsedToday"]

    return participants


def get_user_decks_used_today(player_tag: str) -> int:
    """
    Return the number of decks used today by a specific player.

    Args:
        player_tag(str): Player tag of player to look up.

    Returns:
        int: Number of decks used today, or 0 if can't find relevant information.
    """
    req = requests.get(f"https://api.clashroyale.com/v1/players/%23{player_tag[1:]}", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return 0

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)
    clan_tag = None

    if "clan" in json_obj.keys():
        clan_tag = json_obj["clan"]["tag"]
    else:
        return 0

    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})
    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    if (req.status_code != 200):
        return 0

    for participant in json_obj["clan"]["participants"]:
        if participant["tag"] != player_tag:
            continue
        else:
            return participant["decksUsedToday"]

    return 0


def get_top_fame_users(top_n: int=3, clan_tag: str=PRIMARY_CLAN_TAG) -> list:
    """
    Get the top n users in a clan by fame. Can possible return more than n if players are tied for the same amount of fame.

    Args:
        top_n(int): Number of players to return. More than this may be returned though.
        clan_tag(str, optional): Clan to look for top players in.

    Returns:
        list[tuple(player_name(str), fame(int))]: List of top players and their fame.
    """
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return []

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    active_members = list(get_active_members_in_clan(clan_tag).values())

    fame_list = [ (participant["name"], participant["fame"]) for participant in json_obj["clan"]["participants"] if participant["name"] in active_members ]
    fame_list.sort(key = lambda x : x[1], reverse = True)

    if len(fame_list) <= top_n:
        return fame_list

    i = top_n - 1
    return_list = fame_list[:top_n]

    while (i + 1 < len(fame_list)) and (fame_list[i][1] == fame_list[i + 1][1]):
        return_list.append(fame_list[i + 1])
        i += 1

    return return_list


def get_hall_of_shame(threshold: int, clan_tag: str=PRIMARY_CLAN_TAG) -> list:
    """
    Get a list of players below a specified fame threshold.

    Args:
        threshold(int): Look for players with fame below this threshold.
        clan_tag(str, optional): Clan to look for players below threshold in.

    Returns:
        list[tuple(player_name(str), fame(int))]: List of players below specified fame threshold.
    """
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return []

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    active_members = list(get_active_members_in_clan(clan_tag).values())

    participants = [ (participant["name"], participant["fame"]) for participant in json_obj["clan"]["participants"] if ((participant["fame"] < threshold) and (participant["name"] in active_members)) ]
    participants.sort(key = lambda x : (x[1], x[0].lower()))

    return participants


def get_clan_decks_remaining(clan_tag: str=PRIMARY_CLAN_TAG) -> dict:
    """
    Get the number of available war decks remaining for all clans in a race with specified clan.

    Args:
        clan_tag(str, optional): Clan to check the race status of.

    Returns:
        list[tuple(clan_name(str), decks_remaining(int))]: List of clans in the specified clan's race and their remaining deck count today.
    """
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return []

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    return_list = []

    for clan in json_obj["clans"]:
        active_members = list(get_active_members_in_clan(clan["tag"]).values())
        decks_remaining = 0

        for participant in clan["participants"]:
            if participant["name"] in active_members:
                decks_remaining += (4 - participant["decksUsedToday"])

        return_list.append((clan["name"], decks_remaining))

    return_list.sort(key = lambda x : (x[1], x[0]))

    return return_list


def river_race_completed(clan_tag: str=PRIMARY_CLAN_TAG) -> bool:
    """
    Check if a clan has crossed the finish line.

    Args:
        clan_tag(str, optional): Clan to check completion status of.

    Returns:
        bool: Whether the specified clan has accumulated 10,000 fame and crossed the finish line.
    """
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return False

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    return json_obj["clan"]["fame"] >= 10000


def calculate_player_win_rate(player_tag: str, fame: int) -> dict:
    """
    Look at a player's battelog and break down their performance in recent river race battles.

    Args:
        player_tag(str): Player to check match history of.
        fame(int): Total fame they've accumulated in the current river race.

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
    prev_fame, last_check_time = db_utils.get_and_update_match_history_fame_and_battle_time(player_tag, fame)
    fame -= prev_fame

    # If no fame has been acquired since last check, no point in grabbing battlelog.
    if fame == 0:
        return {}

    req = requests.get(f"https://api.clashroyale.com/v1/players/%23{player_tag[1:]}/battlelog", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return {}

    json_dump = json.dumps(req.json())
    river_race_battle_list = json.loads(json_dump)

    # This list comprehension will result in a list of river race battles since the last check
    river_race_battle_list = [ battle for battle in river_race_battle_list if (((battle["type"].startswith("riverRace")) or (battle["type"] == "boatBattle")) and (bot_utils.battletime_to_datetime(battle["battleTime"]) > last_check_time)) ]

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
            # Determine duel series outcome by result of final game
            team_king_hit_points = battle["team"][0].get("kingTowerHitPoints")
            team_princess_list = battle["team"][0].get("princessTowersHitPoints")
            opponent_king_hit_points = battle["opponent"][0].get("kingTowerHitPoints")
            opponent_princess_list = battle["opponent"][0].get("princessTowersHitPoints")
            team_won = None

            if team_king_hit_points == None:
                team_won = False
            elif opponent_king_hit_points == None:
                team_won = True
            elif (team_princess_list == None) and (opponent_princess_list != None):
                team_won = False
            elif (team_princess_list != None) and (opponent_princess_list == None):
                team_won = True
            elif len(team_princess_list) < len(opponent_princess_list):
                team_won = False
            elif len(team_princess_list) > len(opponent_princess_list):
                team_won = True

            # Determine how many individual matches were won/lost by number of cards used
            if team_won == None:
                print("Can't determine duel outcome. Player tag: ", player_tag)
            elif team_won:
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


def calculate_match_performance(clan_tag: str=PRIMARY_CLAN_TAG):
    """
    Get the match performance of each player in the specified clan. Saves results in match_history table.

    Args:
        clan_tag(str, optional): Check player match performance of players in this clan.
    """
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    active_members = get_active_members_in_clan(clan_tag)
    player_list = [ player for player in json_obj["clan"]["participants"] if (player["tag"] in active_members) and (player["decksUsedToday"] > 0) ]

    performance_list = []

    for player in player_list:
        performance_list.append(calculate_player_win_rate(player["tag"], player["fame"]))

    db_utils.update_match_history(performance_list)