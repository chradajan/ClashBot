from config import PRIMARY_CLAN_TAG
from credentials import CLASH_API_KEY
import json
import re
import requests

def ParsePlayerTag(message: str) -> str:
    foundPattern = re.search(r"(#[A-Z0-9]+)", message)
    if foundPattern != None:
        return foundPattern.group(1)
    return None


def GetClashUserData(message: str, discordName: str) -> dict:
    player_tag = ParsePlayerTag(message)

    if player_tag == None:
        return None

    req = requests.get(f"https://api.clashroyale.com/v1/players/%23{player_tag[1:]}", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"}, params = {"limit":20})

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
def GetDeckUsageToday(clan_tag = PRIMARY_CLAN_TAG) -> list:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"}, params = {"limit":20})

    if (req.status_code != 200):
        return []

    jsonDump = json.dumps(req.json())
    jsonObj = json.loads(jsonDump)

    participantList = [ (participant["name"], participant["decksUsedToday"]) for participant in jsonObj["clan"]["participants"] if (participant["decksUsedToday"] < 4) ]
    participantList.sort(key = lambda x : (x[1], x[0]))

    return participantList


# Get a list of user who have not used 8 decks during current river race.
def GetDeckUsage(clan_tag = PRIMARY_CLAN_TAG) -> list:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"}, params = {"limit":20})

    if (req.status_code != 200):
        return []

    jsonDump = json.dumps(req.json())
    jsonObj = json.loads(jsonDump)

    participantList = [ (participant["name"], participant["decksUsed"]) for participant in jsonObj["clan"]["participants"] if (participant["decksUsed"] < 8) ]
    participantList.sort(key = lambda x : (x[1], x[0]))

    return participantList

def GetTopFameUsers(topN :int=3, clan_tag = PRIMARY_CLAN_TAG) -> list:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"}, params = {"limit":20})

    if (req.status_code != 200):
        return []

    jsonDump = json.dumps(req.json())
    jsonObj = json.loads(jsonDump)

    fameList = [ (participant["name"], participant["fame"]) for participant in jsonObj["clan"]["participants"] ]
    fameList.sort(key = lambda x : x[1], reverse = True)

    if len(fameList) <= topN:
        return fameList

    i = topN - 1
    returnList = fameList[:topN]

    while (i + 1 < len(fameList)) and (fameList[i][1] == fameList[i + 1][1]):
        returnList.append(fameList[i + 1])
        i += 1

    return returnList

def GetHallOfShame(threshold: int, clan_tag = PRIMARY_CLAN_TAG) -> list:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"}, params = {"limit":20})

    if (req.status_code != 200):
        return []

    jsonDump = json.dumps(req.json())
    jsonObj = json.loads(jsonDump)

    participantList = [ (participant["name"], participant["fame"]) for participant in jsonObj["clan"]["participants"] if participant["fame"] < threshold ]
    participantList.sort(key = lambda x : (x[1], x[0]), reverse = True)

    return participantList

def GetOtherClanDecksRemaining(clan_tag = PRIMARY_CLAN_TAG) -> dict:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"}, params = {"limit":20})

    if (req.status_code != 200):
        return []

    jsonDump = json.dumps(req.json())
    jsonObj = json.loads(jsonDump)

    returnList = []

    for clan in jsonObj["clans"]:
        decksRemaining = 0
        for participant in clan["participants"]:
            decksRemaining += 4 - participant["decksUsedToday"]
        returnList.append((clan["name"], decksRemaining))

    returnList.sort(key = lambda x : (x[1], x[0]))

    return returnList
