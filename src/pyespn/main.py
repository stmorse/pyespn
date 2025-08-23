from .api_gateway import APIGateway, ValidationError
from .settings import ESPNSettings

def main() -> None:
    settings = ESPNSettings()  # loads cookies from .env
    gw = APIGateway(cookies=settings.cookies)
    try:
        # Example: provide your real values here
        season = 2025
        league_id = 572240

        teams = gw.get_league_teams(season=season, league_id=league_id)
        for t in teams:
            # pydantic models: dot access with normalized names
            print(f"{t.name} (projected #{t.current_projected_rank})")

    except ValidationError as e:
        # If the API shape drifts, you'll see an explicit validation error here.
        print("Validation error:", e)

    finally:
        gw.close()

if __name__ == "__main__":
    main()