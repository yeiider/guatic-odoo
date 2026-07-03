from odoo.http import request, Response
from odoo import http
from ..models.provider.provider_type import ProviderType
from ..models.payloads.dispatcher import WebhookDispatcher
from ..models.services.dispatcher import ServiceProviderDispatcher
import logging
import json

_logger = logging.getLogger(__name__)


class ProviderWebhookController(http.Controller):
    """
    Controller for handling incoming webhook requests from chat providers.

    This controller exposes endpoints to receive and process webhook events from various chat providers.
    It validates incoming requests, extracts relevant event data, dispatches processing jobs asynchronously,
    and provides a health check endpoint.

    Routes:
        - /webhook/chat/<string:provider_name> (type="json", POST): Receives webhook events from chat providers.
            * Validates JSON payload and provider.
            * Extracts event data using a dispatcher.
            * Checks authentication and channel validity.
            * Enqueues the event for asynchronous processing.
            * Returns appropriate HTTP status codes and messages.

        - /botpress/webhook/response (type="http", POST): Health check endpoint for webhook integration.
            * Returns a simple JSON response indicating the webhook service is healthy.

    Methods:
        - receive(provider_name: str, **kwargs): Handles incoming webhook events for a given provider.
        - health_check(**kwargs): Returns a health status for the webhook endpoint.


    Attributes:
        None

    Exceptions:
        Handles and logs JSON decoding errors, event extraction errors, unsupported provider types,
        authentication failures, invalid channels, and job enqueueing errors, returning appropriate
        HTTP responses for each case.
    """

    @http.route(
        "/webhook/chat/<string:provider_name>",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def receive(self, provider_name: str, **kwargs):
        """
        Receives and processes incoming webhook requests for a given provider.

        This method handles the following steps:
            1. Parses the raw JSON body from the incoming HTTP request.
            2. Validates and extracts the event payload using the appropriate WebhookDispatcher.
            3. Checks if the payload is processable and if the provider/channel are valid.
            4. Authenticates the provider service.
            5. Enqueues the webhook event for asynchronous processing using Odoo's job queue.
            6. Handles and logs errors at each step, returning appropriate HTTP responses.

        Args:
            provider_name (str): The name of the webhook provider.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: An HTTP response object with JSON content indicating the result of the operation.
                - 202 Accepted if the webhook is successfully enqueued.
                - 400 Bad Request for invalid input or unsupported provider/channel.
                - 401 Unauthorized if authentication fails.
                - 500 Internal Server Error for unexpected errors.
                - 200 OK with "ignored" status if the payload is not processable.
        """

        raw_body = request.httprequest.data
        data = {}

        try:

            data = json.loads(raw_body.decode("utf-8"))

        except UnicodeDecodeError as e:
            _logger.error("Error decoding request body: %s", str(e))
            return Response(
                json.dumps({"status": "error", "message": "Invalid request body"}),
                content_type="application/json",
                status=400,
            )
        except json.JSONDecodeError:
            return Response(
                json.dumps({"status": "error", "message": "Invalid JSON format"}),
                content_type="application/json",
                status=400,
            )


        payload = None
        try:
            dispatcher_webhook = WebhookDispatcher(provider_name, data)
            payload = dispatcher_webhook.extract_event()
        except ValueError as e:
            _logger.error("Error extracting event from webhook: %s", str(e))
            return Response(
                json.dumps({"status": "error", "message": str(e)}),
                content_type="application/json",
                status=400,
            )

        except TypeError as e:
            _logger.error("Type error extracting event from webhook: %s", str(e))
            return Response(
                json.dumps(
                    {"status": "error", "message": "Type error processing webhook"}
                ),
                content_type="application/json",
                status=500,
            )
        if not payload:
            _logger.error("Invalid payload for provider %s", provider_name)
            return Response(
                json.dumps({"status": "error", "message": "Invalid payload"}),
                content_type="application/json",
                status=400,
            )
        if not payload.is_processable:

            return Response(
                json.dumps({"status": "ignored", "message": "Payload not processable"}),
                content_type="application/json",
                status=200,
            )
        provider_type = ProviderType.get_type(provider_name)
        service = None

        try:
            service_provider_dispatcher = ServiceProviderDispatcher(request.env)
            service = service_provider_dispatcher.get_service(provider_type)
        except ValueError as e:
            _logger.error("Unsupported provider type: %s", str(e))
            return Response(
                json.dumps({"status": "error", "message": "Unsupported provider type"}),
                content_type="application/json",
                status=400,
            )
        except Exception as e:
            _logger.error("Error getting provider service: %s", str(e))
            return Response(
                json.dumps(
                    {"status": "error", "message": "Error getting provider service"}
                ),
                content_type="application/json",
                status=500,
            )

        if not service.get_is_valid():
            _logger.error("Authentication failed for provider %s", provider_name)
            return Response(
                json.dumps({"status": "error", "message": "Authentication failed"}),
                content_type="application/json",
                status=401,
            )
        if not service.get_is_valid_channel(payload.channel):
            _logger.error(
                "Invalid channel for provider %s: %s",
                provider_name,
                payload.channel,
            )
            return Response(
                json.dumps({"status": "error", "message": "Invalid channel"}),
                content_type="application/json",
                status=401,
            )
        is_restricted, message = service.check_access_restrictions(payload)

        if is_restricted:
            _logger.warning(
                "Access restricted for provider %s: %s", provider_name, message
            )
            return Response(
                json.dumps({"status": "error", "message": message}),
                content_type="application/json",
                status=403,
            )

        try:
            job = (
                request.env["webhook.processor"]
                .with_delay(
                    priority=5,
                    eta=None,
                    max_retries=3,
                    channel="webhook.processing",
                )
                .process_webhook_event(provider_name, data)
            )

            _logger.info("Webhook enqueued successfully with job UUID: %s", job.uuid)

            return Response(
                json.dumps(
                    {
                        "status": "enqueued",
                        "job_id": job.uuid,
                        "message": "Webhook received and queued for processing",
                    }
                ),
                content_type="application/json",
                status=202,
            )

        except Exception as e:
            _logger.error("Error enqueuing webhook: %s", str(e))
            return Response(
                json.dumps(
                    {
                        "status": "error",
                        "message": "Error enqueuing webhook for processing",
                        "details": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    @http.route(
        "/botpress/webhook/response",
        type="http",
        auth="public",
        csrf=False,
        methods=["POST"],
    )
    def health_check(self, **kwargs):
        """Health check endpoint"""
        return request.make_response(
            json.dumps({"status": "ok", "message": "Webhook is healthy"}),
            headers={"Content-Type": "application/json"},
        )

    def _validate_authentication_by_provider_type(
        self, provider_type: ProviderType, data: any
    ) -> bool:
        """Validar la autenticación del webhook"""

        return True
