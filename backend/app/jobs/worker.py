"""Worker entry points share the database lease protocol across transports."""
import asyncio
import logging
import time
from ..core.database import SessionLocal
from ..models import user, project, artifact, finding, traceability, score, session, llm_log, history
from ..models.history import AnalysisRun, OutboxEvent
from ..services.jobs import reconcile
from ..pipeline.analyzer import run_analysis_pipeline


def execute(run_id):
    with SessionLocal() as db:
        run = db.get(AnalysisRun, run_id)
        project_id = run.project_id if run else None
    if project_id is not None:
        from ..core.config import get_settings
        async def bounded():
            await asyncio.wait_for(run_analysis_pipeline(project_id, run_id=run_id), timeout=get_settings().JOB_TIMEOUT_SECONDS)
        asyncio.run(bounded())


def main():
    from ..core.config import get_settings
    while True:
        try:
            with SessionLocal() as db:
                reconcile(db)
                row = db.query(AnalysisRun.id).join(OutboxEvent, OutboxEvent.run_id == AnalysisRun.id).filter(
                    AnalysisRun.status == 'queued', AnalysisRun.cancel_requested.is_(False)).order_by(AnalysisRun.created_at).first()
            if row:
                execute(row[0])
            else:
                time.sleep(get_settings().JOB_POLL_SECONDS)
        except KeyboardInterrupt:
            break
        except Exception as error:
            logging.getLogger(__name__).warning('Local worker iteration failed (%s)', type(error).__name__)
            time.sleep(2)


if __name__ == '__main__':
    main()
