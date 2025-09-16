import os
from django.conf import settings
from django.contrib.auth import get_user_model

def run():
    User = get_user_model()
    username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
    email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "admin123")

    if not User.objects.filter(username=username).exists():
        print(f"Creating superuser {username}...")
        User.objects.create_superuser(username=username, email=email, password=password)
        print("Superuser created.")
    else:
        print(f"Superuser {username} already exists. Skipping.")