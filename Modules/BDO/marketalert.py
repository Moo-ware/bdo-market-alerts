import discord
import asyncio
import sqlite3
from discord import app_commands
from datetime import datetime
from discord.ext import tasks, commands
from utils.functions import findItems, GetWaitlist, matchEnhancement


last_waitlist = [] # Stores the last waitlist processed

class marketalert(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Enable Below when ready to start the bot
        # self.check_waitlist.start() 
    
    def cog_unload(self):
        pass # Delete this when enabling the task below
        # self.check_waitlist.cancel()
        
    @app_commands.command(name='alert', description='Brings up my alert menu') # Create a slash command
    async def alertmenu(self, interaction: discord.Interaction):
        userInfo = await User(interaction.user.id).get_user()
        view = await CreateAlertMenu(interaction.user, userInfo).create_alertmenu_view() # Selects which view the user will see based on the number of alerts the user have
        await interaction.response.send_message(embed=await CreateAlertMenu(interaction.user, userInfo).create_alertmenu_embed(), view=view) # Send a message with our View class that contains the button
        view.message = await interaction.original_response() # Sets the current message as view.message

    
    # disabled for now. (Main loop for checking waitlist)
    """@tasks.loop(seconds=25)
    async def check_waitlist(self):
        global last_waitlist
        channel = self.bot.get_channel(596779920445800456)
        current_list = await GetWaitlist()  #['mainKey', 'name', 'chooseKey', '_waitEndTime', '_pricePerOne'] for each entry
        list_for_db = await waitlist_comparison(last_waitlist, current_list)
        ### data base step ###
        user_id_todm = await database().find_user_with_item(list_for_db)
        await DM(list_for_db).send_dm(user_id_todm, self.bot)
        
        
        last_waitlist = current_list # sets the last to current after sending out alerts"""
        
async def setup(bot):
    await bot.add_cog(marketalert(bot), guild=discord.Object(id=1008234755638173776))


async def waitlist_comparison(old, new): # compares old and new waitlist and removing duplicates
    tmp_list = []
    if len(old) == 0:
        return new
    elif len(new) == 0:
        return []
    
    for i in new:
        found_dupe = False
        for j in old:
            if len(list(set(j).symmetric_difference(set(i)))) == 0:
                found_dupe=True
                break
        if found_dupe is False:
            tmp_list.append(i)
        
    return tmp_list

class DM():
    def __init__(self, item):
        self.item = item

    async def send_dm(self, users, bot): # Sending out dms to each user
        for index, usersid in enumerate(users):
            if len(usersid) != 0:
                for userid in usersid:
                    user = bot.get_user(userid[0])
                    if user is not None:
                        embed = await self.create_dm_embed(self.item[index])
                        await user.send(embed=embed)
                    else:
                        pass

    async def create_dm_embed(self, list):
        embed=discord.Embed(title=f'{await matchEnhancement(list[2])}: {list[1]}',
                            color=0xfe9a9a).add_field(name="Price:", value="{:,}".format(list[4]), inline=True)
        timestamp = str(list[3])[0:10]
        embed.add_field(name='Live in:', value=f'<t:{int(timestamp)}:R>',inline=True)
        return embed


class CreateAlertMenu(): # Creates the physical Alert Menu
    def __init__(self, user, userInfo=None):
        self.user = user
        self.userInfo = userInfo

    async def create_alertmenu_view(self):
        length = len(self.userInfo)
        if length >= 5: # View version where user has reached maximum alerts allowed
            view = AlertMenuMaxed(self.user, self.userInfo)
            return view
        elif length == 0: # View version where user has no alerts 
            view = AlertMenuNoAlerts(self.user, self.userInfo)
            return view
        else: 
            view=AlertMenuNormal(self.user, self.userInfo)
            return view 

    async def create_alertmenu_embed(self):
        description = ''
        for item in self.userInfo:
            description = description + f"[{item[5]}] {item[2]}: {item[4]}\n" 
        embed = discord.Embed(title=f"Welcome back {self.user.name}!", 
                        description=f"**My active alerts**: `{len(self.userInfo)}/5 used`\n```{description}```", 
                        color=0xfe9a9a).set_author(name=self.user.name, icon_url=self.user.avatar)
        embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/629036668531507222/1079318649325756498/78796e7f-eaa1-4f7e-abb6-099499a807ea.png')

        return embed
    
    async def alert_menu_update(self, button_items):
        button_items[2].stop()
        self.userInfo = await User(self.user.id).get_user()
        view = await CreateAlertMenu(self.user, self.userInfo).create_alertmenu_view()
        await button_items[0].edit(embed=await self.create_alertmenu_embed(), view=view)
        view.message = button_items[0]


"""Below are the Database actions"""
class UserDB(): # For performing actions of a User's database
    async def get_user_from_db(self, userid):
        connection = sqlite3.connect("resources/alerts.db")
        cursor = connection.cursor()
        rows = cursor.execute("SELECT AlertList.item_id, AlertList.enhancement_level, Enhancement.e_name, AlertList.price, QueueItems.item_name, AlertTypes.alert_type\
                              FROM AlertList\
                              INNER JOIN QueueItems ON QueueItems.item_id = AlertList.item_id AND QueueItems.e_level IN (AlertList.enhancement_level, AlertList.enhancement_level + 15)\
                              INNER JOIN Enhancement ON AlertList.enhancement_level = Enhancement.elevel\
                              INNER JOIN AlertTypes ON AlertTypes.alert_id = AlertList.alert_id\
                              WHERE user_id = ?", (userid,)).fetchall() ### To implement if Stock Alert is added in the future ###
        cursor.close()
        connection.close()
        return rows

    async def save_user_to_db(self, userid, itemid, elevel, price, alert_id):
        if price == 'NULL':
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


class User(): # For calling actions of a User's database
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
    

class database(): # For getting all types of info from database
    def __init__(self):
        self = self
    
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
        rows = cursor.execute("SELECT item_id, item_name FROM QueueItems WHERE e_level = ? OR e_level = ?", (e_level, e_level + 15)).fetchall()
        cursor.close()
        connection.close()
        return rows
    
    async def find_user_with_item(self, list):
        connection = sqlite3.connect("resources/alerts.db")
        cursor = connection.cursor()
        rows=[]
        for i in list:
            tmp = cursor.execute(
                "SELECT user_id FROM AlertList WHERE item_id = ? AND enhancement_level IN (?, ?)",
                (i[0], i[2], i[2] - 15),
            ).fetchall()
            rows.append(tmp)
        cursor.close()
        connection.close()
        return rows
    

"""Below are the Buttons necessary for UI"""
class UserMenu(): # For enabling and disabling buttons on Alert Menu when Buttons are pressed
    def __init__(self, button_items):
        self.msgid = button_items[0]
        self.button = button_items[1]
        self.view = button_items[2]
    
    async def enable_menu_button(self):
        self.button.disabled = False
        await self.msgid.edit(view=self.view)

    async def disable_menu_button(self):
        self.button.disabled = True
        await self.msgid.edit(view=self.view)


class AlertMenuNormal(discord.ui.View): # Main Alert Menu View
    def __init__(self, author, userItems):
        super().__init__(timeout=180) # Timeout after this long
        self.author = author
        self.userItems = userItems
        
    async def on_timeout(self):
        self.stop()
        await self.message.delete()
        
    async def interaction_check(self, interaction):
        # Only allow the author that invoke the command to be able to use the interaction
        return interaction.user == self.author

    
    @discord.ui.button(label="Create a queue alert", row=0, style=discord.ButtonStyle.primary, emoji="🔔")
    async def create_alert_button_callback(self, interaction: discord.Interaction, button):
        buttonlist = []
        buttonlist.extend([interaction.message, button, self])
        await interaction.response.send_modal(itemModal(buttonlist))
    
    @discord.ui.button(label="Remove Alert", row=0, style=discord.ButtonStyle.red, emoji="🛑") 
    async def remove_button_callback(self, interaction: discord.Interaction, button):
        buttonlist = []
        buttonlist.extend([interaction.message, button, self])
        await interaction.response.edit_message(view=alertEditMenu(interaction.user, self, self.userItems, buttonlist)) 
    
    @discord.ui.button(label="Close", row=1, style=discord.ButtonStyle.grey) 
    async def exit_button_callback(self, interaction: discord.Interaction, button):
        self.stop()
        await interaction.message.delete() 


class AlertMenuMaxed(discord.ui.View): # Secondary Alert Menu when user has reached maximum alerts allowed
    def __init__(self, author, userItems):
        super().__init__(timeout=180) # Timeout after this long
        self.author = author
        self.userItems = userItems

    async def on_timeout(self):
        self.stop()
        await self.message.delete()
        
    async def interaction_check(self, interaction):
        # Only allow the author that invoke the command to be able to use the interaction
        return interaction.user == self.author

    
    @discord.ui.button(label="Create a queue alert", row=0, style=discord.ButtonStyle.primary, emoji="🔔", disabled=True)
    async def create_alert_button_callback(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
    
    @discord.ui.button(label="Remove Alert", row=0, style=discord.ButtonStyle.red, emoji="🛑") 
    async def remove_button_callback(self, interaction: discord.Interaction, button):
        buttonlist = []
        buttonlist.extend([interaction.message, button, self])
        await interaction.response.edit_message(view=alertEditMenu(interaction.user, self, self.userItems, buttonlist)) 
    
    @discord.ui.button(label="Close", row=1, style=discord.ButtonStyle.grey) 
    async def exit_button_callback(self, interaction: discord.Interaction, button):
        self.stop()
        await interaction.message.delete() 

class AlertMenuNoAlerts(discord.ui.View): # Third Alert Menu when user has no alerts
    def __init__(self, author, userItems):
        super().__init__(timeout=180) # Timeout after this long
        self.author = author
        self.userItems = userItems
    
    async def on_timeout(self):
        self.stop()
        await self.message.delete()
        
    async def interaction_check(self, interaction):
        # Only allow the author that invoke the command to be able to use the interaction
        return interaction.user == self.author

    
    @discord.ui.button(label="Create a queue alert", row=0, style=discord.ButtonStyle.primary, emoji="🔔")
    async def create_alert_button_callback(self, interaction: discord.Interaction, button):
        buttonlist = []
        buttonlist.extend([interaction.message, button, self])
        await interaction.response.send_modal(itemModal(buttonlist))
    
    @discord.ui.button(label="Remove Alert", row=0, style=discord.ButtonStyle.red, emoji="🛑", disabled=True) 
    async def remove_button_callback(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
    
    @discord.ui.button(label="Close", row=1, style=discord.ButtonStyle.grey) 
    async def exit_button_callback(self, interaction: discord.Interaction, button):
        self.stop()
        await interaction.message.delete() 

class itemModal(discord.ui.Modal, title="Test test test test"): # Modal that sends after you click Create queue alert from above
    itemGrade = discord.ui.TextInput(label='Enter the level of the item (e.g. Base, Pen)')
    itemName = discord.ui.TextInput(label= 'Enter the name of the Item')
    
    def __init__(self, button_items):
        super().__init__()
        self.button_items = button_items

    # Creating the select menu (Might move to another Class later just for more organization)
    async def create_select_menu(self, list, e_level):
        menuoptions = Select(self.button_items, [e_level, str(self.itemGrade).upper()]) # Passing "button_items" which contains the view, button and msg id of alert menu.
        string = ''
        # Adding matching fields to Select menu
        for i in list:
            menuoptions.add_option(label=f'{i[1]}', value=f'{i[1]}-{i[0]}')
            string = string + f'[{list.index(i)}] {i[1]}\n'
        return menuoptions, string
    
    async def on_submit(self, interaction: discord.Interaction):
        e_level = await database().get_enhancement_level(str(self.itemGrade).upper()) # Get integer e_level from string

        if len(e_level) == 0:
            await interaction.response.send_message(embed=await ResponseMsg().e_level_error())
            await asyncio.sleep(7)
            await interaction.delete_original_response()
            return # Stops execution if e_level is not matched to DB
            
        # Disables the 'Create a Queue Alert' Button on Modal submit
        await UserMenu(self.button_items).disable_menu_button()

        # Match input itemName from model to a BDO Item Name 
        list = await findItems(str(self.itemName), await database().get_items_from_level(e_level[0][0]))
        
        # Making sure list stays within Discord limits
        if len(list) > 1 and len(list) < 25:
            menuoptions, string = await self.create_select_menu(list, e_level[0][0])
            view = SelectView(menuoptions)
            await interaction.response.send_message(embed=discord.Embed(title=f'Found a list of possible items related to `{self.itemName}`',
                                                                  description = f'{string}',
                                                                  color=0xfe9a9a).add_field(name='Please select the correct item below:', value='').set_author(name=interaction.user.name, icon_url=interaction.user.avatar), 
                                                                  view=view)
            view.message = await interaction.original_response() # view.message represents the message sent above
            view.button_items = self.button_items
        # If returned items only has one match
        elif len(list) == 1:
            view = Confirmation(interaction.user, self.button_items, e_level[0][0], list[0][0])
            await interaction.response.send_message(embed = discord.Embed(title='Creating queue alert for:',
                                description=f'`{str(self.itemGrade).upper()}: {list[0][1]}`',
                                color=0xfe9a9a).set_thumbnail(url=f'https://cdn.arsha.io/icons/{list[0][0]}.png'), view=view)
            view.message = await interaction.original_response()
        
        else:
            await interaction.response.send_message(embed=await ResponseMsg.no_item_error(self.itemName, str(self.itemGrade).upper()))
            # For re-enabling Create a Queue Button
            await UserMenu(self.button_items).enable_menu_button()
            await asyncio.sleep(10)
            await interaction.delete_original_response()
            
            
class Select(discord.ui.Select): # Creates the Select Menu after modal above if there are more than 1 matched
    def __init__(self, button_items, e_level_name: list):
        options=[]
        super().__init__(placeholder="Select an option",max_values=1,min_values=1,options=options)
        self.button_items = button_items
        self.e_level_name = e_level_name

    async def callback(self, interaction: discord.Interaction):
        item_id = self.values[0].split('-')[1]
        view = ConfirmationMulti(interaction.user, self, self.button_items, self.e_level_name[0], item_id)
        embed = discord.Embed(title='Creating queue alert for:',
                                description=f"`{self.e_level_name[1]}: {self.values[0].split('-')[0]}`",
                                color=0xfe9a9a).set_thumbnail(url=f"https://cdn.arsha.io/icons/{item_id}.png")
        await interaction.response.edit_message(embed=embed, view=view)
        view.message = await interaction.original_response()

class SelectView(discord.ui.View): # Creates the View with the Select Menu from Select Class
    def __init__(self, menuoptions):
        super().__init__(timeout=60)
        self.add_item(menuoptions)
        
    
    async def on_timeout(self):
        try:
            await self.message.delete()
            await UserMenu(self.button_items).enable_menu_button()
        except discord.errors.NotFound:
            pass


class Confirmation(discord.ui.View): # Confirmation page if only 1 item is matched
    def __init__(self, author, button_items, e_level, item_id):
        super().__init__(timeout=30)
        self.author = author
        self.button_items = button_items
        self.e_level = e_level
        self.item_id = item_id
    
    async def on_timeout(self):
        await self.message.delete()
        await UserMenu(self.button_items).enable_menu_button()

    async def interaction_check(self, interaction):
        # Only allow the author that invoke the command to be able to use the interaction
        return interaction.user == self.author
    
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green) 
    async def confirm_button_callback(self, interaction: discord.Interaction, button):
        try:
            await User(interaction.user.id).save_user(self.item_id, self.e_level, 'NULL', 1)
        except sqlite3.IntegrityError:
            self.stop()
            await interaction.response.edit_message(embed=await ResponseMsg().duplicate_error(), view=None)
            await asyncio.sleep(3)
            await UserMenu(self.button_items).enable_menu_button()
            await interaction.followup.delete_message(interaction.message.id)
        else:
            self.stop()
            await interaction.response.edit_message(embed=await ResponseMsg().add_to_db_success(), view=None)
            await CreateAlertMenu(interaction.user).alert_menu_update(self.button_items)
            await asyncio.sleep(3)
            await interaction.followup.delete_message(interaction.message.id)
    
    @discord.ui.button(label="Go back", style=discord.ButtonStyle.red) # Create a button with the label "Close" with color red
    async def before_button_callback(self, interaction: discord.Interaction, button):
        self.stop()
        await interaction.message.delete()
        
        # Re Enables 'Create queue alert' Button when 'Go Back' is pressed incase user exits Modal without submitting
        await UserMenu(self.button_items).enable_menu_button()
        await interaction.response.send_modal(itemModal(self.button_items))


class ConfirmationMulti(discord.ui.View): # Confirmation Menu for if multiple items are matched
    def __init__(self, author, options, button_items, e_level, item_id):
        super().__init__(timeout=30)
        self.author = author
        self.options = options
        self.button_items = button_items
        self.e_level = e_level
        self.item_id = item_id
    
    async def on_timeout(self):
        print('timeout')
        await self.message.delete()
        await UserMenu(self.button_items).enable_menu_button()
    
    async def interaction_check(self, interaction):
        # Only allow the author that invoke the command to be able to use the interaction
        return interaction.user == self.author
    
    @discord.ui.button(label="Confirm", row=0, style=discord.ButtonStyle.green) 
    async def confirm_button_callback(self, interaction: discord.Interaction, button):
        try:
            await User(interaction.user.id).save_user(self.item_id, self.e_level, 'NULL', 1)
        except sqlite3.IntegrityError:
            self.stop()
            await interaction.response.edit_message(embed=await ResponseMsg().duplicate_error(), view=None)
            await asyncio.sleep(3)
            await UserMenu(self.button_items).enable_menu_button()
            await interaction.followup.delete_message(interaction.message.id)
        else:
            self.stop()
            await interaction.response.edit_message(embed=await ResponseMsg().add_to_db_success(), view=None)
            await CreateAlertMenu(interaction.user).alert_menu_update(self.button_items)
            await asyncio.sleep(3)
            await interaction.followup.delete_message(interaction.message.id)
    
    @discord.ui.button(label="Go Back", row=0, style=discord.ButtonStyle.red) # Create a button with the label "Close" with color red
    async def before_button_callback(self, interaction: discord.Interaction, button):
        self.stop()
        # Going back to Select View
        await interaction.response.edit_message(view=SelectView(self.options))
        
    @discord.ui.button(label="Re-Enter Item Name", row=1, style=discord.ButtonStyle.blurple) # Create a button with the label "Close" with color red
    async def modal_button_callback(self, interaction: discord.Interaction, button):
        self.stop()
        await interaction.message.delete()
        
        # Re Enables 'Create queue alert' Button 
        await UserMenu(self.button_items).enable_menu_button()
        await interaction.response.send_modal(itemModal(self.button_items))
    
    
    @discord.ui.button(label='Exit', row = 1, style=discord.ButtonStyle.gray) # Exit button
    async def exit_callback(self, interaction: discord.Interaction, button):
        self.stop()
        await interaction.message.delete()
        
        # Re Enables 'Create queue alert' Button 
        await UserMenu(self.button_items).enable_menu_button()


class ConfirmationDeletion(discord.ui.View): # Confirmation Menu for alert deletion
    def __init__(self, author, items, button_items, delete_all = False):
        super().__init__()
        self.author = author
        self.items = items
        self.button_items = button_items
        self.delete_all = delete_all
        
    async def interaction_check(self, interaction):
        # Only allow the author that invoke the command to be able to use the interaction
        return interaction.user == self.author
    
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green) 
    async def confirm_button_callback(self, interaction: discord.Interaction, button):
        if self.delete_all is False:
            try:
                await User(interaction.user.id).remove_item_from_user(self.items)
            except Exception as e:
                self.stop()
                await interaction.response.edit_message(embed=discord.Embed(title=e), view=None)
                await asyncio.sleep(3)
                await UserMenu(self.button_items).enable_menu_button()
                await interaction.followup.delete_message(interaction.message.id)
            else:
                self.stop()
                await interaction.response.edit_message(embed= await ResponseMsg.deletion_success(), view=None)
                await CreateAlertMenu(interaction.user).alert_menu_update(self.button_items)
                await asyncio.sleep(3)
                await interaction.followup.delete_message(interaction.message.id)   
        else:
            try:
               await User(interaction.user.id).remove_all_item_from_user()
            except Exception as e:
                self.stop()
                await interaction.response.edit_message(embed=discord.Embed(title=e), view=None)
                await asyncio.sleep(3)
                await UserMenu(self.button_items).enable_menu_button()
                await interaction.followup.delete_message(interaction.message.id)
            else:
                self.stop()
                await interaction.response.edit_message(embed= await ResponseMsg.deletion_success(), view=None)
                await CreateAlertMenu(interaction.user).alert_menu_update(self.button_items)
                await asyncio.sleep(3)
                await interaction.followup.delete_message(interaction.message.id)

    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red) # Create a button with the label "Close" with color red
    async def before_button_callback(self, interaction: discord.Interaction, button):
        self.stop()
        await interaction.message.delete()
        await self.button_items[0].edit(view=self.button_items[2])
    

class alertEditMenu(discord.ui.View):
    def __init__(self, author, view, useritems, button_items):
        super().__init__()
        self.author = author
        self.view = view # Main Alert Menu View
        self.userItems = useritems
        self.button_items = button_items
    
    async def interaction_check(self, interaction):
        # Only allow the author that invoke the command to be able to use the interaction
        return interaction.user == self.author
    
    async def create_select_menu(self):
        alertmenuoptions = alertSelect(len(self.userItems), self.button_items)
        for i in self.userItems:
            alertmenuoptions.add_option(label=f'{i[2]}: {i[4]}', value=f'{i[2]}: {i[4]}-{i[0]}-{i[1]}') ### To implement if Stock Alert is added in the future ###
        return alertmenuoptions
    
    @discord.ui.button(label="Select Alert", style=discord.ButtonStyle.blurple) # Create a button with the label "Close" with color red
    async def select_button_callback(self, interaction: discord.Interaction, button):
        await interaction.response.edit_message(view=alertSelectView(await self.create_select_menu()))
    
    @discord.ui.button(label="Remove ALL Alerts", style=discord.ButtonStyle.red, emoji='⚠️') # Create a button with the label "Close" with color red
    async def removeall_button_callback(self, interaction: discord.Interaction, button):
        embed = await ResponseMsg().confirm_deletion_all()
        await interaction.response.send_message(embed= embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar), 
                                                    view=ConfirmationDeletion(interaction.user, None, self.button_items, True))
    
    @discord.ui.button(label="Go Back", style=discord.ButtonStyle.red) # Create a button with the label "Close" with color red
    async def back_button_callback(self, interaction: discord.Interaction, button):
        await interaction.response.edit_message(view=self.view)
    

class alertSelect(discord.ui.Select):
    def __init__(self, length, button_items):
        options=[]
        super().__init__(placeholder="Select Alerts for Deletion",max_values=length, min_values=1, options=options)
        self.length = length
        self.button_items = button_items

    async def callback(self, interaction: discord.Interaction):
        if len(self.values) != self.length:
            item_list = [[int(i.split('-')[1]), int(i.split('-')[2]), 1] for i in self.values] ### To implement if Stock Alert is added in the future ###
            item_format = [[i.split('-')[0], 'Queue'] for i in self.values]
            embed = await ResponseMsg().confirm_deletion(item_format)
            await interaction.response.send_message(embed= embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar), 
                                                    view=ConfirmationDeletion(interaction.user, item_list, self.button_items)) ### To implement if Stock Alert is added in the future ###
        else:
            embed = await ResponseMsg().confirm_deletion_all()
            await interaction.response.send_message(embed= embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar), 
                                                    view=ConfirmationDeletion(interaction.user, None, self.button_items, True)) ### To implement if Stock Alert is added in the future ###
            

class alertSelectView(discord.ui.View):
    def __init__(self, alertmenuoptions):
        super().__init__(timeout=60)
        self.add_item(alertmenuoptions)

class ResponseMsg(): # Fail and Success response embeds
    async def duplicate_error(self):
        return discord.Embed(title='⚠️ You already have this alert in the database!', color=0xfe9a9a)
    
    async def add_to_db_success(self):
        return discord.Embed(title='✅ Added to database!', color=0xfe9a9a)
    
    async def e_level_error(self):
        return discord.Embed(title='⛔ Enhancement Level is Invalid', 
                             description='Acceptable Inputs:\n`Base, PRI, DUO, TRI, TET, PEN`',
                             color=0xfe9a9a)

    async def no_item_error(itemName, itemGrade):
        return discord.Embed(title=f'No queue-able item found with the name `{itemName}` and Enhancement Level `{itemGrade}`, or too many items are found. Try to be more specific.',
                             description= '**Make sure to:**\n -Include apostrophe **ex: Turo\'s**\n-Make sure the Item is expensive enough to be listed on the registration queue. ', 
                             color=0xfe9a9a)

    async def confirm_deletion(self, items):
        description=""
        for i in items:
            description = description + f"[{i[1]}] {i[0]}\n"
        return discord.Embed(title='Confirm Deletion for the following alerts(s):', description=description, color=0xFF0000)
    
    async def confirm_deletion_all(self):
        return discord.Embed(title='⚠️ Confirm Deletion of `ALL` your alerts ⚠️', color=0xFF0000)
    
    async def deletion_success():
        return discord.Embed(title='✅ Deleted from database!', color=0xfe9a9a)
    
    
