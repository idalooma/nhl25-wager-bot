
from typing import Dict, Any
from db import db

# Example mapping: EA player name -> Discord ID
# You should expand this mapping as needed
EA_TO_DISCORD = {
    'g25pofqnudae': 'incredible_puppy_49731',
}

def get_discord_id_from_ea_name(ea_name: str) -> str:
    """
    Map an EA player name to a Discord user ID.
    """
    return EA_TO_DISCORD.get(ea_name)

def update_player_stats_from_match(match: Dict[str, Any]):
    """
    Update player stats in the database based on a match dict.
    """
    stats = parse_match_stats(match)
    players = stats.get('players', {})
    winner = stats.get('winner')
    # Example: players is a dict with team keys, each with player dicts
    for team_key, team_players in players.items():
        for ea_name, pdata in team_players.items():
            discord_id = get_discord_id_from_ea_name(ea_name)
            if not discord_id:
                continue  # Skip if not mapped
            user = db.get_user(discord_id)
            if not user:
                continue
            user_id = user[0]
            goals = int(pdata.get('goals', 0))
            assists = int(pdata.get('assists', 0))
            win = 1 if team_key == winner else 0
            loss = 1 if team_key != winner else 0
            # Update stats table
            db.update_stats(user_id, games_played=1, wins=win, losses=loss, goals=goals, assists=assists)

def summarize_match_for_lobby(match: Dict[str, Any], club_id: int = None) -> str:
    """
    Return a detailed summary string for the bot to post in Discord, matching the working script output.
    """
    if club_id is None:
        # Try to infer club_id from match structure
        clubs = match.get("clubs", {})
        for cid, club in clubs.items():
            if club.get("details", {}).get("clubId"):
                club_id = club["details"]["clubId"]
                break
    team = None
    opponent = None
    for cid, club in match.get("clubs", {}).items():
        if club.get("details", {}).get("clubId") == int(club_id):
            team = club
        else:
            opponent = club
    if not team or not opponent:
        return "⚠️ Could not identify team/opponent correctly."
    result = "won" if int(team["goals"]) > int(opponent["goals"]) else (
             "lost" if int(team["goals"]) < int(opponent["goals"]) else "tied")
    stats = {
        "Goals": int(team.get("goals", 0)),
        "Assists": 0,
        "Penalty Minutes": 0,
        "Shots": int(team.get("shots", 0)),
        "Hits": 0,
        "Faceoff Wins": 0,
        "Giveaways": 0,
        "Takeaways": 0,
        "Saves": 0,
        "Goals Against": int(team.get("goalsAgainst", 0)),
        "Save Percentage": None
    }
    players = match.get("players", {}).get(str(club_id), {})
    for player_id, player in players.items():
        stats["Assists"] += int(player.get("skassists", 0))
        stats["Penalty Minutes"] += int(player.get("skpim", 0))
        stats["Hits"] += int(player.get("skhits", 0))
        stats["Faceoff Wins"] += int(player.get("skfow", 0))
        stats["Giveaways"] += int(player.get("skgiveaways", 0))
        stats["Takeaways"] += int(player.get("sktakeaways", 0))
        stats["Saves"] += int(player.get("glsaves", 0))
        shots_faced = int(player.get("glshots", 0))
        if shots_faced > 0:
            stats["Save Percentage"] = f"{(stats['Saves'] / shots_faced) * 100:.2f}%"
    summary = (
        f"\n\U0001F3D2 **{team['details']['name']}** {result} against **{opponent['details']['name']}**\n"
        f"Final Score: **{team['goals']} - {opponent['goals']}**\n"
        f"Played at: {datetime.fromtimestamp(match['timestamp']).strftime('%Y-%m-%d %H:%M UTC')}\n"
    )
    summary += "\n\U0001F4CA **Team Stats:**\n"
    for stat, value in stats.items():
        summary += f"- {stat}: {value}\n"
    return summary

import requests
import json
from datetime import datetime
from typing import List, Dict, Any

EA_API_BASE = "https://proclubs.ea.com/api/nhl/clubs/matches"

def fetch_club_matches(club_id: int, platform: str = "common-gen5", match_type: str = "gameType5") -> list:
    """
    Fetch recent matches for a club from the EA NHL25 API.
    Returns a list of match dicts.
    Handles both dict and list responses from the API.
    """
    url = EA_API_BASE
    params = {
        "platform": platform,
        "clubIds": str(club_id),
        "matchType": match_type
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data.get(str(club_id), [])
        elif isinstance(data, list):
            return data
        else:
            return []
    except Exception as e:
        print(f"❌ Error fetching matches: {e}")
        return []

def get_match_summary(match: Dict[str, Any], club_id: int) -> str:
    """
    Return a detailed summary for a match for the given club_id.
    """
    team = None
    opponent = None
    for cid, club in match.get("clubs", {}).items():
        if club.get("details", {}).get("clubId") == int(club_id):
            team = club
        else:
            opponent = club
    if not team or not opponent:
        return "⚠️ Could not identify team/opponent correctly."
    result = "won" if int(team["goals"]) > int(opponent["goals"]) else (
             "lost" if int(team["goals"]) < int(opponent["goals"]) else "tied")
    stats = {
        "Goals": int(team.get("goals", 0)),
        "Assists": 0,
        "Penalty Minutes": 0,
        "Shots": int(team.get("shots", 0)),
        "Hits": 0,
        "Faceoff Wins": 0,
        "Giveaways": 0,
        "Takeaways": 0,
        "Saves": 0,
        "Goals Against": int(team.get("goalsAgainst", 0)),
        "Save Percentage": None
    }
    players = match.get("players", {}).get(str(club_id), {})
    for player_id, player in players.items():
        stats["Assists"] += int(player.get("skassists", 0))
        stats["Penalty Minutes"] += int(player.get("skpim", 0))
        stats["Hits"] += int(player.get("skhits", 0))
        stats["Faceoff Wins"] += int(player.get("skfow", 0))
        stats["Giveaways"] += int(player.get("skgiveaways", 0))
        stats["Takeaways"] += int(player.get("sktakeaways", 0))
        stats["Saves"] += int(player.get("glsaves", 0))
        shots_faced = int(player.get("glshots", 0))
        if shots_faced > 0:
            stats["Save Percentage"] = f"{(stats['Saves'] / shots_faced) * 100:.2f}%"
    summary = (
        f"\n🏒 **{team['details']['name']}** {result} against **{opponent['details']['name']}**\n"
        f"Final Score: **{team['goals']} - {opponent['goals']}**\n"
        f"Played at: {datetime.fromtimestamp(match['timestamp']).strftime('%Y-%m-%d %H:%M UTC')}\n"
    )
    summary += "\n📊 **Team Stats:**\n"
    for stat, value in stats.items():
        summary += f"- {stat}: {value}\n"
    return summary

def parse_match_stats(match: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant stats from a match dict.
    Returns a dict with winner, teams, players, goals, assists, etc.
    """
    stats = {
        'match_id': match.get('matchId'),
        'timestamp': match.get('timestamp'),
        'home': match.get('home', {}),
        'away': match.get('away', {}),
        'winner': match.get('winner'),
        'players': match.get('players', {}),
        'goals': match.get('goals', {}),
        'assists': match.get('assists', {}),
        'result': match.get('result'),
    }
    return stats

def get_latest_match(club_id: int) -> Dict[str, Any]:
    """
    Fetch and return the latest match for a club.
    Handles both list and dict responses from the EA API.
    """
    matches = fetch_club_matches(club_id)
    if isinstance(matches, list) and matches:
        return matches[0]
    elif isinstance(matches, dict):
        # If dict, try to get matches for the club_id
        club_matches = matches.get(str(club_id), [])
        if club_matches:
            return club_matches[0]
        else:
            return {}
    else:
        return {}
