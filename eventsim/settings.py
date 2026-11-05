"""EventSim settings, read from the environment (.env in the lab, never committed)."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EVENTSIM_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/eventsim.db"
    default_seed: int = 42

    token_reader: SecretStr
    token_editor: SecretStr
    token_admin: SecretStr

    # Test-only endpoints (/_test/*). Separate secret, harness only (FR-SIM-06).
    test_endpoints: bool = True
    test_token: SecretStr
