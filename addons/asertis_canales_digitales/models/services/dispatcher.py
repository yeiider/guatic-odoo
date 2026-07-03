from ..heynow.service import HeyNowProviderService
from .provider_service import ProviderService

from ..provider.provider_type import ProviderType


class ServiceProviderDispatcher:
    """
    Dispatcher principal para manejar múltiples proveedores.
    Simplificado porque ya no necesita manejar configuraciones externas.
    """

    def __init__(self, env):
        self.env = env

    def get_service(self, provider_type: ProviderType) -> ProviderService:
        """
        Obtener una instancia del proveedor especificado.
        Si no existe, crear una nueva instancia.

        :param provider_type: Tipo de proveedor a obtener
        :return: Instancia del proveedor
        """
        if provider_type == ProviderType.HEYNOW:
            return HeyNowProviderService(self.env, provider_type)
        raise ValueError(f"Proveedor {provider_type.value} no está soportado")
