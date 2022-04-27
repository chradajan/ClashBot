#!/usr/bin/env bash
cd ../bot/config

# Get blacklist
echo -n "BLACKLIST = {" > blacklist.py
printf "Enter any player tags you would like to blacklist from receiving the elder role regardless of their in-game role.\n"
printf "Provide player tags one line at a time with the # symbol in front of them. Enter a blank line to proceed to the next section.\n\n"

while true
do
    echo  -e "Tag: \c"
    read input
    if [[ $input = "" ]]; then
        break
    fi
    echo -n "\"$input\", " >> blacklist.py
done

echo -n "}" >> blacklist.py
printf "\nBlacklist complete, moving on to config settings.\n\n"

# Get config

# Discord server name
echo  -e "Discord server name: \c"
read input
echo "GUILD_NAME = \"$input\"" > config.py

# Role names
printf "\nEnter role names\n\n"

echo  -e "New role name (leave blank for default): \c"
read new_role_name
if [[ $new_role_name = "" ]]; then
    new_role_name="New"
    echo "NEW_ROLE_NAME = \"New\"" >> config.py
fi
echo "NEW_ROLE_NAME = \"$new_role_name\"" >> config.py


echo  -e "Check rules role name (leave blank for default): \c"
read check_rules_role_name
if [[ $check_rules_role_name = "" ]]; then
    check_rules_role_name="Check Rules"
fi
echo "CHECK_RULES_ROLE_NAME = \"$check_rules_role_name\"" >> config.py

echo  -e "Visitor role name (leave blank for default): \c"
read visitor_role_name
if [[ $visitor_role_name = "" ]]; then
    visitor_role_name="Visitor"
fi
echo "VISITOR_ROLE_NAME = \"$visitor_role_name\"" >> config.py

echo  -e "Member role name (leave blank for default): \c"
read member_role_name
if [[ $member_role_name = "" ]]; then
    member_role_name="Member"
fi
echo "MEMBER_ROLE_NAME = \"$member_role_name\"" >> config.py

echo  -e "Elder role name (leave blank for default): \c"
read elder_role_name
if [[ $elder_role_name = "" ]]; then
    elder_role_name="Elder"
fi
echo "ELDER_ROLE_NAME = \"$elder_role_name\"" >> config.py

echo  -e "Leader role name (leave blank for default): \c"
read leader_role_name
if [[ $leader_role_name = "" ]]; then
    leader_role_name="Leader"
fi
echo "LEADER_ROLE_NAME = \"$leader_role_name\"" >> config.py

echo  -e "Admin role name (leave blank for default): \c"
read admin_role_name
if [[ $admin_role_name = "" ]]; then
    admin_role_name="Admin"
fi
echo "ADMIN_ROLE_NAME = \"$admin_role_name\"" >> config.py

echo "" >> config.py

# Channel names

printf "\nEnter channel names\n\n"

echo  -e "Welcome channel name (leave blank for default): \c"
read input
if [[ $input = "" ]]; then
    echo "WELCOME_CHANNEL_NAME = \"welcome\"" >> config.py
else
    echo "WELCOME_CHANNEL_NAME = \"$input\"" >> config.py
fi

echo  -e "Rules channel name (leave blank for default): \c"
read input
if [[ $input = "" ]]; then
    echo "RULES_CHANNEL_NAME = \"rules\"" >> config.py
else
    echo "RULES_CHANNEL_NAME = \"$input\"" >> config.py
fi

echo  -e "Time off channel name (leave blank for default): \c"
read input
if [[ $input = "" ]]; then
    echo "TIME_OFF_CHANNEL_NAME = \"time-off\"" >> config.py
else
    echo "TIME_OFF_CHANNEL_NAME = \"$input\"" >> config.py
fi

echo  -e "Fame channel name (leave blank for default): \c"
read input
if [[ $input = "" ]]; then
    echo "FAME_CHANNEL_NAME = \"hall-of-fame\"" >> config.py
else
    echo "FAME_CHANNEL_NAME = \"$input\"" >> config.py
fi

echo  -e "Reminders channel name (leave blank for default): \c"
read input
if [[ $input = "" ]]; then
    echo "REMINDER_CHANNEL_NAME = \"cw-strats\"" >> config.py
else
    echo "REMINDER_CHANNEL_NAME = \"$input\"" >> config.py
fi

echo  -e "Strikes channel name (leave blank for default): \c"
read input
if [[ $input = "" ]]; then
    echo "STRIKES_CHANNEL_NAME = \"strikes\"" >> config.py
else
    echo "STRIKES_CHANNEL_NAME = \"$input\"" >> config.py
fi

echo  -e "Leader info channel name (leave blank for default): \c"
read input
if [[ $input = "" ]]; then
    echo "LEADER_INFO_CHANNEL_NAME = \"new-member-info\"" >> config.py
else
    echo "LEADER_INFO_CHANNEL_NAME = \"$input\"" >> config.py
fi

echo  -e "Kicks channel name (leave blank for default): \c"
read input
if [[ $input = "" ]]; then
    echo "KICKS_CHANNEL_NAME = \"clan-kicks\"" >> config.py
else
    echo "KICKS_CHANNEL_NAME = \"$input\"" >> config.py
fi

echo  -e "Commands channel name (leave blank for default): \c"
read input
if [[ $input = "" ]]; then
    echo "COMMANDS_CHANNEL_NAME = \"leader-commands\"" >> config.py
else
    echo "COMMANDS_CHANNEL_NAME = \"$input\"" >> config.py
fi

echo "" >> config.py

# Clan information
printf "\nEnter primary clan information\n\n"

echo -e "Clan name: \c"
read input
echo "PRIMARY_CLAN_NAME = \"$input\"" >> config.py

echo -e "Clan tag (include # symbol): \c"
read input
echo "PRIMARY_CLAN_TAG = \"$input\"" >> config.py

# Provide default emojis and reminder message
echo "CONFIRM_EMOJI = \"✅\"" >> config.py
echo "DECLINE_EMOJI = \"❌\"" >> config.py
echo "" >> config.py
echo "DEFAULT_REMINDER_MESSAGE = \"Please complete your battles by the end of the day:\"" >> config.py

# Credentials
printf "\nEnter credentials\n\n"

echo -e "Discord bot token: \c"
read input
echo "BOT_TOKEN = \"$input\"" > credentials.py

echo -e "Clash Royale API key: \c"
read input
echo "CLASH_API_KEY = \"$input\"" >> credentials.py

echo -e "Database IP: \c"
read database_ip
echo "IP = \"$database_ip\"" >> credentials.py

echo -e "Database username: \c"
read database_username
echo "USERNAME = \"$database_username\"" >> credentials.py

echo -e "Database password: \c"
read database_password
echo "PASSWORD = \"$database_password\"" >> credentials.py

echo -e "Database name: \c"
read database_name
echo "DB_NAME = \"$database_name\"" >> credentials.py

# Prepare database
cd ../../setup

mysql -u $database_username -p$database_password $database_name < DB_Creation_Script.sql
mysql -u $database_username -p$database_password $database_name -e "INSERT INTO discord_roles VALUES (DEFAULT, \"$admin_role_name\");"
mysql -u $database_username -p$database_password $database_name -e "INSERT INTO discord_roles VALUES (DEFAULT, \"$leader_role_name\");"
mysql -u $database_username -p$database_password $database_name -e "INSERT INTO discord_roles VALUES (DEFAULT, \"$elder_role_name\");"
mysql -u $database_username -p$database_password $database_name -e "INSERT INTO discord_roles VALUES (DEFAULT, \"$member_role_name\");"
mysql -u $database_username -p$database_password $database_name -e "INSERT INTO discord_roles VALUES (DEFAULT, \"$visitor_role_name\");"
mysql -u $database_username -p$database_password $database_name -e "INSERT INTO discord_roles VALUES (DEFAULT, \"$check_rules_role_name\");"
mysql -u $database_username -p$database_password $database_name -e "INSERT INTO discord_roles VALUES (DEFAULT, \"$new_role_name\");"

echo "Setup Complete"
