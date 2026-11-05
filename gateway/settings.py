"""Gateway settings, read from the environment (`.env` in the lab).

The gateway holds two kinds of secrets (SR-01, SR-14):
- one MCP bearer token per role (`GATEWAY_TOKEN_*`): what the agent side (n8n) presents;
- one EventSim token per role (`EVENTSIM_TOKEN_*`): never leaves the gateway.

It never holds `EVENTSIM_TEST_TOKEN`: the test endpoints are unreachable from here even if a
path check were bypassed (FR-SIM-06, defence in depth).
"""

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from eventsim.models import Role


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    eventsim_url: str = Field(
        default="http://eventsim:8000", validation_alias=AliasChoices("EVENTSIM_URL")
    )
    eventsim_token_reader: SecretStr = Field(validation_alias="EVENTSIM_TOKEN_READER")
    eventsim_token_editor: SecretStr = Field(validation_alias="EVENTSIM_TOKEN_EDITOR")
    eventsim_token_admin: SecretStr = Field(validation_alias="EVENTSIM_TOKEN_ADMIN")

    gateway_token_reader: SecretStr = Field(validation_alias="GATEWAY_TOKEN_READER")
    gateway_token_editor: SecretStr = Field(validation_alias="GATEWAY_TOKEN_EDITOR")
    gateway_token_admin: SecretStr = Field(validation_alias="GATEWAY_TOKEN_ADMIN")

    config_name: str = Field(validation_alias="EVENTGUARD_CONFIG")

    host: str = Field(default="0.0.0.0", validation_alias="GATEWAY_HOST")  # noqa: S104 (container)
    port: int = Field(default=8100, validation_alias="GATEWAY_PORT")
    mcp_path: str = Field(default="/mcp", validation_alias="GATEWAY_MCP_PATH")
    # Host header values accepted by the MCP endpoint (DNS-rebinding protection).
    allowed_hosts: list[str] = Field(
        default=["gateway:*", "localhost:*", "127.0.0.1:*"],
        validation_alias="GATEWAY_ALLOWED_HOSTS",
    )

    def eventsim_tokens(self) -> dict[Role, SecretStr]:
        return {
            Role.reader: self.eventsim_token_reader,
            Role.editor: self.eventsim_token_editor,
            Role.admin: self.eventsim_token_admin,
        }

    def gateway_tokens(self) -> dict[Role, SecretStr]:
        return {
            Role.reader: self.gateway_token_reader,
            Role.editor: self.gateway_token_editor,
            Role.admin: self.gateway_token_admin,
        }
