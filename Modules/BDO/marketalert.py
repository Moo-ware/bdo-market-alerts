import asyncio
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

from utils.functions import findItems, matchEnhancement


last_waitlist = []  # Stores the last waitlist processed

ALERT_LIMIT = 5
ALERT_TYPE_QUEUE = 1
ALERT_COLOR = 0xFE9A9A
ERROR_COLOR = 0xFF0000
MENU_THUMBNAIL_URL = "https://cdn.discordapp.com/attachments/629036668531507222/1079318649325756498/78796e7f-eaa1-4f7e-abb6-099499a807ea.png"

CREATE_ALERT_CUSTOM_ID = "marketalert:create"
REMOVE_ALERT_CUSTOM_ID = "marketalert:remove"

ENHANCEMENT_CHOICES = (
    ("Base", 0),
    ("PRI", 1),
    ("DUO", 2),
    ("TRI", 3),
    ("TET", 4),
    ("PEN", 5),
)


def enhancement_name(e_level):
    for name, level in ENHANCEMENT_CHOICES:
        if level == e_level:
            return name
    return str(e_level)


def truncate_select_label(value):
    return value if len(value) <= 100 else value[:97] + "..."


def avatar_url(user):
    return user.display_avatar.url


async def safe_delete_message(message):
    if message is None:
        return

    try:
        await message.delete()
    except discord.HTTPException:
        pass


class MarketAlert(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Enable below when ready to start the live polling task.
        # self.check_waitlist.start()

    def cog_unload(self):
        # Enable below when the live polling task is restored.
        # self.check_waitlist.cancel()
        pass

    @app_commands.command(name="alert", description="Open the marketplace alert menu")
    async def alertmenu(self, interaction: discord.Interaction):
        user_info = await User(interaction.user.id).get_user()
        view = AlertMenuView(interaction.user, user_info)
        await interaction.response.send_message(embed=view.create_embed(), view=view)
        view.message = await interaction.original_response()

    # Disabled for now. This is the main loop for checking the marketplace waitlist.
    """@tasks.loop(seconds=25)
    async def check_waitlist(self):
        global last_waitlist
        current_list = await GetWaitlist()
        list_for_db = await waitlist_comparison(last_waitlist, current_list)
        user_id_todm = await database().find_user_with_item(list_for_db)
        await DM(list_for_db).send_dm(user_id_todm, self.bot)
        last_waitlist = current_list"""


async def setup(bot):
    await bot.add_cog(MarketAlert(bot))


async def waitlist_comparison(old, new):
    if len(old) == 0:
        return new
    if len(new) == 0:
        return []

    new_items = []
    for item in new:
        found_dupe = False
        for previous_item in old:
            if len(list(set(previous_item).symmetric_difference(set(item)))) == 0:
                found_dupe = True
                break
        if found_dupe is False:
            new_items.append(item)

    return new_items


class DM:
    def __init__(self, item):
        self.item = item

    async def send_dm(self, users, bot):
        for index, user_ids in enumerate(users):
            if len(user_ids) == 0:
                continue

            for user_id in user_ids:
                user = bot.get_user(user_id[0])
                if user is not None:
                    embed = await self.create_dm_embed(self.item[index])
                    await user.send(embed=embed)

    async def create_dm_embed(self, item):
        embed = discord.Embed(
            title=f"{await matchEnhancement(item[2])}: {item[1]}",
            color=ALERT_COLOR,
        ).add_field(name="Price:", value="{:,}".format(item[4]), inline=True)
        timestamp = str(item[3])[0:10]
        embed.add_field(name="Live in:", value=f"<t:{int(timestamp)}:R>", inline=True)
        return embed


# Database actions
class UserDB:
    async def get_user_from_db(self, userid):
        connection = sqlite3.connect("resources/alerts.db")
        cursor = connection.cursor()
        rows = cursor.execute(
            "SELECT AlertList.item_id, AlertList.enhancement_level, Enhancement.e_name, AlertList.price, QueueItems.item_name, AlertTypes.alert_type "
            "FROM AlertList "
            "INNER JOIN QueueItems ON QueueItems.item_id = AlertList.item_id AND QueueItems.e_level IN (AlertList.enhancement_level, AlertList.enhancement_level + 15) "
            "INNER JOIN Enhancement ON AlertList.enhancement_level = Enhancement.elevel "
            "INNER JOIN AlertTypes ON AlertTypes.alert_id = AlertList.alert_id "
            "WHERE user_id = ?",
            (userid,),
        ).fetchall()
        cursor.close()
        connection.close()
        return rows

    async def save_user_to_db(self, userid, itemid, elevel, price, alert_id):
        if price == "NULL":
            price = None

        connection = sqlite3.connect("resources/alerts.db")
        cursor = connection.cursor()
        cursor.execute("INSERT INTO AlertList VALUES (?, ?, ?, ?, ?)", (userid, itemid, elevel, price, alert_id))
        connection.commit()
        cursor.close()
        connection.close()

    async def remove_item_from_user_db(self, userid, items):
        connection = sqlite3.connect("resources/alerts.db")
        cursor = connection.cursor()
        cursor.executemany(
            "DELETE from AlertList WHERE user_id = ? AND item_id = ? AND enhancement_level = ? AND alert_id = ?",
            [(userid, item[0], item[1], item[2]) for item in items],
        )
        connection.commit()
        cursor.close()
        connection.close()

    async def remove_all_item_from_user_db(self, userid):
        connection = sqlite3.connect("resources/alerts.db")
        cursor = connection.cursor()
        cursor.execute("DELETE from AlertList WHERE user_id = ?", (userid,))
        connection.commit()
        cursor.close()
        connection.close()


class User:
    def __init__(self, userid):
        self.userid = userid
        self._db = UserDB()

    async def get_user(self):
        return await self._db.get_user_from_db(self.userid)

    async def save_user(self, itemid, elevel, price, alert_id):
        await self._db.save_user_to_db(self.userid, itemid, elevel, price, alert_id)

    async def remove_item_from_user(self, items):
        await self._db.remove_item_from_user_db(self.userid, items)

    async def remove_all_item_from_user(self):
        await self._db.remove_all_item_from_user_db(self.userid)


class database:
    async def get_enhancement_level(self, name):
        connection = sqlite3.connect("resources/alerts.db")
        cursor = connection.cursor()
        level = cursor.execute("SELECT elevel FROM Enhancement WHERE e_name = ?", (name,)).fetchall()
        cursor.close()
        connection.close()
        return level

    async def get_items_from_level(self, e_level):
        connection = sqlite3.connect("resources/alerts.db")
        cursor = connection.cursor()
        rows = cursor.execute(
            "SELECT item_id, item_name FROM QueueItems WHERE e_level = ? OR e_level = ?",
            (e_level, e_level + 15),
        ).fetchall()
        cursor.close()
        connection.close()
        return rows

    async def find_user_with_item(self, items):
        connection = sqlite3.connect("resources/alerts.db")
        cursor = connection.cursor()
        rows = []
        for item in items:
            users = cursor.execute(
                "SELECT user_id FROM AlertList WHERE item_id = ? AND enhancement_level IN (?, ?)",
                (item[0], item[2], item[2] - 15),
            ).fetchall()
            rows.append(users)
        cursor.close()
        connection.close()
        return rows


# Discord UI views
class AlertMenuView(discord.ui.View):
    def __init__(self, author, user_items):
        super().__init__(timeout=180)
        self.author = author
        self.user_items = user_items
        self.message = None
        self.sync_button_state()

    def create_embed(self):
        lines = [f"[{item[5]}] {item[2]}: {item[4]}" for item in self.user_items]
        description = "\n".join(lines) if lines else "No active alerts."
        embed = discord.Embed(
            title=f"Welcome back {self.author.name}!",
            description=f"**My active alerts**: `{len(self.user_items)}/{ALERT_LIMIT} used`\n```{description}```",
            color=ALERT_COLOR,
        )
        embed.set_author(name=self.author.name, icon_url=avatar_url(self.author))
        embed.set_thumbnail(url=MENU_THUMBNAIL_URL)
        return embed

    def get_button(self, custom_id):
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == custom_id:
                return item
        return None

    def sync_button_state(self):
        create_button = self.get_button(CREATE_ALERT_CUSTOM_ID)
        remove_button = self.get_button(REMOVE_ALERT_CUSTOM_ID)

        if create_button is not None:
            create_button.disabled = len(self.user_items) >= ALERT_LIMIT
        if remove_button is not None:
            remove_button.disabled = len(self.user_items) == 0

    async def set_create_enabled(self, enabled):
        create_button = self.get_button(CREATE_ALERT_CUSTOM_ID)
        if create_button is not None:
            create_button.disabled = not enabled or len(self.user_items) >= ALERT_LIMIT
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                self.message = None

    async def refresh(self):
        self.user_items = await User(self.author.id).get_user()
        self.sync_button_state()
        if self.message is not None:
            try:
                await self.message.edit(embed=self.create_embed(), view=self)
            except discord.HTTPException:
                self.message = None

    async def on_timeout(self):
        self.stop()
        await safe_delete_message(self.message)

    async def interaction_check(self, interaction):
        if interaction.user == self.author:
            return True

        await interaction.response.send_message(
            "Only the user who opened this alert menu can use it.",
            ephemeral=True,
        )
        return False

    @discord.ui.button(
        label="Create queue alert",
        row=0,
        style=discord.ButtonStyle.primary,
        custom_id=CREATE_ALERT_CUSTOM_ID,
    )
    async def create_alert_button_callback(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(ItemAlertModal(self))

    @discord.ui.button(
        label="Remove alert",
        row=0,
        style=discord.ButtonStyle.danger,
        custom_id=REMOVE_ALERT_CUSTOM_ID,
    )
    async def remove_button_callback(self, interaction: discord.Interaction, button):
        self.message = interaction.message
        await interaction.response.edit_message(view=AlertDeleteMenuView(self))

    @discord.ui.button(label="Close", row=1, style=discord.ButtonStyle.secondary)
    async def exit_button_callback(self, interaction: discord.Interaction, button):
        self.stop()
        await interaction.response.defer()
        await safe_delete_message(interaction.message)


class ItemAlertModal(discord.ui.Modal, title="Create Queue Alert"):
    def __init__(self, menu_view):
        super().__init__(timeout=120)
        self.menu_view = menu_view

        self.enhancement_level = discord.ui.Label(
            text="Enhancement level",
            component=discord.ui.RadioGroup(
                options=[
                    discord.RadioGroupOption(
                        label=name,
                        value=str(level),
                        default=level == 5,
                    )
                    for name, level in ENHANCEMENT_CHOICES
                ],
            ),
        )
        self.item_name = discord.ui.Label(
            text="Item name",
            description="Use the Central Market item name.",
            component=discord.ui.TextInput(
                placeholder="Deboreka Ring",
                min_length=2,
                max_length=100,
                required=True,
            ),
        )

        self.add_item(self.enhancement_level)
        self.add_item(self.item_name)

    async def on_submit(self, interaction: discord.Interaction):
        e_level = int(self.enhancement_level.component.value or "5")
        e_name = enhancement_name(e_level)
        item_name = self.item_name.component.value.strip()

        if not item_name:
            await interaction.response.send_message(embed=ResponseMsg.item_name_error(), ephemeral=True)
            return

        matches = await findItems(item_name, await database().get_items_from_level(e_level))

        if 1 < len(matches) <= 25:
            view = CandidateSelectView(self.menu_view, e_level, e_name, matches, item_name)
            await interaction.response.send_message(
                embed=ResponseMsg.candidate_matches(item_name, matches, interaction.user),
                view=view,
            )
            view.message = await interaction.original_response()
            await self.menu_view.set_create_enabled(False)
        elif len(matches) == 1:
            item_id, matched_name = matches[0]
            view = AlertConfirmationView(self.menu_view, e_level, e_name, item_id, matched_name)
            await interaction.response.send_message(
                embed=ResponseMsg.confirm_alert(e_name, matched_name, item_id),
                view=view,
            )
            view.message = await interaction.original_response()
            await self.menu_view.set_create_enabled(False)
        else:
            await interaction.response.send_message(
                embed=ResponseMsg.no_item_error(item_name, e_name),
                ephemeral=True,
            )


class CandidateSelect(discord.ui.Select):
    def __init__(self, menu_view, e_level, e_name, matches, search_term):
        self.menu_view = menu_view
        self.e_level = e_level
        self.e_name = e_name
        self.matches = matches
        self.search_term = search_term
        self.item_names = {str(item_id): item_name for item_id, item_name in matches}

        options = [
            discord.SelectOption(label=truncate_select_label(item_name), value=str(item_id))
            for item_id, item_name in matches
        ]
        super().__init__(
            placeholder="Select the matching item",
            max_values=1,
            min_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        item_id = self.values[0]
        item_name = self.item_names[item_id]
        view = AlertConfirmationView(
            self.menu_view,
            self.e_level,
            self.e_name,
            int(item_id),
            item_name,
            matches=self.matches,
            search_term=self.search_term,
        )
        await interaction.response.edit_message(
            embed=ResponseMsg.confirm_alert(self.e_name, item_name, item_id),
            view=view,
        )
        view.message = await interaction.original_response()


class CandidateSelectView(discord.ui.View):
    def __init__(self, menu_view, e_level, e_name, matches, search_term):
        super().__init__(timeout=60)
        self.menu_view = menu_view
        self.message = None
        self.add_item(CandidateSelect(menu_view, e_level, e_name, matches, search_term))

    async def on_timeout(self):
        self.stop()
        await safe_delete_message(self.message)
        await self.menu_view.set_create_enabled(True)

    async def interaction_check(self, interaction):
        if interaction.user == self.menu_view.author:
            return True

        await interaction.response.send_message(
            "Only the user who started this alert can use this menu.",
            ephemeral=True,
        )
        return False


class AlertConfirmationView(discord.ui.View):
    def __init__(self, menu_view, e_level, e_name, item_id, item_name, matches=None, search_term=None):
        super().__init__(timeout=30)
        self.menu_view = menu_view
        self.e_level = e_level
        self.e_name = e_name
        self.item_id = item_id
        self.item_name = item_name
        self.matches = matches
        self.search_term = search_term or item_name
        self.message = None

        if self.matches is None:
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.label == "Back to matches":
                    item.disabled = True
                    break

    async def on_timeout(self):
        self.stop()
        await safe_delete_message(self.message)
        await self.menu_view.set_create_enabled(True)

    async def interaction_check(self, interaction):
        if interaction.user == self.menu_view.author:
            return True

        await interaction.response.send_message(
            "Only the user who started this alert can use this confirmation.",
            ephemeral=True,
        )
        return False

    @discord.ui.button(label="Confirm", row=0, style=discord.ButtonStyle.success)
    async def confirm_button_callback(self, interaction: discord.Interaction, button):
        try:
            await User(interaction.user.id).save_user(self.item_id, self.e_level, "NULL", ALERT_TYPE_QUEUE)
        except sqlite3.IntegrityError:
            self.stop()
            await interaction.response.edit_message(embed=ResponseMsg.duplicate_error(), view=None)
            await self.menu_view.set_create_enabled(True)
            await asyncio.sleep(3)
            await safe_delete_message(interaction.message)
        else:
            self.stop()
            await interaction.response.edit_message(embed=ResponseMsg.add_to_db_success(), view=None)
            await self.menu_view.refresh()
            await asyncio.sleep(3)
            await safe_delete_message(interaction.message)

    @discord.ui.button(label="Back to matches", row=0, style=discord.ButtonStyle.secondary)
    async def back_to_matches_button(self, interaction: discord.Interaction, button):
        if self.matches is None:
            await interaction.response.defer()
            return

        view = CandidateSelectView(self.menu_view, self.e_level, self.e_name, self.matches, self.search_term)
        await interaction.response.edit_message(
            embed=ResponseMsg.candidate_matches(self.search_term, self.matches, interaction.user),
            view=view,
        )
        view.message = await interaction.original_response()

    @discord.ui.button(label="Search again", row=1, style=discord.ButtonStyle.primary)
    async def search_again_button_callback(self, interaction: discord.Interaction, button):
        self.stop()
        await interaction.response.send_modal(ItemAlertModal(self.menu_view))
        await self.menu_view.set_create_enabled(True)
        await safe_delete_message(interaction.message)

    @discord.ui.button(label="Cancel", row=1, style=discord.ButtonStyle.secondary)
    async def cancel_button_callback(self, interaction: discord.Interaction, button):
        self.stop()
        await interaction.response.defer()
        await safe_delete_message(interaction.message)
        await self.menu_view.set_create_enabled(True)


class AlertDeleteMenuView(discord.ui.View):
    def __init__(self, menu_view):
        super().__init__(timeout=60)
        self.menu_view = menu_view

    async def on_timeout(self):
        self.stop()
        await self.menu_view.refresh()

    async def interaction_check(self, interaction):
        if interaction.user == self.menu_view.author:
            return True

        await interaction.response.send_message(
            "Only the user who opened this alert menu can edit it.",
            ephemeral=True,
        )
        return False

    @discord.ui.button(label="Select alerts", style=discord.ButtonStyle.primary)
    async def select_button_callback(self, interaction: discord.Interaction, button):
        if not self.menu_view.user_items:
            await interaction.response.defer()
            await self.menu_view.refresh()
            return

        await interaction.response.edit_message(view=DeleteAlertSelectView(self.menu_view))

    @discord.ui.button(label="Remove all alerts", style=discord.ButtonStyle.danger)
    async def remove_all_button_callback(self, interaction: discord.Interaction, button):
        embed = ResponseMsg.confirm_deletion_all()
        await interaction.response.send_message(
            embed=embed.set_author(name=interaction.user.name, icon_url=avatar_url(interaction.user)),
            view=DeleteConfirmationView(self.menu_view, None, True),
        )

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary)
    async def back_button_callback(self, interaction: discord.Interaction, button):
        await interaction.response.edit_message(embed=self.menu_view.create_embed(), view=self.menu_view)


class DeleteAlertSelect(discord.ui.Select):
    def __init__(self, menu_view):
        self.menu_view = menu_view
        options = []

        for item_id, e_level, e_name, _price, item_name, _alert_type in menu_view.user_items:
            options.append(
                discord.SelectOption(
                    label=truncate_select_label(f"{e_name}: {item_name}"),
                    value=f"{item_id}:{e_level}:{ALERT_TYPE_QUEUE}",
                )
            )

        super().__init__(
            placeholder="Select alerts to remove",
            max_values=len(options),
            min_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        delete_all = len(self.values) == len(self.menu_view.user_items)

        if delete_all:
            items = None
            embed = ResponseMsg.confirm_deletion_all()
        else:
            items = [list(map(int, value.split(":"))) for value in self.values]
            labels_by_value = {option.value: option.label for option in self.options}
            embed = ResponseMsg.confirm_deletion([labels_by_value[value] for value in self.values])

        await interaction.response.send_message(
            embed=embed.set_author(name=interaction.user.name, icon_url=avatar_url(interaction.user)),
            view=DeleteConfirmationView(self.menu_view, items, delete_all),
        )


class DeleteAlertSelectView(discord.ui.View):
    def __init__(self, menu_view):
        super().__init__(timeout=60)
        self.menu_view = menu_view
        self.add_item(DeleteAlertSelect(menu_view))

    async def on_timeout(self):
        self.stop()
        await self.menu_view.refresh()

    async def interaction_check(self, interaction):
        if interaction.user == self.menu_view.author:
            return True

        await interaction.response.send_message(
            "Only the user who opened this alert menu can edit it.",
            ephemeral=True,
        )
        return False


class DeleteConfirmationView(discord.ui.View):
    def __init__(self, menu_view, items, delete_all=False):
        super().__init__(timeout=30)
        self.menu_view = menu_view
        self.items = items
        self.delete_all = delete_all

    async def interaction_check(self, interaction):
        if interaction.user == self.menu_view.author:
            return True

        await interaction.response.send_message(
            "Only the user who opened this alert menu can confirm deletion.",
            ephemeral=True,
        )
        return False

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm_button_callback(self, interaction: discord.Interaction, button):
        try:
            if self.delete_all:
                await User(interaction.user.id).remove_all_item_from_user()
            else:
                await User(interaction.user.id).remove_item_from_user(self.items)
        except sqlite3.Error as exc:
            self.stop()
            await interaction.response.edit_message(embed=ResponseMsg.database_error(exc), view=None)
            await asyncio.sleep(3)
            await safe_delete_message(interaction.message)
            await self.menu_view.refresh()
        else:
            self.stop()
            await interaction.response.edit_message(embed=ResponseMsg.deletion_success(), view=None)
            await self.menu_view.refresh()
            await asyncio.sleep(3)
            await safe_delete_message(interaction.message)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button_callback(self, interaction: discord.Interaction, button):
        self.stop()
        await interaction.response.defer()
        await safe_delete_message(interaction.message)
        await self.menu_view.refresh()


class ResponseMsg:
    @staticmethod
    def duplicate_error():
        return discord.Embed(title="You already have this alert in the database.", color=ALERT_COLOR)

    @staticmethod
    def add_to_db_success():
        return discord.Embed(title="Added to database.", color=ALERT_COLOR)

    @staticmethod
    def item_name_error():
        return discord.Embed(title="Item name is required.", color=ALERT_COLOR)

    @staticmethod
    def no_item_error(item_name, item_grade):
        return discord.Embed(
            title=f"No queue-able item found for `{item_grade}: {item_name}`.",
            description="Try a more specific Central Market item name and include punctuation such as apostrophes.",
            color=ALERT_COLOR,
        )

    @staticmethod
    def candidate_matches(item_name, matches, user):
        description = "\n".join(f"[{index}] {match[1]}" for index, match in enumerate(matches, start=1))
        embed = discord.Embed(
            title=f"Possible matches for `{item_name}`",
            description=description,
            color=ALERT_COLOR,
        )
        embed.add_field(name="Select the correct item below.", value="\u200b", inline=False)
        embed.set_author(name=user.name, icon_url=avatar_url(user))
        return embed

    @staticmethod
    def confirm_alert(e_name, item_name, item_id):
        return discord.Embed(
            title="Creating queue alert for:",
            description=f"`{e_name}: {item_name}`",
            color=ALERT_COLOR,
        ).set_thumbnail(url=f"https://cdn.arsha.io/icons/{item_id}.png")

    @staticmethod
    def confirm_deletion(items):
        description = "\n".join(f"[Queue] {item}" for item in items)
        return discord.Embed(
            title="Confirm deletion for the following alerts:",
            description=description,
            color=ERROR_COLOR,
        )

    @staticmethod
    def confirm_deletion_all():
        return discord.Embed(title="Confirm deletion of all alerts.", color=ERROR_COLOR)

    @staticmethod
    def deletion_success():
        return discord.Embed(title="Deleted from database.", color=ALERT_COLOR)

    @staticmethod
    def database_error(error):
        return discord.Embed(title="Database update failed.", description=str(error), color=ERROR_COLOR)
