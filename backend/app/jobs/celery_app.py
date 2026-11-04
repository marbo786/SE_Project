from celery import Celery
from ..core.config import get_settings

settings = get_settings()
celery = Celery('srs_analysis', broker=settings.REDIS_URL)
celery.conf.update(task_serializer='json', accept_content=['json'], task_ignore_result=True,
    task_acks_late=True, task_reject_on_worker_lost=True, worker_prefetch_multiplier=1,
    task_time_limit=settings.JOB_TIMEOUT_SECONDS + 30, task_soft_time_limit=settings.JOB_TIMEOUT_SECONDS,
    broker_connection_retry_on_startup=True, broker_connection_timeout=3,
    broker_transport_options={'visibility_timeout': settings.JOB_TIMEOUT_SECONDS + 60},
    task_publish_retry=False)


@celery.task(name='srs.analyze')
def analyze(run_id):
    from .worker import execute
    execute(run_id)
