# Real-Time Marketplace Alert System

A Python Discord bot that monitors the Black Desert Online Central Market registration queue and sends personalized item alerts to subscribed users.

The bot polls a live marketplace endpoint, normalizes queue records, compares new records against user subscriptions stored in SQLite, and delivers notifications through Discord direct messages.

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
|   `-- BDO/
|       |-- marketalert.py      # Alert menu, subscription DB logic, DM delivery
|       |-- BDOinformation.py   # Queue and boss timer commands
|       `-- guildspy.py         # Guild member lookup and snapshot comparison
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
$env:DISCORD_GUILD_IDS = "your_test_server_id"
```

or create a local config file from the template:

```powershell
copy resources\apikey.example.json resources\apikey.json
```

Then edit `resources/apikey.json` with your token and development Discord server id. `resources/apikey.json` is intentionally ignored by Git.

Guild ids are optional, but recommended while developing because guild slash command sync is immediate. If no guild id is configured, slash commands sync globally and may take time to appear in Discord.

When guild ids are configured, the bot syncs development copies with a `-local` suffix such as `/alert-local` and `/guild-local`. This keeps them distinct if global slash commands also exist in the same server.

Run the bot:

```powershell
python main.py
```

The bot currently requests all Discord intents. In the Discord Developer Portal, enable the privileged intents required by your server and command usage. Prefix commands require Message Content Intent. Slash commands require the bot to be invited with the `bot` and `applications.commands` OAuth2 scopes.

## Commands

- `/alert` - open the marketplace alert management menu.
- `.queue` or `.q` - show the current Central Market registration queue.
- `.boss` or `.next` - show upcoming boss spawns.
- `.boss <name>` - show the next spawn for a specific boss.
- `/guild <guild_name>` - fetch and compare BDO guild member snapshots.

## Current Status

The alert menu, database-backed subscriptions, marketplace matching logic, and Discord DM delivery are present. The live polling task in `marketalert.py` is currently commented out so it is not accidentally run during cleanup. Before re-enabling it, review the Central Market endpoint behavior, Discord rate limits, database snapshot freshness, and polling interval.
