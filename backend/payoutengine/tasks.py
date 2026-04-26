from celery import shared_task


@shared_task
def debug_task(x, y):
    return x + y
