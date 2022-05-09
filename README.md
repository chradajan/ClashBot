
# ClashBot

https://clashbot.readthedocs.io/en/latest/

ClashBot is a Discord bot that helps moderate servers dedicated to Clash Royale clans.
- Manages server roles
- Tracks daily participation in river races.
- Tracks river race match wins/losses for each member of the clan.
- Sends reminders to members who haven't used all their river race decks on war days.
- Assign strikes to members with low participation in river races.
- Automatically set users' nicknames equal to their in-game usernames.
## Discord Server Requirements

ClashBot requires certain roles and channels to be present on the server. The exact names of these roles and channels can be configured (see [Installation](#Installation)).
A basic template of a server configured to utilize ClashBot can be found [here](https://discord.new/w4MqRZYMERr4).

#### Roles
| Name | Description |
|------|-------------|
| New | Role assigned to new users upon joining server. Removed by providing player tag. |
| Check Rules | Role given after a new users provides their player tag. Removed by reacting to rules message.  |
| Visitor | Role assigned to users that are not active members of the clan. |
| Member | Role assigned to users that are active members of the clan. |
| Elder | Role provided to elders in the clan. Provides access to some leader commands. |
| Leader | Manually given role that gives access to more leader commands. |
| Admin | Manually given role that gives access to all commands. |

*\*The names listed above are the default names of these roles*  

#### Channels
| Name | Default | Description |
|------|---------|-------------|
| Welcome | #welcome | Where users with the New role provide their player tags. |
| Rules | #rules | Where rules are posted and members with the Check Rules react to get their assigned roles. |
| Time Off | #time-off | Where users can set vacation status to be omitted from strikes/reminders in next river race. |
| Fame | #hall-of-fame | Where bot sends messages regarding member medal counts. |
| Reminders | #cw-strats | Where deck usage reminders are sent. |
| Strikes | #strikes | Where users are notified when they gain/lose strikes. |
| Leader Info | #new-member-info | Displays stats of new users after they enter a player tag. |
| Kicks | #clan-kicks | Automatically parses in-game screenshots of users being kicked from the clan to easily log the kick. |
| Commands | #leader-commands | Where elders/leaders/admins can utilize various commands. |

## Python

ClashBot is written in Python and requires version >= 3.8.  
https://www.python.org/downloads/
## Discord Developer

You must create a Discord bot that will run ClashBot.

- Visit https://discord.com/developers/docs/intro
- Create a new application, then create a bot.
- Make sure your bot has the following permissions:
    - Manage Roles
    - Manage Nicknames
    - View Channels
    - Send Messages
    - Manage Messages
    - Embed Links
    - Attach Files
    - Read Message History
    - Mention Everyone
    - Add Reactions
## Clash Royale API
 
 Clash Royale data is retrieved from the official Clash Royale API. You must supply your own API key.

 - Create a developer account at https://developer.clashroyale.com/.
 - Once signed in, choose "My Account" from the dropdown in the top right.
 - Create a new API key with the IP address of the server where the bot will be hosted.
## Database

User information and statistics are store in a MySQL database. A MySQL server is required to run ClashBot.

- Follow the steps at https://dev.mysql.com/doc/mysql-installation-excerpt/5.7/en/linux-installation.html if you need to install MySQL.
- The database schema is provided by [setup/DB_Creation_Script.sql](setup/DB_Creation_Script.sql).
- Create a database and user.

## Installation

Steps to configure and start ClashBot

#### Using setup script
```bash
git clone https://github.com/chradajan/ClashBot.git
cd ClashBot
pip install -r requirements.txt
cd setup
./setup.sh
cd ../bot
python3 bot.py
```
The setup script will automatically configure the database with the required schema. 

#### Manual Setup (not necessary if using setup script)
```bash
git clone https://github.com/chradajan/ClashBot.git
cd ClashBot
pip install -r requirements.txt
cd setup
cd ../bot
```
1. After cloning repository, move [ClashBot/setup/blacklist_example.py](setup/blacklist_example.py), [ClashBot/setup/config_example.py](setup/config_example.py), [ClashBot/setup/credentials_example.py](setup/credentials_example.py) to `ClashBot/bot/config/`.
2. Remove "_example" from each file, e.g. `blacklist_example.py` will become `blacklist.py`.
- `ClashBot/bot/config` should now look like this:
    ```bash
    config
    ├── __init__.py
    ├── blacklist.py
    ├── config.py
    ├── credentials.py
    └── logging_config.json
    ```
3. Edit `blacklist.py` if you want to blacklist any users from gaining Elder role even if they are an elder or higher in-game.
- Add the player tags of any blacklisted users to the `BLACKLIST` set like this: `BLACKLIST = {"#ABC123", "#XYZ123"}`.
4. Fill in your server's name, the names of your server's relevant roles and channels, and your clan's name and tag in `config.py`.
5. Provide your bot token, API key, and database credentials in `credentials.py`.
6. Create the database.
- `mysql -u {username} -p {database_name} < setup/DB_Creation_Script.sql`
- The discord_roles table must be populated with the names of the roles on your server.
- If the name of the Leader role on your server is "Coleader", you would do:
    - `mysql -u {username} -p {database_name} -e "INSERT INTO discord_roles VALUES (DEFAULT, 'Coleader');"`
    - Repeat for all seven relevant roles.
7. Launch ClashBot with `python3 bot.py`




  
## How to use

After launching ClashBot for the first time, an admin should run the `!reset_all_members` command in the Commands channel. 
This will clear the database, remove all roles that the bot manages from all users, and assign everyone the New role. Users 
can then begin to enter their player tags in the Welcome channel. Admins should enter their tags as well and react to the rules 
so that they're properly added into the database.  

The bot will now manage roles, send reminders, and track river race statistics. The Member and Visitor roles will automatically be 
given to users based on whether they're active members of the primary clan. Elders in the primary clan will automatically be given 
the Elder role. The Leader and Admin roles must be manually assigned. The bot checks for any necessary role/name changes every 8 hours. 

Use the `!help` command to see a list of commands available to you in the current channel.
## FAQ

#### What does the status column mean in the spreadsheet generated by `!export`?

ClashBot assigns 1 of 4 statuses to each user in the database based on whether they're a member of the clan and Discord server.  
| Status | In the clan | On Discord |
|--------|-------------|------------|
| ACTIVE | YES | YES |
| INACTIVE | NO | YES |
| UNREGISTERED | YES | NO |
| DEPARTED | NO | NO |

#### A Discord user joined the clan but they still have the Visitor role, when will this be updated?

ClashBot runs a check every 8 hours that makes necessary role adjustments such as this. If you'd like to update someone sooner, 
that user can use the `!update` command, or a leader can use either the `!update_member {member}` or `!update_all_members` command.

#### Why is the initial join date incorrect for members of the primary clan?

The initial join date is intended to track when a user first joined the primary clan. Unfortunately, this data cannot be retrieved 
from the Clash Royale API, so this date will depend on when the bot started tracking your clan.

