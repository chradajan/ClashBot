.. _automated-routines:

******************
Automated Routines
******************

.. _automated-routines-reminders:

Automated Reminders
===================

On Battle Days, ClashBot will automatically notify any users that have not completed all four of their battles for the day. These
reminders go out at 19:00 UTC (EU), 02:00 UTC (US), and then 08:00 UTC (Everyone). A message listing all users of the primary clan
along with how many decks they have left will be sent to the Reminders channel. Any users that are Discord members will be mentioned
in this message.

.. _automated-routines-strikes:

Automated Strikes
=================

At the end of each River Race, ClashBot assigns strikes to users that did not complete enough battles. Users are expected to use all
4 decks each Battle Day that they are in the clan. If the clan crosses the finish line early after day three, then participation on
the final day is optional.

ClashBot determines how many total decks are required to not receive a strike based on when users join the clan. If someone is an
active member of the clan at the beginning of the first Battle Day or joins the clan anytime on the first day, they will be expected
to use 16 decks (12 if the clan crosses early). Someone that joins on the second day will only be expected to use 12 decks (8 if the
clan crosses early). When the clan finishes early, the final day is completely ignored. This means that if a user joins day 1, uses
8/12 possible decks on days 1-3, and uses 4 decks on day 4, they will still receive a strike even if the clan finished early despite
having used 12 decks total during the River Race.

When automated strikes are assigned, they are only given to users who are currently active members of the primary clan. ClashBot
tracks when people join the clan throughout each River Race, and will detect anyone who meets the criteria to receive a strike but
is not currently in the clan. For each user like this that is detected, a message will be sent to the Commands channel stating that
user's name, deck usage, and when they started participating in the most recent River Race. Anyone with the Leader role can use the
reactions on this message to give that user a strike if they should actually receive one.

*Note: The API does not have any way to detect if a participant in your clan had previously battled for a different clan before
joining. If someone joins in the middle of a River Race and can't battle due to having battled for another clan already, they will
still receive an automated strike. Their strikes will need to be manually adjusted.* 

Clear Vacation
==============

In addition to assigning strikes at the end of each River Race, every member will have their vacation status reset.

.. _automated-routines-update:

Automated Member Updates
========================

Every 8 hours, ClashBot goes through each member of the Discord server and determines who needs to be updated. Any users that are
updated will have their entry in the database updated and their roles adjusted.

.. _automated-routines-update-criteria:

Who gets updated?
*****************

    Members of the Discord server that meet any of the following criteria will be updated:

    * Their saved Discord username does not match their current Discord username
    * They possess the Member role but are not currently a member of the primary clan
    * They are a member of the primary clan and meet and of these criteria:
        * Their Discord nickname does not match their current in-game name
        * Their saved clan role in the database does not match their current clan role
        * They possess the visitor role

.. _automated-routines-update-changes:

What gets updated?
******************

    When a member is updated, the following updates will occur:

    * The following fields in the database are updated to reflect their current values:
        * In-game name
        * Tag
        * Discord name
        * Clan affiliation and role
        * Database status
    * If they are a member of the primary clan and had never previously joined it, the current time is marked as their initial join
      date
    * If this is their first time joining the primary clan in the current River Race/season, then the current time is marked as
      their tracking time for when they started participation in the race/season
    * Role adjustments are made as needed
        * Anyone in the primary clan should possess the Member role
        * Anyone Elders, Coleaders, or Leader of the primary clan should posses the Elder role
        * Anyone not in the primary clan should possess the Visitor role
    * Their Discord nickname will be updated to match their in-game name
        * ClashBot does not have permission to update Admin nicknames, so Admins must do this manually

Daily Reset and Deck Usage Tracking
===================================

In order to determine how many decks members use each day, ClashBot needs to detect when exactly the daily reset occurs since the
timing of this fluctuates. This is accomplished by looking at the primary clan's combined deck usage every minute during the hour
that the reset could occur and checking if the total usage has dropped since the previous check. Once a drop is detected indicating
that the daily reset has occurred, all members of the primary clan will have their deck usage for the day logged in the database.
Anyone not in the primary clan will have 0 decks logged for them.

When the daily reset immediately before the first Battle Day occurs, ClashBot needs to prepare the database to start tracking for
the upcoming Battle Days. The River Race stats table that tracks performance in the most recent River Race will be reset. If it's
the start of a new season, then the season stats table will be reset too.

Performance Tracking
====================

ClashBot automatically tracks performance in River Race battles on Battle Days for each user in the primary clan. Tracking checks
occur hourly and check the battle logs of any users who have acquired medals since the most recent check. Wins and losses in all
River Race match types performed while in the primary clan are counted. Any user can view their own win/loss stats by using the
``!stats`` command. Leadership can check the stats of any user through the use of the ``!stats_report`` and ``!export`` commands.

.. _automated-routines-kick-parsing:

Kick Image Parsing
==================

When kicking a member from the clan, you can take a screenshot of the dialog menu that pops up in-game to kick them and provide a
message for why they were kicked. You can then upload this screenshot to the Kicks channel and ClashBot will automatically parse out
the user who is being kicked. It will send a message you can react to in order to confirm that the person was kicked and that the
kick should be logged. This is a convenient alternative to manually using the ``!kick`` command.

New Member Info
===============

When a new user joins the Discord server and enters their player tag, ClashBot will send a message to the Leader Info channel with
the new user's level, trophies, best trophies, and card collection information.
