import subprocess
import sys

# Start webhook server
webhook_proc = subprocess.Popen([sys.executable, "webhook_server.py"])

# Start Discord bot
bot_proc = subprocess.Popen([sys.executable, "bot.py"])

try:
    webhook_proc.wait()
    bot_proc.wait()
except KeyboardInterrupt:
    webhook_proc.terminate()
    bot_proc.terminate()
    print("Stopped both webhook server and Discord bot.")
