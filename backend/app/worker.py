import logging
import time

from app.core.bootstrap import bootstrap_app
from app.core.config import settings
from app.services.jobs import claim_next_job, process_job

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("regis-worker")


def main() -> None:
    bootstrap_app()
    logger.info("REGIS worker iniciado")
    while True:
        job = claim_next_job()
        if not job:
            time.sleep(settings.worker_poll_seconds)
            continue
        logger.info("Procesando job %s", job.id)
        processed = process_job(job)
        logger.info("Job %s termino con estado %s", processed.id, processed.status)


if __name__ == "__main__":
    main()
