"""
Observability setup for mcp-server.

Call configure_logging() and configure_sentry() once at startup (in lifespan).
Prometheus metrics are wired by attaching the instrumentator to the FastAPI app.

Environment variables:
  LOG_FORMAT       "json" (default in prod) | "console" (default in dev)
  SENTRY_DSN       Sentry DSN; Sentry is skipped if absent
"""
import logging
import os

import structlog


def configure_logging() -> None:
    """Set up structlog with JSON or colored-console output."""
    log_format = os.getenv("LOG_FORMAT", "json")

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if log_format == "console":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)


def configure_sentry() -> None:
    """Init Sentry if SENTRY_DSN is present."""
    dsn = os.getenv("SENTRY_DSN", "")
    if not dsn:
        return
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=dsn, traces_sample_rate=0.1)
    except ImportError:
        pass


def attach_prometheus(app) -> None:
    """Attach prometheus-fastapi-instrumentator and expose /metrics."""
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            excluded_handlers=["/metrics", "/health"],
        ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    except ImportError:
        pass
