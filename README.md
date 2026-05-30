# Real-Time Marketplace Alert System

A Python Discord bot that monitors the Black Desert Online Central Market registration queue and sends personalized item alerts to subscribed users.

This project was built around a practical event-driven workflow: poll a live marketplace endpoint, normalize queue records, compare new records against user subscriptions stored in SQLite, and deliver real-time notifications through Discord direct messages.

## Highlights

- Polls the BDO Central Market waitlist API for newly registered marketplace items.
- Stores per-user alert subscriptions in a normalized SQLite schema.
- Matches marketplace events against item id, enhancement level, and alert type.
- Uses Discord slash commands, modals, select menus, buttons, embeds, and DMs for the user workflow.
- Includes supporting BDO utilities such as boss timers, queue lookup, and guild membership snapshots.

## Tech Stack

- Python
- discord.py
- SQLite
- REST APIs / HTTP requests
- BeautifulSoup for guild page parsing
- fuzzywuzzy for item-name matching

## Core Flow

1. A user opens the alert menu with `/alert`.
2. The bot loads that user's active subscriptions from SQLite.
3. The user creates an alert by entering an enhancement level and item name.
4. Fuzzy matching helps map user input to a known market item.
5. The selected alert is saved to `AlertList`.
6. The marketplace watcher polls the Central Market waitlist.
7. New queue records are matched against saved subscriptions.
8. Matching users receive a Discord DM with item, enhancement, price, and live-in time.

## Repository Layout

```text
.
|-- main.py                     # Bot entrypoint and cog loading
|-- Modules/
|   |-- BDO/
|   |   |-- marketalert.py      # Alert menu, subscription DB logic, DM delivery
|   |   |-- BDOinformation.py   # Queue and boss timer commands
|   |   `-- guildspy.py         # Guild member lookup and snapshot comparison
|   |-- Utilities.py            # General Discord utility commands
|   `-- fun.py                  # Optional OpenAI / fun commands
|-- resources/
|   |-- apikey.example.json     # Local config template
|   |-- alerts.db               # SQLite alert/item snapshot
|   |-- guilds.db               # SQLite guild snapshot cache
|   `-- itemID.csv              # BDO item id reference data
`-- utils/
    |-- functions.py            # API calls, time helpers, matching helpers
    `-- marketwatcher.py        # Experimental watcher loop
```

## Setup

Create a virtual environment and install dependencies:

```powershell
pip install -r requirements.txt
```

Configure the Discord bot token with either an environment variable:

```powershell
$env:DISCORD_TOKEN = "your_discord_bot_token"
```

or create a local config file from the template:

```powershell
copy resources\apikey.example.json resources\apikey.json
```

Then edit `resources/apikey.json` with your token. `resources/apikey.json` is intentionally ignored by Git.

Run the bot:

```powershell
python main.py
```

The bot currently requests all Discord intents. In the Discord Developer Portal, enable the privileged intents required by your server and command usage.

## Commands

- `/alert` - open the marketplace alert management menu.
- `.queue` or `.q` - show the current Central Market registration queue.
- `.boss` or `.next` - show upcoming boss spawns.
- `.boss <name>` - show the next spawn for a specific boss.
- `/guild <guild_name>` - fetch and compare BDO guild member snapshots.
- `.ping` - latency check.
- `/avatar` - display a user's avatar.

## Project Status

This is a revived portfolio project. The core marketplace-alert architecture is present, but the live polling task in `marketalert.py` is currently commented out so it is not accidentally run while the project is being cleaned up. To re-enable production-style alerting, review the Central Market endpoint behavior, Discord rate limits, database snapshot freshness, and the polling interval before uncommenting `self.check_waitlist.start()`.

## Recruiter-Facing Summary

This project demonstrates backend Python development, API integration, SQL-backed event matching, Discord API usage, and practical automation. It is especially relevant for roles involving backend systems, data ingestion, alerting workflows, automation, and data-oriented application logic.
