from flask import Flask, render_template, request, redirect, url_for
import discord
from discord.ext import commands
import threading
import os

app = Flask(__name__)

#Discordとflaskの結合
TOKEN = os.getenv("DISCORD_TOKEN")
bot = commands.Bot(command_prefix="!",intents=discord.Intents.all())

@app.route("/")
def index():
    return render_template("index.html",bot_status="稼働中")

@app.route("/shutdown", methods=["POST"])
def shutdown():
    os._exit(0) #強制シャットダウン
    return redirect(url_for("index"))

@app.route("/status")
def status():
    return{
        "bot_name": str(bot.user),
        "guild_count": len(bot.guilds),
        "ping": round(bot.latency *1000)
    }

#botをFlaskと並行して起動
def run_bot():
    bot.run(TOKEN)

if __name__ == "__main__":
     threading.Thread(target=run_bot).start()
     app.run(debug=True, port=5000)