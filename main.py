import discord
import os
import json
from pathlib import Path
from discord.ext import commands


BASE_DIR = Path(__file__).resolve().parent
MODULES_DIR = BASE_DIR / "Modules"
CONFIG_PATH = BASE_DIR / "resources" / "apikey.json"


def load_config():
    if not CONFIG_PATH.exists():
        return {}

    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        return json.load(config_file)


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

    data = load_config()
    if not data:
        raise RuntimeError(
            "Discord token not found. Set DISCORD_TOKEN or create resources/apikey.json "
            "from resources/apikey.example.json."
        )

    token = data.get("token")
    if not token:
        raise RuntimeError("Missing 'token' in resources/apikey.json.")

    return token


def parse_guild_ids(value):
    if value is None or value == "":
        return []

    if isinstance(value, int):
        return [value]

    if isinstance(value, str):
        return [int(part.strip()) for part in value.split(",") if part.strip()]

    return [int(guild_id) for guild_id in value]


def get_app_command_guild_ids():
    env_value = os.getenv("DISCORD_GUILD_IDS") or os.getenv("DISCORD_GUILD_ID")
    if env_value:
        return parse_guild_ids(env_value)

    config = load_config()
    return parse_guild_ids(config.get("guild_ids") or config.get("guild_id"))


def get_local_command_suffix():
    suffix = os.getenv("DISCORD_LOCAL_COMMAND_SUFFIX")
    if suffix:
        return suffix

    config = load_config()
    return config.get("local_command_suffix", "local")


class MarketplaceAlertBot(commands.Bot):
    def copy_commands_to_guild_with_suffix(self, guild, suffix):
        for command in self.tree.get_commands():
            local_command = command._copy_with(
                parent=None,
                binding=command.binding,
                set_on_binding=False,
            )
            local_command.name = f"{command.name}-{suffix}"
            local_command.description = f"[{suffix}] {command.description}"
            self.tree.add_command(local_command, guild=guild, override=True)

    async def setup_hook(self):
        for extension in iter_extensions():
            await self.load_extension(extension)

        guild_ids = get_app_command_guild_ids()
        if guild_ids:
            suffix = get_local_command_suffix()
            for guild_id in guild_ids:
                guild = discord.Object(id=guild_id)
                self.copy_commands_to_guild_with_suffix(guild, suffix)
                synced = await self.tree.sync(guild=guild)
                command_names = ", ".join(command.name for command in synced)
                print(f"Synced {len(synced)} local slash command(s) to guild {guild_id}: {command_names}")
        else:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} global slash command(s). Global updates can take up to an hour.")


intents = discord.Intents.all()
client = MarketplaceAlertBot(command_prefix=".", intents=intents)

@client.event
async def on_ready():
    print('Logged on as {0.user}'.format(client))


if __name__ == "__main__":
    client.run(get_bot_token())
