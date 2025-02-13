from flask import Flask, render_template, request, redirect, url_for
import threading
import discord
from discord.ext import commands
import os

#app
app = Flask(__name__)

#discord bot
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

#bot-status
@app.route("/")
def index():
    return render_template("index.html",bot_status="稼働中" if bot.is_ready() else"停止中")

#bot-shtdwm
@app.route("/shutdown", methods=["POST"])
def shutdown():
    if bot.is_ready():
        threading.Thread(target=bot.close).start()
        return redirect(url_for("index"))
    return "Botはすでに停止しています"

#Flask-Backg
def run_flask():
    app.run(host="0.0.0.0",port=5000, debug=True, use_reloader=False)
    
#Flask-sled
threading.Thread(target=run_flask, daemon=True).start()

#bot-start
@bot.event
async def on_ready():
    print(f"botがログインしました:{bot.user}")

#bot-run
bot.run(TOKEN)