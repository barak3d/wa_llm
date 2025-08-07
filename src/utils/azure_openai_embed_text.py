from typing import List
from openai import AsyncAzureOpenAI

async def azure_openai_embed_text(
    embedding_client: AsyncAzureOpenAI, 
    input: List[str],
    model_name: str
) -> List[List[float]]:
    """
    Generate embeddings using Azure OpenAI embedding model.
    
    Args:
        embedding_client: Azure OpenAI async client
        input: List of texts to embed
        model_name: The embedding model name to use
    
    Returns:
        List of embedding vectors
    """
    batch_size = 100  # Azure OpenAI recommended batch size
    embeddings = []
    
    for i in range(0, len(input), batch_size):
        batch = input[i : i + batch_size]
        response = await embedding_client.embeddings.create(
            model=model_name,
            input=batch
        )
        
        batch_embeddings = [embedding.embedding for embedding in response.data]
        embeddings.extend(batch_embeddings)
    
    return embeddings
