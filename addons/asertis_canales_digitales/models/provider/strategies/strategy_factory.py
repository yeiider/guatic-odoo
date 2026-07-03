from typing import Dict, Type
from .base_strategy import BaseFileStrategy, MultipleFilesStrategy
from .files_first_strategy import FilesFirstStrategy
from .interleaved_strategy import InterleavedStrategy
from .single_request_strategy import SingleRequestStrategy
from .text_first_strategy import TextFirstStrategy
from .files_with_text_strategy import FilesWithTextStrategy

import logging

_logger = logging.getLogger(__name__)


class FileStrategyFactory:
    """Factory para crear estrategias de manejo de archivos"""

    _strategies: Dict[MultipleFilesStrategy, Type[BaseFileStrategy]] = {
        MultipleFilesStrategy.SINGLE_REQUEST: SingleRequestStrategy,
        MultipleFilesStrategy.TEXT_FIRST: TextFirstStrategy,
        MultipleFilesStrategy.FILES_FIRST: FilesFirstStrategy,
        MultipleFilesStrategy.FILES_WITH_TEXT: FilesWithTextStrategy,
        MultipleFilesStrategy.INTERLEAVED: InterleavedStrategy,
    }

    @classmethod
    def create_strategy(
        cls,
        strategy_type: MultipleFilesStrategy,
        sender_callback,
        provider,
        webhook_url,
        headers,
        provider_name,
        provider_metadata: Dict[str, str] = None,
    ) -> BaseFileStrategy:
        """Crear instancia de estrategia"""

        if strategy_type not in cls._strategies:
            _logger.warning("Unknown strategy %s, using TEXT_FIRST", strategy_type)
            strategy_type = MultipleFilesStrategy.TEXT_FIRST

        strategy_class = cls._strategies[strategy_type]
        return strategy_class(
            sender_callback,
            provider,
            webhook_url,
            headers,
            provider_name,
            provider_metadata,
        )

    @classmethod
    def register_strategy(
        cls, strategy_type: MultipleFilesStrategy, strategy_class: type
    ):
        """Registrar nueva estrategia (para extensibilidad)"""
        if not issubclass(strategy_class, BaseFileStrategy):
            raise ValueError("Strategy class must inherit from BaseFileStrategy")

        cls._strategies[strategy_type] = strategy_class
        _logger.info("Registered new strategy: %s", strategy_type.value)
