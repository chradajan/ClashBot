from config import PRIMARY_CLAN_TAG
from credentials import CLASH_API_KEY
import json
import re
import requests

# { player_tag: player_name }
def get_active_members_in_clan(clan_tag : str=PRIMARY_CLAN_TAG) -> dict:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/members", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
            return {}

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    return { member["tag"]: member["name"] for member in json_obj["items"] }


def parse_player_tag(message: str) -> str:
    found_pattern = re.search(r"(#[A-Z0-9]+)", message)
    if found_pattern != None:
        return found_pattern.group(1)
    return None


# clash_data = {
#     player_tag: str,
#     player_name: str,
#     discord_name: str,
#     clan_role: str,
#     clan_name: str,
#     clan_tag: str
# }
def get_clash_user_data(message: str, discord_name: str) -> dict:
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


# Get a list of users who have not used 4 decks today.
# [(player_name, decks_remaining)]
def get_remaining_decks_today(clan_tag: str=PRIMARY_CLAN_TAG) -> list:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return []

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    active_members = list(get_active_members_in_clan(clan_tag).values())

    participants = [ (participant["name"], 4 - participant["decksUsedToday"]) for participant in json_obj["clan"]["participants"] if ((participant["decksUsedToday"] < 4) and (participant["name"] in active_members)) ]
    participants.sort(key = lambda x : (x[1], x[0].lower()))

    return participants


# Get a list of players in clan and decks used today
# [(player_tag, decks_used)]
def get_deck_usage_today(clan_tag: str=PRIMARY_CLAN_TAG) -> list:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return []

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    active_members = list(get_active_members_in_clan(clan_tag).keys())

    participants = [ (participant["tag"], participant["decksUsedToday"]) for participant in json_obj["clan"]["participants"] if participant["tag"] in active_members ]

    return participants


# Get a list of players in clan and decks used today
# {player_name: decks_used}
def get_deck_usage_today_dict(clan_tag: str=PRIMARY_CLAN_TAG) -> dict:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return []

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    active_members = list(get_active_members_in_clan(clan_tag).values())

    participants = {}

    for participant in json_obj["clan"]["participants"]:
        if participant["name"] not in active_members:
            continue

        participants[participant["name"]] = participant["decksUsedToday"]

    return participants


def get_user_decks_used_today(player_tag: str) -> int:
    req = requests.get(f"https://api.clashroyale.com/v1/players/%23{player_tag[1:]}", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return None

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)
    clan_tag = None

    if "clan" in json_obj.keys():
        clan_tag = json_obj["clan"]["tag"]
    else:
        return None

    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})
    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    if (req.status_code != 200):
        return None

    for participant in json_obj["clan"]["participants"]:
        if participant["tag"] != player_tag:
            continue
        else:
            return participant["decksUsedToday"]

    return None


# [(player_name, fame)]
def get_top_fame_users(top_n : int=3, clan_tag : str=PRIMARY_CLAN_TAG) -> list:
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

# [(player_name, fame)]
def get_hall_of_shame(threshold: int, clan_tag : str=PRIMARY_CLAN_TAG) -> list:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return []

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    active_members = list(get_active_members_in_clan(clan_tag).values())

    participants = [ (participant["name"], participant["fame"]) for participant in json_obj["clan"]["participants"] if ((participant["fame"] < threshold) and (participant["name"] in active_members)) ]
    participants.sort(key = lambda x : (x[1], x[0].lower()))

    return participants

# [(clan_name, decks_remaining)]
def get_clan_decks_remaining(clan_tag : str=PRIMARY_CLAN_TAG) -> dict:
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


def river_race_completed(clan_tag : str=PRIMARY_CLAN_TAG) -> bool:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return False

    json_dump = json.dumps(req.json())
    json_obj = json.loads(json_dump)

    return json_obj["clan"]["fame"] >= 10000
