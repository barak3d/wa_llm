# Migration Summary: Logfire, Voyage AI, and Anthropic to Azure OpenAI

This document summarizes the migration from logfire, Voyage AI, and Anthropic dependencies to Azure OpenAI services.

## Changes Made

### 1. Dependencies Updated

**Removed:**
- `logfire[fastapi,httpx,sqlalchemy,system-metrics]>=3.12.0`
- `pydantic-ai[logfire]>=0.2.14` 
- `voyageai>=0.3.2`

**Added:**
- `pydantic-ai>=0.2.14` (without logfire)
- `openai>=1.12.0`
- `azure-identity>=1.15.0`

### 2. Configuration Changes

**Updated `src/config/__init__.py`:**
- Removed: `anthropic_api_key`, `voyage_api_key`, `voyage_max_retries`, `logfire_token`
- Added: `azure_openai_api_key`, `azure_openai_endpoint`, `azure_openai_api_version`, `azure_openai_embedding_deployment`, `azure_openai_chat_deployment`

**Updated `.env` file:**
```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o

# Model Names (configurable)
EMBEDDING_MODEL_NAME=text-embedding-3-large
CHAT_MODEL_NAME=gpt-4o
```

### 3. Application Changes

**Main Application (`app/main.py`):**
- Removed all logfire instrumentation calls
- Updated embedding client from `AsyncClient` (Voyage) to `AsyncAzureOpenAI`
- Removed logfire configuration and imports

**Embedding Service:**
- Replaced `src/utils/voyage_embed_text.py` with `src/utils/azure_openai_embed_text.py`
- Updated function signature and implementation for Azure OpenAI

### 4. AI Model Configuration Updates - Azure OpenAI Integration

All AI agents throughout the codebase have been updated to use proper Azure OpenAI integration with pydantic-ai:

**Before:**
```python
model="anthropic:claude-4-sonnet-20250514"
```

**After:**
```python
# Using Azure OpenAI with pydantic-ai
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

client = AsyncAzureOpenAI(
    azure_endpoint='...',
    api_version='2024-02-01',
    api_key='your-api-key',
)

model = OpenAIModel(
    'gpt-4o',
    provider=OpenAIProvider(openai_client=client),
)
agent = Agent(model)
```

The `Settings` class now provides:
- `get_azure_openai_client()` - Returns configured Azure OpenAI client
- `get_chat_model()` - Returns pydantic-ai compatible model with Azure provider

**Files updated:**
- `src/load_new_kbtopics/__init__.py`
- `src/handler/router.py` 
- `src/handler/knowledge_base_answers.py`
- `src/handler/whatsapp_group_link_spam.py`
- `src/summarize_and_send_to_groups/__init__.py`

### 5. Type Annotations Updated

All `AsyncClient` (VoyageAI) type annotations updated to `AsyncAzureOpenAI`:
- `src/api/deps.py`
- `src/api/load_new_kbtopics_api.py`
- `src/handler/base_handler.py`
- `src/handler/__init__.py`
- `src/handler/router.py`
- `src/load_new_kbtopics/__init__.py`

## Required Configuration

### 1. Azure OpenAI Setup

You need to:
1. Create an Azure OpenAI resource in Azure Portal
2. Deploy the following models:
   - **Chat Model**: GPT-4o (deployment name: `gpt-4o`)
   - **Embedding Model**: text-embedding-3-large (deployment name: `text-embedding-3-large`)

### 2. Environment Variables

Update your `.env` file with:
- `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint URL
- `AZURE_OPENAI_API_VERSION`: API version (default: `2024-02-01`)
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`: Embedding model deployment name
- `AZURE_OPENAI_CHAT_DEPLOYMENT`: Chat model deployment name
- `EMBEDDING_MODEL_NAME`: The embedding model name (configurable, default: `text-embedding-3-large`)
- `CHAT_MODEL_NAME`: The chat model name (configurable, default: `gpt-4o`)

### 3. Removed Environment Variables

The following environment variables are no longer needed:
- `ANTHROPIC_API_KEY`
- `VOYAGE_API_KEY`
- `LOGFIRE_TOKEN`

## Benefits of Migration

1. **Unified Provider**: All AI services now use Azure OpenAI
2. **Cost Optimization**: Single provider billing and management
3. **Simplified Configuration**: Fewer API keys and services to manage
4. **Enhanced Security**: Azure's enterprise-grade security features
5. **Better Integration**: Native Azure ecosystem integration

## Post-Migration Testing

After configuration, test the following functionality:
1. Message routing and intent detection
2. Knowledge base Q&A functionality
3. Group chat summarization
4. Embedding generation for new topics
5. Spam detection functionality

## Troubleshooting

If you encounter issues:
1. Verify Azure OpenAI resource is properly configured
2. Check that both GPT-4o and text-embedding-3-large models are deployed
3. Ensure environment variables are correctly set
4. Confirm API keys have proper permissions
5. Check Azure OpenAI quota and rate limits
