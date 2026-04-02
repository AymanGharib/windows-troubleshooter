"""
Bootstrap the incident agent in RabbitMQ consumer mode.

Consumes correlated incidents from RabbitMQ and publishes progress/results to
the result queue.
"""

import logging
import sys
import os

# Add parent directory to path for shared modules (5 levels up to workspace root)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

from app.config import AppConfig
from app.rabbitmq.consumer import start_consumer
from app.common.utils import get_logger

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = get_logger(__name__)


def main():
    """Main entry point - starts RabbitMQ consumer."""
    logger.info("=" * 60)
    logger.info("Starting Incident Agent RabbitMQ Consumer")
    logger.info("=" * 60)

    try:
        rabbitmq_config = AppConfig.get_rabbitmq_config()
        logger.info(f"RabbitMQ URL: {rabbitmq_config.RABBITMQ_URL}")
        logger.info(f"Incident Queue: {rabbitmq_config.RABBITMQ_TASK_QUEUE}")
        logger.info(f"Incident Exchange: {rabbitmq_config.RABBITMQ_EXCHANGE}")
        logger.info(f"Incident Routing Key: {rabbitmq_config.RABBITMQ_ROUTING_KEY}")
        logger.info(f"Result Queue: {rabbitmq_config.RABBITMQ_RESULT_QUEUE}")
    except Exception as e:
        logger.error(f"Failed to get RabbitMQ config: {e}")
        sys.exit(1)

    try:
        platform_config = AppConfig.get_platform_config()
        logger.info(f"AI Platform: {platform_config.AIPLATFORM_BASE_URL}")
    except Exception as e:
        logger.error(f"Failed to get platform config: {e}")
        sys.exit(1)

    try:
        model_config = AppConfig.get_model_config()
        logger.info(f"Model: {model_config.MODEL_NAME}")
    except Exception as e:
        logger.error(f"Failed to get model config: {e}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Starting consumer...")
    logger.info("=" * 60)

    # Start the consumer
    try:
        start_consumer()
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
