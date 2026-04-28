"""
PCB Builder - Celery Configuration
Distributed task queue for long-running PCB generation jobs.
"""

import os
from celery import Celery
from celery.signals import setup_logging

from shared.config import get_settings

settings = get_settings()

REDIS_URL = settings.redis_url

celery_app = Celery(
    "pcb_builder",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "services.ai_service.tasks",
        "services.eda_service.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # Soft limit 55 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    result_expires=86400,  # Results expire after 24h
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": 43200,  # 12 hours
    },
    # Task routing
    task_routes={
        "services.ai_service.tasks.*": {"queue": "ai"},
        "services.eda_service.tasks.*": {"queue": "eda"},
    },
    # Result backend
    result_backend=REDIS_URL,
    result_extended=True,
)


@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Use structlog for Celery workers too."""
    from shared.logging_config import configure_logging
    configure_logging()
