from .provider import Provider
from .provider_type import ProviderType
from ..heynow.provider import HeynowProvider


class ProviderDispatcher:
    """
    Dispatcher class for selecting and instantiating provider implementations based on the provider name.

    Attributes:
        provider_name (str): The name of the provider to dispatch.
        env: The environment/context object required by provider implementations.

    Methods:
        get_provider() -> Provider:
            Returns an instance of the appropriate Provider subclass based on the provider_name.
            Raises:
                ValueError: If the provider_name is not supported.
    """

    def __init__(self, provider_name: str, env):
        self.provider_name = provider_name
        self.env = env

    def get_provider(self) -> Provider:
        """
        Returns an instance of the appropriate Provider subclass based on the provider_name attribute.

        If the provider_name matches the value for HeyNow, returns a HeynowProvider instance.
        Raises:
            ValueError: If the provider_name is not supported.

        Returns:
            Provider: An instance of the selected provider.
        """

        if self.provider_name == ProviderType.HEYNOW.value:
            return HeynowProvider(self.env)
        else:
            raise ValueError(f"Unsupported provider: {self.provider_name}")
