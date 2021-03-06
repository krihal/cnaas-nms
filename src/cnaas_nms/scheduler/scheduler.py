import inspect
import datetime
from pytz import utc
from typing import Optional, Union
from types import FunctionType

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

import cnaas_nms.db.session
from cnaas_nms.scheduler.jobtracker import Jobtracker, JobStatus
from cnaas_nms.tools.log import get_logger

logger = get_logger()


class SingletonType(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonType, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Scheduler(object, metaclass=SingletonType):
    def __init__(self):
        if self.is_api_caller(caller = inspect.currentframe()):
            sqlalchemy_url = cnaas_nms.db.session.get_sqlalchemy_conn_str()
            jobstores = {'default': SQLAlchemyJobStore(url=sqlalchemy_url)}
        else:
            jobstores = {'default': MemoryJobStore()} 
        self._scheduler = BackgroundScheduler(
            executors = {'default': ThreadPoolExecutor(10)},
            jobstores = jobstores,
            job_defaults = {},
            timezone = utc
        )

    def get_scheduler(self):
        return self._scheduler

    def is_api_caller(self, caller):
        """Check if API main run was the caller."""
        frameinfo = inspect.getframeinfo(caller.f_back.f_back)
        filename = '/'.join(frameinfo.filename.split('/')[-2:])
        function = frameinfo.function
        logger.info("Scheduler started from filename {} function {}".format(
            filename, function))
        if filename == 'cnaas_nms/run.py' and function == 'main':
            return True
        else:
            return False

    def start(self):
        return self._scheduler.start()

    def shutdown(self):
        return self._scheduler.shutdown()

    def add_job(self, func, **kwargs):
        return self._scheduler.add_job(func, **kwargs)

    def add_onetime_job(self, func: Union[str, FunctionType], when: Optional[int]=None, **kwargs):
        """Schedule a job to run at a later time.

        Args:
            func: The function to call
            when: Optional number of seconds to wait before starting job
            **kwargs: Arguments to pass through to called function
        Returns:
            apscheduler.job.Job
        """
        job = Jobtracker()
        id = job.create({'status': JobStatus.SCHEDULED})
        if when and isinstance(when, int):
            trigger = 'date'
            run_date = datetime.datetime.utcnow() + datetime.timedelta(seconds=when)
        else:
            trigger = None
            run_date = None
        kwargs['job_id'] = id
        return self._scheduler.add_job(
            func, trigger=trigger, kwargs=kwargs, id=id, run_date=run_date)

