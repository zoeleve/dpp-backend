from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DPP Management Platform"
    
    # Database settings
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: str
    POSTGRES_DB: str

    # Security settings
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Fuseki settings
    FUSEKI_HOST: str = "localhost"
    FUSEKI_PORT: int = 3030
    FUSEKI_DATASET_NAME: str = "dpp_dataset"

    LOG_LEVEL: str

    @property
    def FUSEKI_ENDPOINT(self) -> str:
        """Base URL for SPARQL query endpoint."""
        return f"http://{self.FUSEKI_HOST}:{self.FUSEKI_PORT}/{self.FUSEKI_DATASET_NAME}"

    @property
    def FUSEKI_QUERY_URL(self) -> str:
        """Full URL for SPARQL SELECT/CONSTRUCT queries."""
        # Updated to /sparql based on probe results for secoresearch/fuseki
        return f"{self.FUSEKI_ENDPOINT}/sparql"

    @property
    def FUSEKI_UPDATE_URL(self) -> str:
        """Full URL for SPARQL INSERT/DELETE updates."""
        # Assuming /update works, but if query is /sparql, update might be /update or /sparql too
        return f"{self.FUSEKI_ENDPOINT}/update"

    @property
    def FUSEKI_DATA_URL(self) -> str:
        """Full URL for direct Graph data operations (PUT/POST RDF)."""
        return f"{self.FUSEKI_ENDPOINT}/data"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
