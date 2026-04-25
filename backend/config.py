import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file (repo root)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

@dataclass
class Config:
    """Configuration settings for the RAG system"""
    # Anthropic API settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    
    # Embedding model settings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # Document processing settings
    CHUNK_SIZE: int = 800       # Size of text chunks for vector storage
    CHUNK_OVERLAP: int = 100     # Characters to overlap between chunks
    MAX_RESULTS: int = 5         # Maximum search results to return
    MAX_HISTORY: int = 2         # Number of conversation messages to remember
    
    # Database paths
    CHROMA_PATH: str = "./chroma_db"  # ChromaDB storage location

config = Config()

_PLACEHOLDER = "your-api-key-here"
if not config.ANTHROPIC_API_KEY or config.ANTHROPIC_API_KEY == _PLACEHOLDER:
    raise ValueError(
        "ANTHROPIC_API_KEY is not set. "
        "Add your real Anthropic API key to the .env file at the repo root: "
        "ANTHROPIC_API_KEY=sk-ant-..."
    )


