from celery import shared_task


@shared_task
def debug_task(x, y):
    return x + y

@shared_task
def process_payout(payout_id):
    pass