from config import PRIMARY_CLAN_TAG
from credentials import CLASH_API_KEY
import json
import re
import requests

def GetActiveMembersInClan(clan_tag : str=PRIMARY_CLAN_TAG) -> list:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/members", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
            return []

    jsonDump = json.dumps(req.json())
    jsonObj = json.loads(jsonDump)

    return [ member["name"] for member in jsonObj["items"] ]


def ParsePlayerTag(message: str) -> str:
    foundPattern = re.search(r"(#[A-Z0-9]+)", message)
    if foundPattern != None:
        return foundPattern.group(1)
    return None


def GetClashUserData(message: str, discordName: str) -> dict:
    player_tag = ParsePlayerTag(message)

    if player_tag == None:
        return None

    req = requests.get(f"https://api.clashroyale.com/v1/players/%23{player_tag[1:]}", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return None

    jsonDump = json.dumps(req.json())
    jsonObj = json.loads(jsonDump)

    userDict = {
        "player_tag": player_tag,
        "player_name": jsonObj["name"],
        "discord_name": discordName,
        "clan_role": jsonObj["role"],
        "clan_name": jsonObj["clan"]["name"],
        "clan_tag": jsonObj["clan"]["tag"]
    }

    return userDict


# Get a list of users who have not used 4 decks today.
# Returns [(player_name, decks_remaining)]
def GetDeckUsageToday(clan_tag : str=PRIMARY_CLAN_TAG) -> list:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return []

    jsonDump = json.dumps(req.json())
    jsonObj = json.loads(jsonDump)

    activeMembers = GetActiveMembersInClan(clan_tag)

    participantList = [ (participant["name"], 4 - participant["decksUsedToday"]) for participant in jsonObj["clan"]["participants"] if ((participant["decksUsedToday"] < 4) and (participant["name"] in activeMembers)) ]
    participantList.sort(key = lambda x : (x[1], x[0].lower()))

    return participantList


# Get a list of members in specified clan with fewer than 8 decks used.
# Returns [(player_name, decks_used)]
def GetDeckUsage(clan_tag : str=PRIMARY_CLAN_TAG) -> list:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return []

    jsonDump = json.dumps(req.json())
    jsonObj = json.loads(jsonDump)

    activeMembers = GetActiveMembersInClan(clan_tag)

    participantList = [ (participant["name"], participant["decksUsed"]) for participant in jsonObj["clan"]["participants"] if ((participant["decksUsed"] < 8) and (participant["name"] in activeMembers)) ]

    return participantList

def GetTopFameUsers(topN : int=3, clan_tag : str=PRIMARY_CLAN_TAG) -> list:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"})

    if (req.status_code != 200):
        return []

    jsonDump = json.dumps(req.json())
    jsonObj = json.loads(jsonDump)

    activeMembers = GetActiveMembersInClan(clan_tag)

    fameList = [ (participant["name"], participant["fame"]) for participant in jsonObj["clan"]["participants"] if participant["name"] in activeMembers ]
    fameList.sort(key = lambda x : x[1], reverse = True)

    if len(fameList) <= topN:
        return fameList

    i = topN - 1
    returnList = fameList[:topN]

    while (i + 1 < len(fameList)) and (fameList[i][1] == fameList[i + 1][1]):
        returnList.append(fameList[i + 1])
        i += 1

    return returnList

def GetHallOfShame(threshold: int, clan_tag : str=PRIMARY_CLAN_TAG) -> list:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"}, params = {"limit":20})

    if (req.status_code != 200):
        return []

    jsonDump = json.dumps(req.json())
    jsonObj = json.loads(jsonDump)

    activeMembers = GetActiveMembersInClan(clan_tag)

    participantList = [ (participant["name"], participant["fame"]) for participant in jsonObj["clan"]["participants"] if ((participant["fame"] < threshold) and (participant["name"] in activeMembers)) ]
    participantList.sort(key = lambda x : (x[1], x[0].lower()))

    return participantList

def GetOtherClanDecksRemaining(clan_tag : str=PRIMARY_CLAN_TAG) -> dict:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"}, params = {"limit":20})

    if (req.status_code != 200):
        return []

    jsonDump = json.dumps(req.json())
    jsonObj = json.loads(jsonDump)

    returnList = []

    for clan in jsonObj["clans"]:
        activeMembers = GetActiveMembersInClan(clan["tag"])
        decksRemaining = 0

        for participant in clan["participants"]:
            if participant["name"] in activeMembers:
                decksRemaining += (4 - participant["decksUsedToday"])

        returnList.append((clan["name"], decksRemaining))

    returnList.sort(key = lambda x : (x[1], x[0]))

    return returnList
