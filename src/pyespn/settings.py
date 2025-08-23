from pydantic_settings import BaseSettings, SettingsConfigDict

# handle user cookies from .env for authentication to ESPN API
class ESPNSettings(BaseSettings):
    swid: str
    espn_s2: str

    # Configure pydantic to load from `.env` automatically
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cookies(self) -> dict[str, str]:
        return {"SWID": self.swid, "espn_s2": self.espn_s2}