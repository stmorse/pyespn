from .api_gateway import APIGateway
from .league import League

def main() -> None:

    # setup league
    season = 2025
    league_id = 572240

    league = League(season=season, league_id=league_id)

    # do a test call to grab teams
    teams = league.get_teams()
    for t in teams:
        print(t.record.home.points_against)
        print(f"{t.name} (projected {t.current_projected_rank}) ({t.abbrev})")

    print()

    players = league.get_players()
    for p in players[:5]:
        print(p.first_name)

if __name__ == "__main__":
    main()