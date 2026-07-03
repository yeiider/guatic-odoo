import time
import logging
from functools import wraps
from psycopg2 import IntegrityError, OperationalError
from psycopg2.errors import InFailedSqlTransaction
from odoo.exceptions import MissingError, ValidationError
from odoo.addons.queue_job.exception import RetryableJobError

_logger = logging.getLogger(__name__)





def retry_on_transient_error(
    max_retries=3, initial_delay=0.1, catch_integrity_error=False
):
    """
    Decorador para reintentar una función en caso de errores transitorios
    (ej. concurrencia, deadlocks, transacciones abortadas, registros no encontrados).

    Args:
        max_retries (int): Número máximo de reintentos.
        initial_delay (float): Retraso inicial en segundos.
        catch_integrity_error (bool): Si es True,
        también reintenta en IntegrityError.
        Útil para casos de race conditions al crear registros.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            self = args[0]
            attempts = 0
            while attempts < max_retries:
                try:
                    return func(*args, **kwargs)
                except (
                    IntegrityError, 
                    OperationalError, 
                    InFailedSqlTransaction,
                    MissingError,
                    ValidationError,
                    RetryableJobError
                ) as e:

                    error_str = str(e).lower()
                    is_transient_error = False

                    # Manejar errores de integridad (duplicados)
                    if (
                        isinstance(e, IntegrityError)
                        and catch_integrity_error
                        and "unique" in error_str
                    ):
                        is_transient_error = True

                    # Manejar errores operacionales (deadlocks, etc.)
                    elif isinstance(e, OperationalError) and any(
                        keyword in error_str
                        for keyword in [
                            "deadlock detected",
                            "could not serialize access",
                            "concurrent update",
                            "connection timeout",
                            "server closed the connection",
                        ]
                    ):
                        is_transient_error = True

                    # Manejar transacciones abortadas
                    elif isinstance(e, InFailedSqlTransaction) and any(
                        keyword in error_str
                        for keyword in [
                            "current transaction is aborted",
                            "commands ignored until end of transaction block",
                            "transaction aborted",
                        ]
                    ):
                        is_transient_error = True

                    # Manejar MissingError (registros no encontrados) - común en race conditions
                    elif isinstance(e, MissingError) and any(
                        keyword in error_str
                        for keyword in [
                            "does not exist",
                            "missing",
                            "not found",
                            "record does not exist",
                        ]
                    ):
                        is_transient_error = True

                    # Manejar ValidationError específicos de concurrencia
                    elif isinstance(e, ValidationError) and any(
                        keyword in error_str
                        for keyword in [
                            "concurrent",
                            "already exists",
                            "state changed",
                            "record was modified",
                        ]
                    ):
                        is_transient_error = True

                    # Manejar nuestra excepción personalizada
                    elif isinstance(e, RetryableJobError):
                        is_transient_error = True

                    # Errores específicos de Odoo relacionados con registros inexistentes
                    elif any(
                        keyword in error_str
                        for keyword in [
                            "record does not exist",
                            "no longer exists",
                            "channel does not exist",
                            "partner does not exist",
                            "recordset is empty",
                            "expected singleton",
                        ]
                    ):
                        is_transient_error = True

                    if is_transient_error and attempts < max_retries - 1:
                        delay = initial_delay * (2**attempts)
                        _logger.warning(
                            "Transient error detected (%s). Retrying %s in %s seconds (attempt %s/%s).",
                            type(e).__name__ + ": " + str(e),
                            func.__name__,
                            delay,
                            attempts + 1,
                            max_retries,
                        )

                        # Hacer rollback y reiniciar cursor si es necesario
                        try:
                            self.env.cr.rollback()
                            # Invalidar cache para asegurar datos frescos en el siguiente intento
                            if hasattr(self.env, 'invalidate_all'):
                                self.env.invalidate_all()
                        except Exception as rollback_error:
                            _logger.warning(
                                "Error during rollback/invalidation: %s. Continuing with retry.",
                                rollback_error,
                            )

                        time.sleep(delay)
                        attempts += 1
                        continue  # Reintentar
                    else:
                        _logger.error(
                            "Operation %s failed after %s attempts due to non-retriable error or max retries reached: %s",
                            func.__name__,
                            attempts + 1,
                            type(e).__name__ + ": " + str(e),
                        )
                        raise

                except Exception as e:
                    # Para cualquier otra excepción no manejada específicamente
                    error_str = str(e).lower()
                    
                    # Verificar si parece ser un error transitorio por el mensaje
                    if any(
                        keyword in error_str
                        for keyword in [
                            "timeout",
                            "connection",
                            "temporary",
                            "busy",
                            "locked",
                            "retry",
                        ]
                    ) and attempts < max_retries - 1:
                        delay = initial_delay * (2**attempts)
                        _logger.warning(
                            "Possible transient error detected (%s). Retrying %s in %s seconds (attempt %s/%s).",
                            type(e).__name__ + ": " + str(e),
                            func.__name__,
                            delay,
                            attempts + 1,
                            max_retries,
                        )
                        
                        try:
                            self.env.cr.rollback()
                            if hasattr(self.env, 'invalidate_all'):
                                self.env.invalidate_all()
                        except Exception as rollback_error:
                            _logger.warning(
                                "Error during rollback/invalidation: %s. Continuing with retry.",
                                rollback_error,
                            )
                        
                        time.sleep(delay)
                        attempts += 1
                        continue
                    else:
                        # Si no parece transitorio o se agotaron los intentos, re-lanzar
                        raise

            raise Exception(
                f"Failed to execute {func.__name__} after {max_retries} attempts."
            )

        return wrapper

    return decorator