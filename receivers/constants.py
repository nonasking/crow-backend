class ParseSMSErrorMessages:
    # TextChoices로 두면 str()이 label 대신 키("PARSE_FAILED")를 돌려주므로 문자열 상수로 둔다.
    INVALID_JSON = "Invalid JSON"
    PARSE_FAILED = "메시지 파싱 실패: "
    NOTION_FAILED = "Notion 업로드 실패"
    EXCHANGE_RATE_FAILED = "환율 조회 실패"
    INVALID_FORMAT = "메시지 형식이 잘못되었습니다"
    UNSUPPORTED_COMPANY = "지원하지 않는 카드사입니다"
    EMPTY_ITEM = "가맹점명을 찾을 수 없습니다"
    CANCELLATION_IGNORED = "승인취소 문자는 기록하지 않습니다"
