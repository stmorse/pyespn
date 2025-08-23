from .api_gateway import APIGateway
from .league import League

def main() -> None:

    # setup league
    season = 2025
    league_id = 572240

    league = League(season=season, id=league_id)

    # do a test call to grab teams
    teams = league.get_teams()
    for t in teams:
        print(f"{t.name} (projected #{t.current_projected_rank})")

if __name__ == "__main__":
    main()