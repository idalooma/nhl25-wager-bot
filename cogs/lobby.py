# Utility function to format stats as Markdown tables for Discord
def format_match_stats(match_number, team1_name, team2_name, team_stats, team1_players, team2_players):
    # Team stats table
    lines = []
    lines.append(f"=== Detailed Stats for Match {match_number}: {team1_name} vs {team2_name} ===\n")
    lines.append(f"| Stat             | {team1_name} | {team2_name} |")
    lines.append(f"|------------------|{'-'*len(team1_name):-<21}|{'-'*len(team2_name):-<21}|")
    for stat, t1, t2 in team_stats:
        lines.append(f"| {stat:<16} | {t1:<19} | {t2:<19} |")
    lines.append("")
    # Player stats tables
    def player_table(title, players):
        if not players:
            return f"**{title}**\n_No players_\n"
        header = "| User ID | Pos | G | A | Pts | +/- | PIM | S | H | FO | GA | TA | Sv | GS | GA | Sv% |"
        sep =    "|---------|-----|---|---|-----|-----|-----|---|---|----|----|----|----|----|----|-----|"
        rows = [header, sep]
        for p in players:
            # p should be a tuple/list of stats in order
            rows.append("| " + " | ".join(str(x) for x in p) + " |")
        return f"**{title}**\n" + "\n".join(rows) + "\n"
    lines.append(player_table(team1_name + " Player Stats", team1_players))
    lines.append(player_table(team2_name + " Player Stats", team2_players))
    return "\n".join(lines)
import discord
from discord.ext import commands
from db import db


import discord
from discord import app_commands
from discord.ext import commands
from db import db

class Lobby(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="create_lobby", description="Create a new 6v6 wager lobby.")
    async def create_lobby(self, interaction: discord.Interaction, wager: float, club_id: int):
        import traceback
        await interaction.response.defer()
        discord_id = str(interaction.user.id)
        username = interaction.user.name
        try:
            db.add_user(discord_id, username)
            user = db.get_user(discord_id)
            wager_cents = int(wager * 100)
            if not user or user[3] < wager_cents:
                await interaction.followup.send("You do not have enough funds in your wallet to create this lobby.")
                return
            import random, string
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            db.create_lobby(code, discord_id, wager_cents, club_id)
            db.update_lobby_teams(code, team1=discord_id)
            db.update_wallet(discord_id, -wager_cents)
            db.add_transaction(user[0], "wager", -wager_cents, None)
            await interaction.followup.send(f"Lobby created!\nCode: `{code}`\nWager: ${wager:.2f}\nClub ID: {club_id}\nYou have been added to Team 1 and ${wager:.2f} has been debited from your wallet.\nUse `/join {code} team1|team2` to join a team.")
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[DEBUG] Exception in create_lobby: {tb}")
            await interaction.followup.send(f"❌ An error occurred: {e}\n```{tb}```")

    @app_commands.command(name="join", description="Join a team in a lobby.")
    async def join(self, interaction: discord.Interaction, code: str, team: str):
        import traceback
        try:
            lobby = db.get_lobby_by_code(code)
            if not lobby:
                await interaction.response.send_message("Lobby not found.")
                return
            status = lobby[6] if len(lobby) > 6 else None
            if status != "open":
                await interaction.response.send_message("Lobby is locked and cannot be joined.")
                return
            discord_id = str(interaction.user.id)
            username = interaction.user.name
            db.add_user(discord_id, username)
            user = db.get_user(discord_id)
            wager_cents = lobby[3]
            team1 = lobby[4] or ""
            team2 = lobby[5] or ""
            team1_members = team1.split(",") if team1 else []
            team2_members = team2.split(",") if team2 else []
            if discord_id in team1_members or discord_id in team2_members:
                await interaction.response.send_message("You are already in a team in this lobby.")
                return
            if not user or user[3] < wager_cents:
                await interaction.response.send_message("You do not have enough funds in your wallet to join this lobby.")
                return
            if team == "team1":
                if len(team1_members) >= 6:
                    await interaction.response.send_message(f"Team1 is already full!")
                    return
                team1_members.append(discord_id)
            elif team == "team2":
                if len(team2_members) >= 6:
                    await interaction.response.send_message(f"Team2 is already full!")
                    return
                team2_members.append(discord_id)
            else:
                await interaction.response.send_message("Invalid team. Use 'team1' or 'team2'.")
                return
            db.update_wallet(discord_id, -wager_cents)
            db.add_transaction(user[0], "wager", -wager_cents, None)
            db.update_lobby_teams(code, team1=",".join(team1_members), team2=",".join(team2_members))
            if hasattr(self, 'lobby_meta') and code in self.lobby_meta:
                if team == "team1":
                    self.lobby_meta[code]['team1'].append(discord_id)
                else:
                    self.lobby_meta[code]['team2'].append(discord_id)
            await interaction.response.send_message(f"{username} joined {team} in lobby {code}! ${wager_cents/100:.2f} has been debited from your wallet.")
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[DEBUG] Exception in join: {tb}")
            await interaction.response.send_message(f"❌ An error occurred: {e}\n```{tb}```")

    @app_commands.command(name="leave", description="Leave a lobby.")
    async def leave(self, interaction: discord.Interaction, code: str):
        import traceback
        try:
            lobby = db.get_lobby_by_code(code)
            if not lobby:
                await interaction.response.send_message("Lobby not found.")
                return
            discord_id = str(interaction.user.id)
            user = db.get_user(discord_id)
            team1 = lobby[4] or ""
            team2 = lobby[5] or ""
            status = lobby[6] if len(lobby) > 6 else None
            wager_cents = lobby[3]
            changed = False
            for team, idx in [(team1, 4), (team2, 5)]:
                members = team.split(",") if team else []
                if discord_id in members:
                    members.remove(discord_id)
                    new_team = ",".join(members)
                    if idx == 4:
                        db.update_lobby_teams(code, team1=new_team)
                    else:
                        db.update_lobby_teams(code, team2=new_team)
                    changed = True
            if changed:
                if status == "open":
                    if user:
                        db.update_wallet(discord_id, wager_cents)
                        db.add_transaction(user[0], "refund", wager_cents, None)
                    await interaction.response.send_message(f"You left lobby {code}. Your wager has been refunded.")
                else:
                    await interaction.response.send_message(f"You left lobby {code}.")
            else:
                await interaction.response.send_message("You are not in this lobby.")
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[DEBUG] Exception in leave: {tb}")
            await interaction.response.send_message(f"❌ An error occurred: {e}\n```{tb}```")

    @app_commands.command(name="start_game", description="Lock teams and start the game.")
    async def start_game(self, interaction: discord.Interaction, code: str):
        import traceback
        try:
            lobby = db.get_lobby_by_code(code)
            if not lobby:
                await interaction.response.send_message("Lobby not found.")
                return
            discord_id = str(interaction.user.id)
            creator_id = lobby[2]
            if discord_id != creator_id:
                await interaction.response.send_message("Only the lobby creator can start the game.")
                return
            team1 = lobby[4] or ""
            team2 = lobby[5] or ""
            team1_members = team1.split(",") if team1 else []
            team2_members = team2.split(",") if team2 else []
            if len(team1_members) != 6 or len(team2_members) != 6:
                await interaction.response.send_message("Cannot start game: Both teams must have exactly 6 members.")
                return
            from datetime import datetime
            db.update_lobby_status(code, status="started", start_time=int(datetime.utcnow().timestamp()))
            await interaction.response.send_message(f"Lobby {code} started! Teams are now locked.")
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[DEBUG] Exception in start_game: {tb}")
            await interaction.response.send_message(f"❌ An error occurred: {e}\n```{tb}```")

    @app_commands.command(name="report_result", description="Validate and report the result of a lobby using EA API.")
    async def report_result(self, interaction: discord.Interaction, code: str):
        import traceback
        try:
            lobby = db.get_lobby_by_code(code)
            if not lobby:
                await interaction.response.send_message("Lobby not found.")
                return
            club_id = lobby[8]
            start_time = lobby[9]
            team1 = lobby[4] or ""
            team2 = lobby[5] or ""
            team1_members = team1.split(",") if team1 else []
            team2_members = team2.split(",") if team2 else []
            from ea_api import fetch_club_matches
            matches = fetch_club_matches(club_id)
            found_match = None
            for match in matches:
                if match.get('timestamp', 0) < start_time:
                    continue
                found_match = match
                break
            if not found_match:
                await interaction.response.send_message("No matching EA match found for this lobby.")
                return
            team1_score = int(found_match['clubs'][str(club_id)]['goals'])
            opponent_id = [cid for cid in found_match['clubs'] if int(cid) != int(club_id)][0]
            team2_score = int(found_match['clubs'][opponent_id]['goals'])
            if team1_score > team2_score:
                winning_team = 'team1'
                winners = team1_members
            elif team2_score > team1_score:
                winning_team = 'team2'
                winners = team2_members
            else:
                await interaction.response.send_message("Game was a tie. No payout.")
                db.update_lobby_status(code, status="completed")
                return
            wager_cents = lobby[3]
            payout = wager_cents * 2
            for discord_id in winners:
                user = db.get_user(discord_id)
                if user:
                    db.update_wallet(discord_id, payout)
                    db.add_transaction(user[0], "payout", payout, None)
            db.update_lobby_status(code, status="completed")
            await interaction.response.send_message(f"Result for lobby {code}: {winning_team} wins! Each winner has been credited ${payout/100:.2f}.")
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[DEBUG] Exception in report_result: {tb}")
            await interaction.response.send_message(f"❌ An error occurred: {e}\n```{tb}```")

    @app_commands.command(name="lobbies", description="List open lobbies.")
    async def lobbies(self, interaction: discord.Interaction):
        import traceback
        try:
            import sqlite3
            with sqlite3.connect("nhl25bot.db") as conn:
                c = conn.cursor()
                c.execute("SELECT code, wager_cents, status FROM lobbies WHERE status = 'open'")
                rows = c.fetchall()
            if not rows:
                await interaction.response.send_message("No open lobbies.")
                return
            msg = "Open lobbies:\n" + "\n".join([f"Code: {r[0]}, Wager: ${r[1]/100:.2f}, Status: {r[2]}" for r in rows])
            await interaction.response.send_message(msg)
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[DEBUG] Exception in lobbies: {tb}")
            await interaction.response.send_message(f"❌ An error occurred: {e}\n```{tb}```")

    @app_commands.command(name="cancel", description="Cancel a lobby.")
    async def cancel(self, interaction: discord.Interaction, code: str):
        import traceback
        try:
            await interaction.response.defer()
            lobby = db.get_lobby_by_code(code)
            if not lobby:
                await interaction.followup.send("Lobby not found.")
                return
            discord_id = str(interaction.user.id)
            creator_id = lobby[2]
            if discord_id != creator_id:
                await interaction.followup.send("Only the lobby creator can cancel this lobby.")
                return
            status = lobby[6] if len(lobby) > 6 else None
            if status in ("open", "started"):
                team1 = lobby[4] or ""
                team2 = lobby[5] or ""
                all_members = (team1.split(",") if team1 else []) + (team2.split(",") if team2 else [])
                wager_cents = lobby[3]
                for member_id in all_members:
                    user = db.get_user(member_id)
                    if user:
                        db.update_wallet(member_id, wager_cents)
                        db.add_transaction(user[0], "refund", wager_cents, None)
            db.update_lobby_status(code, status="cancelled")
            await interaction.followup.send(f"Lobby {code} has been cancelled and all funds have been refunded.")
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[DEBUG] Exception in cancel: {tb}")
            await interaction.followup.send(f"❌ An error occurred: {e}\n```{tb}```")

    @app_commands.command(name="view_lobby", description="View members in each team for a lobby.")
    async def view_lobby(self, interaction: discord.Interaction, code: str):
        import traceback
        try:
            await interaction.response.defer()
            lobby = db.get_lobby_by_code(code)
            if not lobby:
                await interaction.followup.send("Lobby not found.")
                return
            team1 = lobby[4] or ""
            team2 = lobby[5] or ""
            team1_members = team1.split(",") if team1 else []
            team2_members = team2.split(",") if team2 else []
            def mention_or_name(discord_id):
                member = interaction.guild.get_member(int(discord_id))
                if member:
                    return member.mention
                user = db.get_user(discord_id)
                if user and user[1]:
                    return user[1]
                return discord_id
            team1_names = [mention_or_name(did) for did in team1_members]
            team2_names = [mention_or_name(did) for did in team2_members]
            msg = f"Lobby {code} members:\nTeam 1: {', '.join(team1_names) if team1_names else 'None'}\nTeam 2: {', '.join(team2_names) if team2_names else 'None'}"
            await interaction.followup.send(msg)
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[DEBUG] Exception in view_lobby: {tb}")
            await interaction.followup.send(f"❌ An error occurred: {e}\n```{tb}```")

    @app_commands.command(name="help", description="Show all available commands and their descriptions.")
    async def help(self, interaction: discord.Interaction):
        import traceback
        try:
            commands_info = [
                ("/create_lobby [wager] [club_id]", "Create a new 6v6 wager lobby. You are auto-added to Team 1 and must have enough funds in your wallet."),
                ("/join [lobby_code] [team1|team2]", "Join a team in a lobby. Wallet is checked and debited for the wager amount."),
                ("/leave [lobby_code]", "Leave a lobby before game start for a full refund. After start, leaving forfeits your wager."),
                ("/start_game [lobby_code]", "Lock teams and start the game (creator only, both teams must have 6 members)."),
                ("/cancel [lobby_code]", "Cancel a lobby (creator only, refunds all players)."),
                ("/report_result [lobby_code]", "Validate the result using the EA API and automatically pay out winners."),
                ("/lobbies", "List all open lobbies you can join."),
                ("/view_lobby [lobby_code]", "View members in each team for a specific lobby."),
                ("/deposit [amount]", "Deposit money into your wallet using PayPal. You will receive a payment link."),
                ("/withdraw [amount] [paypal_email]", "Withdraw money from your wallet. Direct PayPal payout. If you have saved your PayPal email, you can omit it."),
                ("/earnings", "Show your wallet balance."),
                ("/transactions", "List your transaction history."),
                ("/stats_list [club_id]", "Show a numbered list of recent matches for a club, with a summary for each."),
                ("/show_stats [club_id] [match_number]", "Show detailed stats for both teams and all players for the selected match from the list."),
            ]
            msg = "**Available Commands:**\n"
            for cmd, desc in commands_info:
                msg += f"{cmd} - {desc}\n"
            await interaction.response.send_message(msg)
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[DEBUG] Exception in help: {tb}")
            await interaction.response.send_message(f"❌ An error occurred: {e}\n```{tb}```")
async def setup(bot):
    await bot.add_cog(Lobby(bot))

@commands.Cog.listener()
async def on_ready():
    await bot.tree.sync()
    print(f"Synced commands for {bot.user}")
