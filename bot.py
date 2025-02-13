import discord
from discord.ext import commands
import os 
import asyncio
import random
import psutil
import time
from gtts import gTTS
from dotenv import load_dotenv
import yt_dlp
import youtube_dl
from discord import FFmpegPCMAudio

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"
VERSION = "5.10.7"
#bot-権限
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

#辞書
read_channels = {}

#path
FFMPEG_PATH = os.getenv("FFMPEG_PATH")


#path-check
if not os.path.exists(FFMPEG_PATH):
    print(f"error: ffmpegが見つかりません。{FFMPEG_PATH}を確認してください")
    exit(1)

#bot-start
start_time = time.time()

@bot.event
async def on_ready():
    activity = discord.Game(name=f"!help1 | {VERSION} ",type=discord.ActivityType.playing)
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f"kotaro online : {bot.user} (ver:{VERSION})")
    bot.remove_command("help") #既存のhelpを削除(新たに導入するhelpのため)

FFMPEG_OPTIONS = {
    'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

#音楽再生q
queue = []
music_queue = []

#get audio info
def get_audio_info(video_url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'extract_flat': False,
        'timeout': 10  # 10秒でタイムアウト
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        return info['url'], info.get('title', 'Unknown Title')

async def play_next(ctx):
    if queue:  # キューに曲がある場合
        url = queue.pop(0)  # 先頭の曲を取得
        audio_url, title = get_audio_info(url)
        ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn -filter:a "volume=0.05"'  # 音量を50%に調整
    }

        def after_play(error):
            coro = play_next(ctx)
            fut = bot.loop.create_task(coro)
            fut.add_done_callback(lambda f: f.exception() if f.exception() else None)

        ctx.voice_client.play(discord.FFmpegPCMAudio(audio_url, executable="ffmpeg"), after=after_play)
        await ctx.send(f"🎵 再生中: {title}")  # 曲名を表示
    else:
        await ctx.send("🎵 再生キューが空です。")

@bot.command()
async def play(ctx, url):
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()
    
    queue.append(url)  # キューに追加
    if not ctx.voice_client.is_playing():
        await play_next(ctx)  # すぐに再生開始

@bot.command()
async def skip(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()  # 現在の曲をスキップ
        await play_next(ctx)

@bot.command()
async def queue_list(ctx):
    if queue:
        await ctx.send("📜 再生キュー:\n" + "\n".join(queue))
    else:
        await ctx.send("🎵 再生キューが空です。")

#再接続
@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and after.channel is None:  # ボットが切断された場合
        print("ボットがボイスチャンネルから切断されました。再接続します...")
        for vc in bot.voice_clients:
            await vc.disconnect(force=True)  # 強制的に切断

#音量設定
@bot.command()
async def volume(ctx, level: float):
    if ctx.voice_client is None:
        await ctx.send("ボイスチャンネルに接続していません！")
        return

    if level < 0 or level > 2.0:
        await ctx.send("音量は 0.0 〜 2.0 の間で指定してください！")
        return

    ctx.voice_client.source = discord.PCMVolumeTransformer(ctx.voice_client.source)
    ctx.voice_client.source.volume = level
    await ctx.send(f"🔊 音量を {level * 100:.0f}% に変更しました！")

#一時停止
@bot.command()
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ 音楽を一時停止しました。")

#再開
@bot.command()
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ 音楽を再開しました。")

#停止
@bot.command()
async def stop(ctx):
    ctx.voice_client.stop()
    await ctx.send("⏹️ 音楽を停止しました。")

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
            tts = gTTS(text=message.content, lang="ja")
            tts.save("speech.mp3")

        if message.guild.voice_client is None:
            if message.author.voice:
                vc = await message.author.voice.channel.connect()
            else:
                await message.channel.send("⚠️ ボイスチャンネルに参加してからメッセージを送信してください!")
                return
        else:
            vc = message.channel.guild.voice_client

        vc.play(discord.FFmpegPCMAudio("speech.mp3", executable=FFMPEG_PATH))
    
    await bot.process_commands(message)

#!help
@bot.command(name="help1", guild_only=True)
async def custum_help(ctx):
    embed = discord.Embed(title="📖コマンド一覧", color=discord.Color.blue())
    embed.add_field(name= "🎵 ~~!play [link]~~", value="linkを再生します。音量に注意してください", inline=False)
    embed.add_field(name= "⏸️ ~~!pause~~", value="再生されている音楽を一時停止します", inline=False)
    embed.add_field(name= "▶️ ~~!resume~~", value="停止している音楽を再開します", inline=False)
    embed.add_field(name= "⏹️ ~~!stop~~", value="音楽を停止します", inline=False)
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
    await ctx.send("⚠️ Botをシャットダウンします。管理人に報告してください。`error:200x`")
    await bot.close()

#error_handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("このコマンドを実行する権限がありません")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("必要な引数が足りません")
    else:
        raise error
    
#run
bot.run(TOKEN)


#version
#1.0.0 = 簡易的なコーディングが完了初期起動状態
#1.1.0 = !kotaroコマンドの実装(初期はおはようのみ)
#1.1.1 = !kotaro含むすべてのコマンドの権限設定の変更(エラーが発生したため)
#1.2.0 = !roleコマンドを!addroleと!removeroleに変更し、2つのコーディングが完了
#2.0.0 = nowコマンドの実装
#2.0.1 = flaskの修正
#2.2.0 = vc
#2.3.0 = voiceの仕様変更(読み上げるチャンネルを設定してその値を自動取得するように変更)
#2.3.1 = setreadがserreadになってる事象を修正
#2.4.0 = ffmpegのインストール
#2.4.1 = ffmpegのパス指定
#2.4.2 = ffmpegのパスerrorの解決
