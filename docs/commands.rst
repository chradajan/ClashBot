.. _commands:

********
Commands
********

This page documents all the commands provided by ClashBot. Using ``!help`` on Discord will provide a list of commands available to
you given your current roles and the channel that you asked for help in.

------------------------------------------------------------------------------------------------------------------------------------

Automation Tools
================

A set of commands available to Leaders and Admins to control some of ClashBot's automated routines.
To see more info about these commands on Discord, use ``!help AutomationTools``.

automation_status
*****************

.. table::
    :widths: 50 25 25
    :align: left

    +---------------------------------------+-----------------+----------------------+
    | Command                               | Roles           | Channels             |
    +=======================================+=================+======================+
    | ``!automation_status``                |  | Leader       | Commands             |
    |                                       |  | Admin        |                      |
    +---------------------------------------+-----------------+----------------------+

Check whether automated reminders and automated strikes are enabled/disabled.

set_automated_reminders
***********************

.. table::
    :widths: 50 25 25
    :align: left

    +---------------------------------------+-----------------+----------------------+
    | Command                               | Roles           | Channels             |
    +=======================================+=================+======================+
    | ``!set_automated_reminders <status>`` | | Leader        | Commands             |
    |                                       | | Admin         |                      |
    +---------------------------------------+-----------------+----------------------+

Enable/disable automated reminders, see :ref:`automated-routines-reminders`.

*Args*
    status (:ref:`bool-parameter-type`): New status of automated reminders.

set_automated_strikes
*********************

.. table::
    :widths: 50 25 25
    :align: left

    +---------------------------------------+-----------------+----------------------+
    | Command                               | Roles           | Channels             |
    +=======================================+=================+======================+
    | ``!set_automated_strikes <status>``   | | Leader        | Commands             |
    |                                       | | Admin         |                      |
    +---------------------------------------+-----------------+----------------------+

Enable/disable automated strikes, see :ref:`automated-routines-strikes`.

*Args*
    status (:ref:`bool-parameter-type`): New status of automated strikes.

------------------------------------------------------------------------------------------------------------------------------------

Leader Utilities
================

Various utilities available to leadership.
To see more info about these commands on Discord, use ``!help LeaderUtils``.

export
******

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!export <primary_clan_only> <include_card_levels>`` | | Elder         | Commands             |
    |                                                       | | Leader        |                      |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Export information from the database to an Excel spreadsheet. The spreadsheet contains sheets containing general info about each
user, deck usage history for the past week, kicks, stats of current river race, stats for the current season, all time stats, and
optionally card levels.

*Args*
    | primary_clan_only (:ref:`bool-parameter-type`): If True, spreadsheet will only contain data for members that are currently
        members of the primary clan. If False, then all users in the database will be included. *Defaults to True*.
    | include_card_levels (:ref:`bool-parameter-type`): Whether to include card levels of all members being exported. *Defaults to
        False*.

force_rules_check
*****************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!force_rules_check``                                | Admin           | Commands             |
    +-------------------------------------------------------+-----------------+----------------------+

Use this command after making a change to the rules that you want all members to acknowledge. All Discord members without the Admin
role will have their roles stripped and be given the Check Rules role. Once a user reacts to ClashBot's message in the Rules channel
to acknowledge that they've read the updated rules, they will be re-assigned all the roles they possessed when this command was
issued.

mention_users
*************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!mention_users <members> <channel> <message>``      | | Leader        | Commands             |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

This will send your message to the specified channel and mention the specified users. ClashBot must be a member of the specified
channel and have permission to send messages there.

*Args*
    | members (:ref:`discord-member-parameter-type`): A list of members that you want mentioned separated by spaces. Any members
        with spaces in their names must be enclosed in quotes.
    | channel (:ref:`discord-channel-parameter-type`): The channel you wish to send the message to.
    | message (:ref:`string-parameter-type`): The message you wish to send. Must be enclosed in quotes.

*Sample Usage*
    | ``!mention_users "User A" UserB#1234 UserC #general "Hello World"``
    | This will send the message "Hello World" to the #general channel and mention User A, User B, and User C.

send_reminder
*************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!send_reminder <message>``                          | | Elder         | Commands             |
    |                                                       | | Leader        |                      |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Send a reminder message to the Reminders channel and optionally specify a custom message to be sent with the reminder. This reminder
message is the same format as an :ref:`automated one<automated-routines-reminders>`. Using this command will not affect the timing
of any upcoming reminders.

*Args*
    message (:ref:`string-parameter-type`): Optionally specify the message you'd like to send with the reminder. Leave this blank to
        use the default message sent by automated reminders.

top_medals
**********

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!top_medals``                                       | | Leader        | Commands             |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Sends a list of the top three users with the most medals to the Fame channel. If there is a tie, then more than three users could be
shown.

medals_check
************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!medals_check <threshold>``                         | | Leader        | Commands             |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Sends a list of users with fewer medals than the specified threshold to the Fame channel. Any users that are members of the Discord
server will be mentioned.

*Args*
    threshold (:ref:`int-parameter-type`): Look for members of the clan with fewer medals than this threshold.

kick
****

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!kick <member>``                                    | | Elder         | Commands             |
    |                                                       | | Leader        | Kicks                |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Log a kick for the specified user with the current date. This does not kick them from the Discord server, just logs that you kicked
them from the clan. This can be used to log kicks for any users in the database regardless of whether they are on the Discord
server.

*Args*
    member (:ref:`user-parameter-type`): The user to log a kick for.

undo_kick
*********

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!undo_kick <member>``                               | | Elder         | Commands             |
    |                                                       | | Leader        | Kicks                |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Undo the most recent kick logged for the specified user. The user does not need to be a member of the Discord server.

*Args*
    member (:ref:`user-parameter-type`): The user to undo the most recent kick for.

------------------------------------------------------------------------------------------------------------------------------------

Member Utilities
================

Various utilities available to all members of the Discord server. Any commands that say they can be used in any channel are unusable
in the Welcome and Rules channels.
To see more info about these commands on Discord, use ``!help MemberUtils``.

river_race_status
*****************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!river_race_status <show_predictions>``             | No restrictions | Any                  |
    +-------------------------------------------------------+-----------------+----------------------+

Show a list of all clans in the current River Race and how many decks they still have available to use today.

*Args*
    show_predictions (:ref:`bool-parameter-type`): Whether to include a prediction for the outcome at the end of the day too. This
        prediction uses the same logic as `predict`_ assuming each clan uses all possible remaining decks at their current average
        medals per deck.

predict
*******

.. table::
    :widths: 50 25 25
    :align: left

    +---------------------------------------------------------------------+-----------------+----------------------+
    | Command                                                             | Roles           | Channels             |
    +=====================================================================+=================+======================+
    | ``!predict <use_historical_win_rates> <use_historical_deck_usage>`` | No restrictions | Any                  |
    +---------------------------------------------------------------------+-----------------+----------------------+

Predicts the outcome at the end of the current Battle Day. Any clans that have already crossed the finish line will be omitted from
the predicted outcomes. If the primary clan is not predicted to finish first, then show what win rate is required to match the
predicted score of first place assuming the primary clan uses all possible remaining decks.

*Args*
    | use_historical_win_rates (:ref:`bool-parameter-type`): If True, calculate each clan's average medals per deck in the current
        season and multiply this by the number of decks expected to use the rest of the day to determine their predicted score. If
        False, assume each clan will complete the rest of their battles with a 50% win rate (165.625 medals/deck).
    | use_historical_deck_usage (:ref:`bool-parameter-type`): If True, assume each clan will use use their average number of decks
        used per day (if they've already exceeded their average, then assume they use 25% of their remaining decks). If False,
        assume each clan uses all possible remaining decks for the day.

*Explanation*
    At the end of each Battle Day, ClashBot logs how many decks each clan participating in your clan's River Race used, along with
    the total number of medals they earned. These values are continually added to throughout a season to determine each clans
    average medals per deck and average number of decks used per day

    .. math::
        \bar{M} = \frac{M_{total}}{D_{total}}

    .. math::
        \bar{D} = \frac{D_{total}}{n}

    where :math:`\bar{M}` is the average number of medals earned per deck, :math:`\bar{D}` is the average number of decks used
    per day, :math:`M_{total}` is the total medals earned, :math:`D_{total}` is the total number of decks used, and :math:`n` is the
    number of Battle Days. :math:`\bar{D}`, along with the number of decks a clan has used today :math:`D_{today}`, is then used to
    determine the expected number expected number of decks that that clan will use for the remainder of the day. A clan's predicted
    score is then calculated as such

    .. math::
        P = \bar{M}(\bar{D} - D_{today}) + M_{today}

    where :math:`M_{today}` is the number of medals earned so far today.

    The win rates shown are not the actual win rates of each clan, but an approximation of each clan's win rate given their
    :math:`\bar{M}`. These win rates assume the following:

    * Players maintain the same win rate across any PvP match (duels, regular matches, and special matches)
    * Players always play a duel, followed by either one or two regular/special matches
    * No boat attacks are performed

    Since winning a duel match gives 250 medals vs 200 for a regular/special win, and any loss will result in 100 medals regardless
    of game mode, these assumptions lead to the highest expected medals per deck. Without any data, an approximate value for
    :math:`\bar{M}` can be calculated as a function of win rate :math:`r`. These calculations are calculated by approximating the
    number of medals earned by a single player in one Battle Day with the assumptions made above. First, the expected number of duel
    matches played at win rate :math:`r`

    .. math::
        n_{duel} = \sum_{k=0}^{1} r^k(2+k){1 + k \choose k}(1-r)^2 + \sum_{k=0}^{1} r^2(2+k){1 + k \choose k}(1-r)^k

    .. math::
        n_{duel} = \sum_{k=0}^{1} (2+k){1 + k \choose k}[r^k(1-r)^2 + r^2(1-r)^k]

    .. math::
        n_{duel} = 2(-r^2 + r + 1)

    where :math:`n_{duel}` is the expected number of duel matches played. The expected number of regular/special matches played
    :math:`n_{regular}` then is simply

    .. math::
        n_{regular} = 4 - n_{duel}

    since only 4 decks total can be used per day. Next, the expected number of medals per individual duel match and regular/special
    match must be calculated for win rate :math:`r`:

    .. math::
        m_{duel} = 250r + 100(1 - r) = 150r + 100

    .. math::
        m_{regular} = 200r + 100(1 - r) = 100r + 100

    Finally, the expected number of medals per deck at a given win rate can be calculated as

    .. math::
        m = \frac{m_{duel} * n_{duel} + m_{regular} * n_{regular}}{4}

    .. math::
        m = \frac{(150r + 100)[2(-r^2 + r + 1)] * (100r + 100)[4 - 2(-r^2 + r + 1)]}{4}

    .. math::
        m = -25r^3 + 25r^2 + 125r + 100

    The win rates shown in the outcome of the ``predict`` command are calculated by substituting :math:`\bar{M}` for :math:`m` in
    the polynomial above and solving for its root between [0, 1].

set_reminder_time
*****************

.. table::
    :widths: 50 25 25
    :align: left

    +---------------------------------------------------------------------+-----------------+----------------------+
    | Command                                                             | Roles           | Channels             |
    +=====================================================================+=================+======================+
    | ``!set_reminder_time <reminder_time>``                              | No restrictions | Any                  |
    +---------------------------------------------------------------------+-----------------+----------------------+

This is how Discord members can choose which automated reminder to receive. See :ref:`automated-routines-reminders` for when these
are sent out. Users are assigned to receive US reminders by default.

*Args*
    reminder_time (:ref:`string-parameter-type`): Which time you want to receive notifications. Valid options are "US" or "EU".

vacation
********

.. table::
    :widths: 50 25 25
    :align: left

    +---------------------------------------------------------------------+-----------------+----------------------+
    | Command                                                             | Roles           | Channels             |
    +=====================================================================+=================+======================+
    | ``!vacation``                                                       | No restrictions | Time Off             |
    +---------------------------------------------------------------------+-----------------+----------------------+

Use this to toggle your vacation status. Users on vacation will be omitted from automated reminders and from receiving strikes until
the end of the current River Race.

update
******

.. table::
    :widths: 50 25 25
    :align: left

    +---------------------------------------------------------------------+-----------------+----------------------+
    | Command                                                             | Roles           | Channels             |
    +=====================================================================+=================+======================+
    | ``!update``                                                         | No restrictions | Any                  |
    +---------------------------------------------------------------------+-----------------+----------------------+

Use this to update your information in the database and make any necessary role adjustments. To see what gets updated, refer to 
:ref:`automated-routines-update-changes`. This can be useful if you received the Visitor role due to joining the Discord server
prior to joining the primary clan. Once you join the primary clan, using this command would result in you losing the Visitor role
and gaining the Member role. This could also be used to receive the Elder role if you have received a promotion to elder status
in-game but have not yet received the role. Alternatively, all members that need to be updated are updated every 8 hours and any
changes performed by this command would be performed then automatically. See :ref:`automated-routines-update`.

strikes
*******

.. table::
    :widths: 50 25 25
    :align: left

    +---------------------------------------------------------------------+-----------------+----------------------+
    | Command                                                             | Roles           | Channels             |
    +=====================================================================+=================+======================+
    | ``!strikes``                                                        | No restrictions | Any                  |
    +---------------------------------------------------------------------+-----------------+----------------------+

Use this to view how many non-permanent strikes you have currently accumulated.

stats
*****

.. table::
    :widths: 50 25 25
    :align: left

    +---------------------------------------------------------------------+-----------------+----------------------+
    | Command                                                             | Roles           | Channels             |
    +=====================================================================+=================+======================+
    | ``!stats``                                                          | No restrictions | Any                  |
    +---------------------------------------------------------------------+-----------------+----------------------+

Use this to view your stats in River Race battles played while you were a member of the primary clan.

------------------------------------------------------------------------------------------------------------------------------------

Status Reports
==============

Various reports that leadership can use to check the status of the current River Race and the primary clan's members.
To see more info about these commands on Discord, use ``!help StatusReports``.

decks_report
************

.. table::
    :widths: 50 25 25
    :align: left

    +---------------------------------------------------------------------+-----------------+----------------------+
    | Command                                                             | Roles           | Channels             |
    +=====================================================================+=================+======================+
    | ``!decks_report``                                                   | | Elder         | Commands             |
    |                                                                     | | Leader        |                      |
    |                                                                     | | Admin         |                      |
    +---------------------------------------------------------------------+-----------------+----------------------+

This will give a summary of your clan's participation on the current Battle Day. The following information is provided:

* How many users have participated so far today and how many decks they've used.
* Any users that have not used all 4 decks today and how many decks they still have available to them.
* Any users that battled for your clan today but are not currently members of the clan.
* Any users that are locked out of battling today due to your clan having reached 50 daily participants already.
* A warning if there are more members of your clan with 4 decks remaining than there are spots left for them to participate today.

medals_report
*************

.. table::
    :widths: 50 25 25
    :align: left

    +---------------------------------------------------------------------+-----------------+----------------------+
    | Command                                                             | Roles           | Channels             |
    +=====================================================================+=================+======================+
    | ``!medals_report <threshold>``                                      | | Elder         | Commands             |
    |                                                                     | | Leader        |                      |
    |                                                                     | | Admin         |                      |
    +---------------------------------------------------------------------+-----------------+----------------------+

Behaves similarly to `medals_check`_ but does not send anything to the Fame channel. Instead, this will display a list of users in
your clan below the specified threshold.

*Args*
    threshold (:ref:`int-parameter-type`): Look for members of the clan with fewer medals than this threshold.

player_report
*************

.. table::
    :widths: 50 25 25
    :align: left

    +---------------------------------------------------------------------+-----------------+----------------------+
    | Command                                                             | Roles           | Channels             |
    +=====================================================================+=================+======================+
    | ``!player_report <member>``                                         | | Elder         | Commands             |
    |                                                                     | | Leader        |                      |
    |                                                                     | | Admin         |                      |
    +---------------------------------------------------------------------+-----------------+----------------------+

Check a user's information saved in the database along with their past week of daily deck usage. Includes

* In-game name
* Tag
* Strikes and permanent strikes
* Number of kicks and date of most recent kick
* Discord name
* Clan affiliation and role
* Vacation status
* Database status

*Args*
    member (:ref:`user-parameter-type`): Show this user's data.

stats_report
************

.. table::
    :widths: 50 25 25
    :align: left

    +---------------------------------------------------------------------+-----------------+----------------------+
    | Command                                                             | Roles           | Channels             |
    +=====================================================================+=================+======================+
    | ``!stats_report <member>``                                          | | Elder         | Commands             |
    |                                                                     | | Leader        |                      |
    |                                                                     | | Admin         |                      |
    +---------------------------------------------------------------------+-----------------+----------------------+

Check the specified user's River Race statistics. Returns the same data as if the specified user used the ``!stats`` command.

*Args*
    member (:ref:`user-parameter-type`): Show this user's stats.

------------------------------------------------------------------------------------------------------------------------------------

Strikes
=======

Commands for leadership to give/remove strikes and monitor users with strikes. For more information on the difference between the
two types of strikes, see :ref:`strike-types`.
To see more info about these commands on Discord, use ``!help Strikes``.

give_strike
***********

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!give_strike <member>``                             | | Leader        | Commands             |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Give 1 strike to the specified user.

*Args*
    member (:ref:`user-parameter-type`): User to give a strike to.


give_strikes
************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!give_strikes <members>``                           | | Leader        | Commands             |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Give 1 strike to each of the specified users.

*Args*
    members (:ref:`user-parameter-type`): List of users separated by spaces to give a strike to.

remove_strike
*************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!remove_strike <member>``                           | | Leader        | Commands             |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Remove 1 strike and 1 permanent strike from the specified user.

*Args*
    member (:ref:`user-parameter-type`): User to remove strike from.

remove_strikes
**************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!remove_strikes <members>``                         | | Leader        | Commands             |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Remove 1 strike from each of the specified users.

*Args*
    members (:ref:`user-parameter-type`): List of users separated by spaces to remove a strike from.

reset_all_strikes
*****************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!reset_all_strikes``                                | | Leader        | Commands             |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Reset non-permanent strikes to 0 for all users. Permanent strikes are unaffected.

strikes_report
**************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!strikes_report``                                   | | Elder         | Commands             |
    |                                                       | | Leader        |                      |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Get a report of all users that have non-permanent strikes. Two tables are displayed, one of users with strikes that are in your
clan and one of users with strikes not in your clan.

upcoming_strikes
****************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!upcoming_strikes``                                 | | Elder         | Commands             |
    |                                                       | | Leader        |                      |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Get a report of users in your clan who will receive a strike at the end of the current River Race based on participation up until
the start of the current Battle Day. See :ref:`automated-routines-strikes` for more information about how automated strikes are
calculated.

------------------------------------------------------------------------------------------------------------------------------------

Update Utilities
================

Various utilities that leadership can use to update the status of members on the Discord server.
To see more info about these commands on Discord, use ``!help UpdateUtils``.

update_member
*************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!update_member <member>``                           | | Leader        | Commands             |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Update the specified member. Behaves the same way as if that user used the `update`_ command.

*Args*
    member (:ref:`discord-member-parameter-type`): Member to update.

update_all_members
******************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!update_all_members``                               | | Leader        | Commands             |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Manually perform an automated update of all members. Not all members will actually be updated, only the ones that are determined to
need an update. See :ref:`automated-routines-update`.

reset_member
************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!reset_member <member>``                            | | Admin         | Commands             |
    +-------------------------------------------------------+-----------------+----------------------+

Remove the specified user from the database, clear their roles, and assign them the New role.

*Args*
    member (:ref:`discord-member-parameter-type`): Member to reset.

reset_all_members
*****************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!reset_all_members <confirmation>``                 | | Admin         | Commands             |
    +-------------------------------------------------------+-----------------+----------------------+

Completely clear the database of any user data, clear roles from all users, and assign everyone the New role. This command is most
useful for first time setup of ClashBot on a new Discord server.

*Args*
    confirmation (:ref:`string-parameter-type`): A confirmation message is needed to avoid accidentally using this command.

------------------------------------------------------------------------------------------------------------------------------------

Vacation
========

Commands for leadership to check and modify vacation status of members of the Discord server.
To see more info about these commands on Discord, use ``!help Vacation``.

set_vacation
************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!set_vacation <member> <status>``                   | | Elder         | Commands             |
    |                                                       | | Leader        |                      |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Manually set the vacation status of the specified member.

*Args*
    | member (:ref:`discord-member-parameter-type`): Member to change vacation status of.
    | status (:ref:`bool-parameter-type`): Vacation status to set for specified member.

vacation_list
*************

.. table::
    :widths: 50 25 25
    :align: left

    +-------------------------------------------------------+-----------------+----------------------+
    | Command                                               | Roles           | Channels             |
    +=======================================================+=================+======================+
    | ``!vacation_list``                                    | | Elder         | Commands             |
    |                                                       | | Leader        |                      |
    |                                                       | | Admin         |                      |
    +-------------------------------------------------------+-----------------+----------------------+

Get a list of all members that are currently on vacation.
