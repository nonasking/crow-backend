class ParseSMSErrorMessages:
    # TextChoices로 두면 str()이 label 대신 키("PARSE_FAILED")를 돌려주므로 문자열 상수로 둔다.
    INVALID_JSON = "Invalid JSON"
    PARSE_FAILED = "메시지 파싱 실패: "
    NOTION_FAILED = "Notion 업로드 실패"
    INVALID_FORMAT = "메시지 형식이 잘못되었습니다"
    UNSUPPORTED_COMPANY = "지원하지 않는 카드사입니다"
