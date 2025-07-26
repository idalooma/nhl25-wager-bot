import sys
from ea_api import fetch_club_matches
import operator

def get_team_stats(club, players):
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
        stats["Save Percentage"] = (stats['Saves'] / stats['Goalie Shots']) * 100
    else:
        stats["Save Percentage"] = 0
    return stats

def parse_filter(expr):
    # e.g. '>=3' or '<10' or '==5'
    ops = {'>=': operator.ge, '<=': operator.le, '>': operator.gt, '<': operator.lt, '==': operator.eq}
    for op_str, op_func in ops.items():
        if expr.startswith(op_str):
            try:
                val = float(expr[len(op_str):])
                return op_func, val
            except:
                return None, None
    return None, None

if __name__ == "__main__":
    print("EA NHL25 Advanced Match Analysis Script")
    club_id = input("Enter club_id: ").strip()
    if not club_id.isdigit():
        print("Invalid club_id. Must be an integer.")
        sys.exit(1)
    club_id = int(club_id)

    num_matches = input("How many recent matches to analyze? (default 5): ").strip()
    num_matches = int(num_matches) if num_matches.isdigit() else 5

    # List available stats
    stat_labels = [
        "Goals", "Assists", "Penalty Minutes", "Skater Shots", "Hits", "Faceoff Wins", "Giveaways", "Takeaways", "Saves", "Goalie Shots", "Goals Against", "Save Percentage"
    ]
    print("Available stats:", ', '.join(stat_labels))
    filter_stats = input("Which stat(s) to filter by? (comma-separated, blank for none): ").strip()
    filters = {}
    if filter_stats:
        for stat in filter_stats.split(','):
            stat = stat.strip()
            if stat in stat_labels:
                expr = input(f"Enter filter for {stat} (e.g., '>=3', '<10', blank for none): ").strip()
                if expr:
                    op, val = parse_filter(expr)
                    if op:
                        filters[stat] = (op, val)

    print("\nFetching recent matches...")
    matches = fetch_club_matches(club_id)
    matches = matches[:num_matches]
    print(f"Fetched {len(matches)} matches.")

    # Ask for output type
    print("Show (1) summary, (2) per-match details, or (3) both?")
    out_type = input("Enter 1, 2, or 3: ").strip()

    filtered = []
    for m in matches:
        clubs = m.get("clubs", {})
        if len(clubs) != 2:
            continue
        team_stats = []
        for cid, club in clubs.items():
            players = m.get("players", {}).get(str(cid), {})
            stats = get_team_stats(club, players)
            team_stats.append((club["details"]["name"], stats))
        # Apply filters to both teams
        passes = True
        for stat, (op, val) in filters.items():
            if not (op(team_stats[0][1][stat], val) or op(team_stats[1][1][stat], val)):
                passes = False
                break
        if passes:
            filtered.append(team_stats)

    # Summary output
    if out_type in ('1', '3'):
        print("\n=== Summary Table ===")
        from collections import defaultdict
        agg = [defaultdict(float), defaultdict(float)]
        for teams in filtered:
            for i, (name, stats) in enumerate(teams):
                for stat in stat_labels:
                    agg[i][stat] += stats[stat] if isinstance(stats[stat], (int, float)) else 0
        count = len(filtered)
        if count:
            print(f"{'':<20}{'Team 1':<15}{'Team 2':<15}")
            for stat in stat_labels:
                v0 = agg[0][stat]/count if count else 0
                v1 = agg[1][stat]/count if count else 0
                print(f"{stat:<20}{v0:<15.2f}{v1:<15.2f}")
        else:
            print("No matches met the filter criteria.")

    # Per-match details
    if out_type in ('2', '3'):
        print("\n=== Per-Match Details ===")
        for i, teams in enumerate(filtered):
            print(f"\n--- Match {i+1} ---")
            print(f"{'':<20}{teams[0][0]:<15}{teams[1][0]:<15}")
            for stat in stat_labels:
                v0 = teams[0][1][stat]
                v1 = teams[1][1][stat]
                print(f"{stat:<20}{str(v0):<15}{str(v1):<15}")
