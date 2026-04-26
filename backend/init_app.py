import os
from django.contrib.auth import get_user_model
from payoutengine.seed import run as seed_run


def create_superuser():
    User = get_user_model()

    username = "admin"
    password = "admin"

    if not User.objects.filter(username=username).exists():
        print("Creating superuser...")
        User.objects.create_superuser(username=username, password=password)
    else:
        print("Superuser already exists")


def run_seed():
    print("Running seed...")
    seed_run()


def run():
    create_superuser()
    run_seed()
