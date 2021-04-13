from credentials import CLASH_API_KEY
import json
import re
import requests

def ParsePlayerTag(message: str) -> str:
    foundPattern = re.search(r"(#[A-Z0-9]+)", message)
    if (foundPattern != None):
        return foundPattern.group(1)
    return None


def GetClashUserData(message: str, discordName: str) -> dict:
    player_tag = ParsePlayerTag(message)
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


def GetDeckUsageToday(clan_tag = "#JVQJRV0") -> list:
    req = requests.get(f"https://api.clashroyale.com/v1/clans/%23{clan_tag[1:]}/currentriverrace", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"}, params = {"limit":20})

    if (req.status_code != 200):
        return []

    jsonDump = json.dumps(req.json())
    jsonObj = json.loads(jsonDump)

    participantList = []

    try:
        participantList = [ (participant["name"], participant["decksUsedToday"]) for participant in jsonObj["clan"]["participants"] if (participant["decksUsedToday"] < 4) ]
    except:
        print("Failed to get decksUsedToday")

    return participantList