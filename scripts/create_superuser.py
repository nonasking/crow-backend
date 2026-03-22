import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.contrib.auth.models import User

username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

if not username or not password:
    print("DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_PASSWORD 환경변수가 필요합니다.")
    exit(1)

if User.objects.filter(username=username).exists():
    print(f"이미 존재하는 유저: {username}")
else:
    User.objects.create_superuser(username=username, password=password)
    print(f"Superuser 생성 완료: {username}")
