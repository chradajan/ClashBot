from credentials import CLASH_API_KEY
import json
import re
import requests

def ParseClanTag(message: str) -> str:
    foundPattern = re.search(r"(#[A-Z0-9]+)", message)
    if (foundPattern != None):
        return foundPattern.group(1)
    return None


def GetClashUserData(message: str, discordName: str) -> dict:
    clanTag = ParseClanTag(message)
    req = requests.get(f"https://api.clashroyale.com/v1/players/%23{clanTag[1:]}", headers={"Accept":"application/json", "authorization":f"Bearer {CLASH_API_KEY}"}, params = {"limit":20})
    if (req.status_code != 200):
        return None
    jsonDump = json.dumps(req.json())
    jsonObj = json.loads(jsonDump)
    userDict = {
        "player_tag": clanTag,
        "player_name": jsonObj["name"],
        "discord_name": discordName,
        "clan_role": jsonObj["role"],
        "clan_name": jsonObj["clan"]["name"],
        "clan_tag": jsonObj["clan"]["tag"]
    }
    return userDict