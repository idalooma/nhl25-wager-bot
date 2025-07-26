import discord
from discord.ext import commands
from ea_api import get_latest_match, update_player_stats_from_match, summarize_match_for_lobby
from db import db


import discord
from discord import app_commands
from discord.ext import commands
from ea_api import get_latest_match, update_player_stats_from_match, summarize_match_for_lobby
from db import db

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="stats_list", description="Show a list of recent matches for a club.")
    async def stats_list(self, interaction: discord.Interaction, club_id: int):
        import traceback
        try:
            from ea_api import fetch_club_matches
            matches = fetch_club_matches(club_id)
            if not matches:
                await interaction.response.send_message("No recent matches found for this club.")
                return
            msg = ""
            for idx, match in enumerate(matches, 1):
                clubs = match.get("clubs", {})
                if len(clubs) != 2:
                    continue
                club_names = list(clubs.values())
                team1 = club_names[0]
                team2 = club_names[1]
                result = "won" if int(team1["goals"]) > int(team2["goals"]) else ("lost" if int(team1["goals"]) < int(team2["goals"]) else "tied")
                msg += f"{idx}. 🏒 *{team1['details']['name']}* {result} against *{team2['details']['name']}*\nFinal Score: *{team1['goals']} - {team2['goals']}*\n"
            await interaction.response.send_message(msg or "No valid matches found.")
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[DEBUG] Exception in stats_list: {tb}")
            await interaction.response.send_message(f"❌ An error occurred: {e}\n```{tb}```")

    @app_commands.command(name="show_stats", description="Show detailed stats for a match by club and match number from stats_list.")
    async def show_stats(self, interaction: discord.Interaction, club_id: int, match_number: int):
        import traceback
        try:
            await interaction.response.defer()  # Always defer immediately
            from ea_api import fetch_club_matches
            from cogs.lobby import format_match_stats
            matches = fetch_club_matches(club_id)
            if not matches or match_number < 1 or match_number > len(matches):
                await interaction.followup.send("Invalid match number or no matches found.")
                return
            match = matches[match_number - 1]
            clubs = match.get("clubs", {})
            if len(clubs) != 2:
                await interaction.followup.send("Could not find both teams in the match data.")
                return
            # Prepare team names and stats for the formatter
            club_ids = list(clubs.keys())
            team1_id, team2_id = club_ids[0], club_ids[1]
            team1_name = clubs[team1_id]["details"]["name"]
            team2_name = clubs[team2_id]["details"]["name"]
            stat_labels = [
                "Goals", "Assists", "Penalty Minutes", "Skater Shots", "Hits", "Faceoff Wins", "Giveaways", "Takeaways", "Saves", "Goalie Shots", "Goals Against", "Save Percentage"
            ]
            def collect_team_stats(cid):
                club = clubs[cid]
                stats = {
                    "Goals": int(club.get("goals", 0)),
                    "Assists": 0,
                    "Penalty Minutes": 0,
                    "Skater Shots": int(club.get("shots", 0)),
                    "Hits": 0,
                    "Faceoff Wins": 0,
                    "Giveaways": 0,
                    "Takeaways": 0,
                    "Saves": 0,
                    "Goalie Shots": 0,
                    "Goals Against": int(club.get("goalsAgainst", 0)),
                    "Save Percentage": None
                }
                players = match.get("players", {}).get(str(cid), {})
                for player_id, player in players.items():
                    stats["Assists"] += int(player.get("skassists", 0))
                    stats["Penalty Minutes"] += int(player.get("skpim", 0))
                    stats["Hits"] += int(player.get("skhits", 0))
                    stats["Faceoff Wins"] += int(player.get("skfow", 0))
                    stats["Giveaways"] += int(player.get("skgiveaways", 0))
                    stats["Takeaways"] += int(player.get("sktakeaways", 0))
                    stats["Saves"] += int(player.get("glsaves", 0))
                    stats["Goalie Shots"] += int(player.get("glshots", 0))
                if stats["Goalie Shots"] > 0:
                    stats["Save Percentage"] = f"{(stats['Saves'] / stats['Goalie Shots']) * 100:.2f}"
                else:
                    stats["Save Percentage"] = "0"
                return stats, players
            team1_stats, team1_players_dict = collect_team_stats(team1_id)
            team2_stats, team2_players_dict = collect_team_stats(team2_id)
            # Prepare team_stats for formatter
            team_stats = []
            for label in stat_labels:
                team_stats.append((label, team1_stats[label], team2_stats[label]))
            # Prepare player stats for formatter (list of tuples)
            def player_row(player_id, player):
                return (
                    player.get('name', player_id),
                    player.get('pos', ''),
                    player.get('goals', 0),
                    player.get('skassists', 0),
                    player.get('points', 0),
                    player.get('plusmin', 0),
                    player.get('skpim', 0),
                    player.get('shots', 0),
                    player.get('skhits', 0),
                    player.get('skfow', 0),
                    player.get('skgiveaways', 0),
                    player.get('sktakeaways', 0),
                    player.get('glsaves', 0),
                    player.get('glshots', 0),
                    player.get('goalsAgainst', 0),
                    player.get('savePct', 0)
                )
            team1_players = [player_row(pid, p) for pid, p in team1_players_dict.items()]
            team2_players = [player_row(pid, p) for pid, p in team2_players_dict.items()]
            # Use the Markdown formatter
            msg = format_match_stats(match_number, team1_name, team2_name, team_stats, team1_players, team2_players)
            # Send in chunks if too long
            max_len = 1900
            lines = msg.split('\n')
            chunk = ''
            for line in lines:
                if len(chunk) + len(line) + 2 > max_len:
                    await interaction.followup.send(f"```{chunk}```")
                    chunk = ''
                chunk += line + '\n'
            if chunk:
                await interaction.followup.send(f"```{chunk}```")
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[DEBUG] Exception in show_stats: {tb}")
            await interaction.followup.send(f"❌ An error occurred: {e}\n```{tb}```")

    @app_commands.command(name="stats", description="Show stats for a user.")
    async def stats(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        user = db.get_user(str(member.id))
        if not user:
            await interaction.response.send_message(f"No user found for {member.display_name}.")
            return
        user_id = user[0]
        stats = db.get_stats(user_id)
        if not stats:
            await interaction.response.send_message(f"No stats found for {member.display_name}.")
            return
        games, wins, losses, earnings, goals, assists = stats[2], stats[3], stats[4], stats[5], stats[6], stats[7]
        await interaction.response.send_message(
            f"Stats for {member.display_name}:\n"
            f"Games Played: {games}\nWins: {wins}\nLosses: {losses}\nGoals: {goals}\nAssists: {assists}\nEarnings: ${earnings/100:.2f}"
        )

    @app_commands.command(name="earnings", description="Show your wallet balance.")
    async def earnings(self, interaction: discord.Interaction):
        import traceback
        try:
            discord_id = str(interaction.user.id)
            username = interaction.user.name
            user = db.get_user(discord_id)
            if not user:
                # Try by username as fallback
                user = db.get_user(username)
            if not user:
                await interaction.response.send_message(f"No user found for {interaction.user.display_name}.")
                return
            wallet_cents = user[3]  # Assuming user[3] is wallet amount in cents
            await interaction.response.send_message(
                f"Your wallet balance: ${wallet_cents/100:.2f}"
            )
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[DEBUG] Exception in earnings: {tb}")
            await interaction.response.send_message(f"❌ An error occurred: {e}\n```{tb}```")

async def setup(bot):
    await bot.add_cog(Stats(bot))
