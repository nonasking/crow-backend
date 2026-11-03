from django.apps import AppConfig


class ReceiversConfig(AppConfig):
    name = "receivers"

    def ready(self):
        from receivers import checks  # noqa: F401  system check 등록
