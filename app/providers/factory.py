from .mock import MockProvider
from .self_hosted import SelfHostedProvider
from ..config import settings

def get_provider():
    # Backward compatibility: older deployments may still have PROVIDER=huggingface.
    # RedPits no longer supports hosted HF inference; route legacy values to the local engine.
    if settings.provider == "mock":
        return MockProvider()
    return SelfHostedProvider()
