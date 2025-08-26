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
        # print(t.record.home.points_against)
        # print(t.record)
        # print(t.record.home)
        print(t)
        print()

    print()

    players = league.get_players()
    for p in players[:5]:
        print(p)
        print()

if __name__ == "__main__":
    main()