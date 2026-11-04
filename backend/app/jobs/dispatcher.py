"""Run beside Celery: reconcile expired work and retry undelivered outbox events."""
import logging
import time
from ..core.database import SessionLocal
from .worker import history  # register all models
from .celery_app import analyze
from ..services.jobs import dispatch, reconcile


def main():
    while True:
        try:
            with SessionLocal() as db:
                reconcile(db)
                dispatch(db, lambda run_id: analyze.apply_async(args=[run_id]))
        except KeyboardInterrupt:
            break
        except Exception as error:
            logging.getLogger(__name__).warning('Dispatcher iteration failed (%s)', type(error).__name__)
        time.sleep(2)


if __name__ == '__main__':
    main()
