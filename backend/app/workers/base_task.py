import asyncio
from celery import Task

class AsyncCeleryTask(Task):
    """Base class for running async code in Celery."""

    def __call__(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.run(*args, **kwargs))
