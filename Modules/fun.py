import discord
import openai
import owoify
import json
import os
from pathlib import Path
from discord.ext import commands
from discord import app_commands

CONFIG_PATH = Path(__file__).resolve().parents[1] / "resources" / "apikey.json"


def get_openai_key():
    token = os.getenv("OPENAI_API_KEY")
    if token:
        return token

    if not CONFIG_PATH.exists():
        return None

    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        data = json.load(config_file)

    return data.get("openaitoken")


openaikey = get_openai_key()

class fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name = 'owoify', aliases = ['owo'])
    async def owo(self, ctx, *, text = None):
        if text is not None:
            await ctx.send(owoify.owoify(text))
            
        else:
            channel = ctx.channel
            messages = [message async for message in channel.history(limit=2)]
            msg = messages[1].content
            
            if (msg[:1] + msg[-1:]) == '<>':
                pass
            else:   
                await ctx.send(owoify.owoify(messages[1].content))


    @commands.command(name = 'askgpt', aliases = ['ask'])
    async def askgpt(self, ctx, temp, *, body = None):
        if body is not None:
            if openaikey is None:
                await ctx.send('OpenAI API key is not configured.')
                return

            openai.api_key = f"{openaikey}"
            response = await openai.Completion.acreate(
                model="gpt-4", 
                prompt="{}".format(body), 
                temperature= float(temp), 
                max_tokens=2000)

            responseFormat = response.choices[0].text
            
            await ctx.send(f'{responseFormat}')
        else:
            await ctx.send('Please provide information')

    
    @commands.command(name = 'image', aliases = ['img'])
    async def image(self, ctx, *, body = None):
        if body is None:
            await ctx.send('Please provide information')
            return

        if openaikey is None:
            await ctx.send('OpenAI API key is not configured.')
            return
        
        openai.api_key = f"{openaikey}"
        try:
            response = await openai.Image.acreate(
                prompt=f"{body}",
                n=1,
                size="1024x1024"
            )
        except openai.error.InvalidRequestError:
            await ctx.send('Prompt violates safety restrictions.')
            return
        else:
            link = response["data"][0]["url"]
            embed=discord.Embed(title=body, color=0x00ff00).set_footer(text="Powered by OpenAI DALL-E")
            embed.set_image(url=link)
            await ctx.send(embed=embed)
    
    # Slash Commands





async def setup(bot):
    await bot.add_cog(fun(bot))
    
