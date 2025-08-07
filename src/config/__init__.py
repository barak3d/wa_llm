from os import environ
from typing import Optional, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API settings
    port: int = 5001
    host: str = "0.0.0.0"

    # Database settings
    db_uri: str

    # WhatsApp settings
    whatsapp_host: str
    whatsapp_basic_auth_password: Optional[str] = None
    whatsapp_basic_auth_user: Optional[str] = None

    # Azure OpenAI settings
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_api_version: str = "2024-06-01"
    azure_openai_embedding_deployment: str
    azure_openai_chat_deployment: str
    
    # Model names
    embedding_model_name: str = "text-embedding-3-large"
    chat_model_name: str = "gpt-4o"

    # Optional settings
    debug: bool = False
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        arbitrary_types_allowed=True,
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def apply_env(self) -> Self:
        # Set Azure OpenAI environment variables for pydantic-ai
        if self.azure_openai_api_key:
            environ["OPENAI_API_KEY"] = self.azure_openai_api_key
        if self.azure_openai_endpoint:
            environ["OPENAI_BASE_URL"] = self.azure_openai_endpoint

        return self

    def get_azure_openai_client(self):
        """Get Azure OpenAI client for embeddings"""
        from openai import AsyncAzureOpenAI
        return AsyncAzureOpenAI(
            azure_endpoint=self.azure_openai_endpoint,
            api_version=self.azure_openai_api_version,
            api_key=self.azure_openai_api_key,
        )

    def get_chat_model(self):
        """Get pydantic-ai compatible chat model"""
        from pydantic_ai.models.openai import OpenAIModel
        from pydantic_ai.providers.openai import OpenAIProvider
        
        provider = OpenAIProvider(openai_client=self.get_azure_openai_client())
        return OpenAIModel(self.chat_model_name, provider=provider)
