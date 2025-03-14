import discord
from discord.ext import commands
import os
import asyncio
import random
import psutil
import time
from gtts import gTTS
import requests
from dotenv import load_dotenv
import yt_dlp
import youtube_dl
from discord import FFmpegPCMAudio
import re
from osu_bot import fetch_osu_result, fetch_user_info


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"
VERSION = "6.1.20β"
RIOT_GAMES_API_KEY = os.getenv("RIOT_GAMES_API_KEY")
API_URL = 'https://public-api.tracker.gg/v2/valorant/standard/profile/riot/{username}%23{tagline}'

#bot-権限
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

#辞書
read_channels = {}

#path
FFMPEG_PATH = os.getenv("FFMPEG_PATH") #path check

#bot-start
start_time = time.time()

@bot.event
async def on_ready():
    activity = discord.Game(name=f"!help1 | {VERSION} ",type=discord.ActivityType.playing)
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f"kotaro online : {bot.user} (ver:{VERSION})")
    bot.remove_command("help") #既存のhelpを削除(新たに導入するhelpのため)

FFMPEG_OPTIONS = {
    'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

#PUUID
def get_puuid(username: str, tagline: str):
    url = f'https://api.riotgames.com/val/matches/by-puuid/{username}%23{tagline}/ids'
    headers = {
        'X-Riot-Token' : RIOT_GAMES_API_KEY
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data['puuid']
    else:
        return None

#Val
@bot.command()
async def valorant(ctx, username: str, tagline: str):
    puuid = get_puuid(username, tagline)
    if not puuid:
        await ctx.send("プレイヤーのPUUIDの取得に失敗しました。ユーザーネームとタグラインを確認してください。")
        return

    url = API_URL.format(puuid=puuid)
    headers = {
        'X-Riot-Token' : RIOT_GAMES_API_KEY
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        match_ids = response.json()
        if not match_ids:
            await ctx.send("試合結果が見つかりませんでした")
            return

        #val match
        match_id = match_ids[0]
        match_url = f'https://api.riotgames.com/val/matches/{match_id}'
        match_response = requests.get(match_url, headers=headers)

        if match_response.status_code == 200:
            match_data = match_response.json()
            result = f"最新の試合結果:\nマップ: {match_data['map']}\n"
            result += f"結果: {'勝利' if match_data['teams']['team1']['won'] else '敗北'}\n"
            result += f"キル: {match_data['players'][0]['stats']['kills']}\n"
            result += f"デス: {match_data['players'][0]['stats']['deaths']}\n"
            result += f"アシスト: {match_data['players'][0]['stats']['assists']}\n"
        else:
            result = "試合データの取得に失敗しました。"
        else:
        result = (
            f"データの取得に失敗しました。ユーザーネームとタグラインを確認してください。\n"
            f"ステータスコード: {response.status_code}\n"
            f"レスポンス: {response.json()}"
        )

    await ctx.send(result)

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and after.channel is None:  # ボットが切断された場合
        print("ボットがボイスチャンネルから切断されました。再接続します...")
        for vc in bot.voice_clients:
            if vc.is_connected():
                vc.stop()
            await asyncio.sleep(1)  # 切断までの猶予
            await vc.disconnect(force=True)  # 強制的に切断

#osu!-res
@bot.command()
async def osu(ctx, username: str):
    result, file = await fetch_osu_result(username)
    if result:
        if file:
            await ctx.send(embed=result, file=file)
        else:
            await ctx.send(embed=result)
    else:
        await ctx.send('**直近のプレイが見つかりませんでした🔎**')

#osu!-inf
@bot.command()
async def osuinfo(ctx, username: str):
    total_pp, global_rank = await fetch_user_info(username)
    if total_pp is not None and global_rank is not None:
        embed = discord.Embed(title=f"osu! userinfo - {username}", color=0x0099ff)
        embed.add_field(name= 'Totalpp', value=str(total_pp), inline=True)
        embed.add_field(name= 'Global Rank', value=str(global_rank), inline=True)

        await ctx.send(embed=embed)
    else:
        await ctx.send('**ユーザー情報が見つかりませんでした**')

#音量設定
@bot.command()
async def volume(ctx, level: float):
    if ctx.voice_client is None:
        await ctx.send("ボイスチャンネルに接続していません！")
        return


    if level < 0 or level > 2.0:
        await ctx.send("音量は 0.0 〜 2.0 の間で指定してください！")
        return

    if not isinstance(ctx.voice_client.source, discord.PCMVolumeTransformer):
        ctx.voice_client.source = discord.PCMVolumeTransformer(ctx.voice_client.source)

    ctx.voice_client.source.volume = level  # 音量を変更するだけ
    await ctx.send(f"🔊 音量を {level * 100:.0f}% に変更しました！")

# VC切断
@bot.command()
async def leave(ctx):
    await ctx.voice_client.disconnect()
    await ctx.send("📤 VCから切断しました")

#VC移動-all
@bot.command(guild_only=True)
#@commands.has_permissions(move_members=True)
async def moveall(ctx, target_channel: discord.VoiceChannel):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("⚠️ VCに参加してからコマンドを使用してください")
        return
    
    current_channel = ctx.author.voice.channel
    for member in current_channel.members:
        await member.move_to(target_channel)

    await ctx.send(f"✅ **{current_channel.name}** のメンバーを **{target_channel.name}** に移動させました")

#VC移動-solo
@bot.command(guild_only=True)
#@commands.has_permissions(move_members=True)
async def move(ctx, member: discord.Member, target_channel: discord.VoiceChannel):
    if not member.voice or not member.voice.channel:
        await ctx.send(f"⚠️ {member.mention} が見つかりません...")
        return
    
    await member.move_to(target_channel)
    await ctx.send(f"✅ **{member.mention}** を **{target_channel.name}** に移動しました")

#読み上げのチャンネル設定
@bot.command(guild_only=True)
async def setread(ctx):  
    read_channels[ctx.guild.id] = ctx.channel.id
    await ctx.send(f"📢読み上げチャンネルを **{ctx.channel.mention}** に設定しました！")
    
#↑の解除
@bot.command(guild_only=True)
async def unsetread(ctx):
    if ctx.guild.id in read_channels:
        del read_channels[ctx.guild.id]
        await ctx.send("📢読み上げチャンネルの設定を解除しました！")

        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect()
    else:
        await ctx.send("⚠️読み上げチャンネルの設定はされていません。")

# !role
@bot.command(guild_only=True)
async def role(ctx,min_value: int, max_value: int):
    if min_value > max_value:
         await ctx.send("⚠️ 最小値が最大値より大きいです。")
         return
    
    random_number = random.randint(min_value,max_value)
    await ctx.send(f"🎲 結果は: **{random_number}** でした！")

#message - remove_emojis
def remove_emojis(text):
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F"  # 顔文字
        "\U0001F300-\U0001F5FF"  # 記号 & 絵文字
        "\U0001F680-\U0001F6FF"  # 乗り物 & 地図記号
        "\U0001F700-\U0001F77F"  # 追加の記号
        "\U0001F780-\U0001F7FF"  # 幾何学模様
        "\U0001F800-\U0001F8FF"  # 装飾記号
        "\U0001F900-\U0001F9FF"  # 装飾文字
        "\U0001FA00-\U0001FA6F"  # 道具・アイコン
        "\U0001FA70-\U0001FAFF"  # 追加の絵文字
        "\U00002702-\U000027B0"  # その他の絵文字
        "\U000024C2-\U0001F251]+"  # その他の記号
        , flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)
    text = re.sub(r"<a?:\w+:\d+>","",text)

    return text

#message
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.content.startswith(PREFIX):
        await bot.process_commands(message)
        return
    
    guild_id = message.guild.id
    if guild_id in read_channels and message.channel.id == read_channels[guild_id]:
        if message.author.voice and message.author.voice.channel:
            voice_channel = message.author.voice.channel
            if not message.guild.voice_client:
                await voice_channel.connect()
        
        if message.guild.voice_client:
            clean_text = remove_emojis(message.content)  # 絵文字削除
            print(f"元のメッセージ: {message.content}")  # デバッグ出力
            print(f"絵文字削除後のメッセージ: {clean_text}")  # デバッグ出力

            if clean_text.strip():  # 空白だけならスキップ
                tts = gTTS(text=clean_text, lang="ja")  # ✅ 修正: 絵文字削除後のテキストを使用
                tts.save("speech.mp3")

                if not os.path.exists("speech.mp3"):
                    print("⚠️ speech.mp3 が作成されていません！")
                    return

                vc = message.channel.guild.voice_client
                vc.play(discord.FFmpegPCMAudio("speech.mp3", executable=FFMPEG_PATH))
            else:
                print("⚠️ メッセージが空だったためスキップされました。")

    await bot.process_commands(message)

#!help
@bot.command(name="help1", guild_only=True)
async def custum_help(ctx):
    embed = discord.Embed(title="📖コマンド一覧", color=discord.Color.blue())
    embed.add_field(name= "📤 !leave", value="botを切断します", inline=False)
    embed.add_field(name= "📢 !setread", value="コマンドを入力したチャンネルを読み上げ対象に設定", inline=False)
    embed.add_field(name= "📢 !unsetread", value="現在設定されている読み上げチャンネルの設定を削除します", inline=False)
    embed.add_field(name= "👟 !kick @[user]", value="指定したユーザーをサーバーからキック", inline=False)
    embed.add_field(name= "🔨 !ban @[user]", value="指定したユーザーをこのサーバーからBAN", inline=False)
    embed.add_field(name= "🚮 !clear [数字]", value="指定した数字の数だけメッセージを削除", inline=False)
    embed.add_field(name= "🚩 !addrole @[user] [role]", value="指定したユーザーにロールを付与", inline=False)
    embed.add_field(name= "🚫 !removerole @[user] [role]", value="指定したユーザーからロールを削除", inline=False)
    embed.add_field(name= "⛓️‍💥 !moveall #[channel]", value="現在あなたがいるVCのメンバー全員を指定したVCに移動させます", inline=False)
    embed.add_field(name= "⛓️‍💥 !move @[user] #[channel]", value="指定されたユーザーを指定したVCに移動させます", inline=False)
    embed.add_field(name= "🤖 !status", value="現在のbotのステータスを表示する", inline=False)
    embed.add_field(name= "🎲 !role [最小値]  [最大値]", value="最小値から最大値までの間でランダムな数字を出します", inline=False)
    embed.add_field(name= "⚠️ !shutdown", value="botをシャットダウンする", inline=False)
    await ctx.send(embed=embed)

#kick
@bot.command(guild_only=True)
@commands.has_permissions(kick_members=True)
async def kick(ctx,member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"{member.mention}をキックしました。原因：{reason}")

#BAN
@bot.command(guild_only=True)
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"{member.mention}をBANしました。原因 : {reason}")

#自動退出
@bot.event
async def on_voice_state_update(member, before, after):
    if not member.bot:
        voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)

        if voice_client and len(voice_client.channel.members) == 1:
            await asyncio.sleep(10)
            if len(voice_client.channel.members) == 1:
                await voice_client.disconnect()
                print("🔌 VCから自動退出しました")


#mesage clear
@bot.command(guild_only=True)
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"{amount} 件のメッセージを削除しました。", delete_after=3)


#role-O
@bot.command(guild_only=True)
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role:
        try:
            await member.add_roles(role)
            await ctx.send(f"**{member.mention}** に **{role_name}** を付与しました。")
        except discord.Forbidden:
            await ctx.send("権限不足のため、役職を付与できません。")
        except discord.HTTPException as e:
            await ctx.send(f"役職を付与中にエラーが発生しました: {e}")
    else:
        await ctx.send(f" **{role_name}** が見つかりません。")
    
#role-X
@bot.command(guild_only=True)
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name )
    if role :
        await member.remove_roles(role)
        await ctx.send(f" **{member.mention}** から **{role_name}** を削除しました")
    else:
        await ctx.send(f" **`{role_name}** が見つかりません...")

#kotaro
@bot.command(guild_only=True)
async def kotaro(ctx):
    await ctx.send("おはよう! \n 詳しいバージョン情報はこちらから")

#okaeri
@bot.command(guild_only=True)
async def okaeri(ctx):
    await ctx.send(f"**ただいま！戻ってきたよ！** \n 現在のバージョンは **`{VERSION}`**だよ！")

#bot-now
@bot.command(guild_only=True)
@commands.has_permissions(administrator=True)
async def status(ctx):
    latency = round(bot.latency * 1000) #ping
    uptime = round(time.time() - start_time) 
    cpu_usage = psutil.cpu_percent()
    memory_usage = psutil.virtual_memory().percent


    embed = discord.Embed(
        title="📊 kotaro status", 
        description= "現在のこたろのステータスです",
        color=discord.Color.blue()
    )
    
    embed.set_thumbnail(url=bot.user.avatar.url)
    embed.add_field(name="📡 ping",value=f"🟢 {latency}ms",inline=True)
    embed.add_field(name="🕒 稼働時間", value=f"⏳ {uptime} 秒", inline=True)
    embed.add_field(name="🖥️ server",value=f"🏠 {len(bot.guilds)}",inline=True)
    embed.add_field(name="👥 user",value=f"👤 {sum(g.member_count for g in bot.guilds)}", inline=True)
    embed.add_field(name="💾 メモリ使用率", value=f"🧠 {memory_usage}%", inline=True)
    embed.add_field(name="⚙️ CPU使用率", value=f"🔥 {cpu_usage}%", inline=True)
    embed.add_field(name="🆙 Version",value=f"🔹 {VERSION}", inline=False)

    await ctx.send(embed=embed)

#bot-shutdown
@bot.command(guild_only=True)
@commands.has_permissions(administrator=True)
async def shutdown(ctx):
    await ctx.send("⚠️ Botをシャットダウンします。管理人に報告してください。")
    await bot.close()

#error_handling
@bot.event
async def on_command_error(ctx, error):
    print(f"ERROR: コマンド実行中にエラーが発生: {error}")  # エラーログ
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("このコマンドを実行する権限がありません")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("必要な引数が足りません")
    else:
        await ctx.send(f"⚠️ エラーが発生しました: {error}") #エラー内容を表示
    
#run
bot.run(TOKEN)


