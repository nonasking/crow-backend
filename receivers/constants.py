from django.db import models


class ParseSMSErrorMessages(models.TextChoices):
    INVALID_JSON = "INVALID_JSON", "Invalid JSON"
    PARSE_FAILED = "PARSE_FAILED", "메시지 파싱 실패: "
    NOTION_FAILED = "NOTION_FAILED", "Notion 업로드 실패"
    INVALID_FORMAT = "INVALID_FORMAT", "메시지 형식이 잘못되었습니다"
    UNSUPPORTED_COMPANY = "UNSUPPORTED_COMPANY", "지원하지 않는 카드사입니다"
