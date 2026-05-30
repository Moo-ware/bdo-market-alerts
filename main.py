import discord
import os
import json
from pathlib import Path
from discord.ext import commands


BASE_DIR = Path(__file__).resolve().parent
MODULES_DIR = BASE_DIR / "Modules"
CONFIG_PATH = BASE_DIR / "resources" / "apikey.json"


def iter_extensions():
    for path in sorted(MODULES_DIR.rglob("*.py")):
        if path.name.startswith("_"):
            continue

        module_path = path.relative_to(BASE_DIR).with_suffix("")
        yield ".".join(module_path.parts)


def get_bot_token():
    token = os.getenv("DISCORD_TOKEN")
    if token:
        return token

    if not CONFIG_PATH.exists():
        raise RuntimeError(
            "Discord token not found. Set DISCORD_TOKEN or create resources/apikey.json "
            "from resources/apikey.example.json."
        )

    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        data = json.load(config_file)

    token = data.get("token")
    if not token:
        raise RuntimeError("Missing 'token' in resources/apikey.json.")

    return token


class MarketplaceAlertBot(commands.Bot):
    async def setup_hook(self):
        for extension in iter_extensions():
            await self.load_extension(extension)


intents = discord.Intents.all()
client = MarketplaceAlertBot(command_prefix=".", intents=intents)

@client.event
async def on_ready():
    print('Logged on as {0.user}'.format(client))


if __name__ == "__main__":
    client.run(get_bot_token())


