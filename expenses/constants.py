from django.db import models


class ExpenseCategoryEnum(models.TextChoices):
    BEAUTY = "beauty", "미용"
    HOUSEHOLD = "household", "생활용품"
    PHONE_BILL = "phone_bill", "통신비"
    ALLOWANCE = "allowance", "자유금"
    FOOD = "food", "식대"
    MEDICAL = "medical", "병원비"
    TRANSPORT = "transport", "교통비"
    HOUSING = "housing", "주거"
    CLOTHING = "clothing", "의복"
    EVENT = "event", "이벤트"
    EXERCISE = "exercise", "운동"
    UNKNOWN = "unknown", "미상"
    SUBSCRIPTION = "subscription", "청약"
    SELF_DEV = "self_dev", "자기개발"
    CELEBRATION = "celebration", "경조사"
    ETC = "etc", "기타"
    UNSETTLED = "unsettled", "미정산"


class ExpenseSubCategoryEnum(models.TextChoices):
    # 미용
    BEAUTY = "beauty", "미용"
    # 생활용품
    HOUSEHOLD = "household", "생활용품"
    # 통신비
    PHONE_BILL = "phone_bill", "통신비"
    # 자유금
    ALLOWANCE_MS = "allowance_ms", "민성자유금"
    ALLOWANCE_MK = "allowance_mk", "민근자유금"
    # 식대
    ALCOHOL = "alcohol", "주류"
    BEVERAGE = "beverage", "음료"
    DELIVERY = "delivery", "배달/포장"
    DINING_OUT = "dining_out", "외식"
    COOKING = "cooking", "요리"
    COMPANY_MEAL = "company_meal", "회사식대"
    # 병원비
    HOSPITAL_ETC = "hospital_etc", "기타병원비"
    REGULAR_CHECKUP = "regular_checkup", "정기진료"
    # 교통비
    TRANSPORT = "transport", "교통비"
    # 주거
    ELECTRICITY = "electricity", "전기요금"
    WATER = "water", "수도요금"
    GAS = "gas", "가스요금"
    MAINTENANCE = "maintenance", "관리비"
    LEASE_INTEREST = "lease_interest", "전세이자"
    INTERNET = "internet", "인터넷요금"
    # 의복
    CLOTHING_BUY = "clothing_buy", "의복구입"
    CLOTHING_CARE = "clothing_care", "의복관리"
    # 이벤트
    VACATION = "vacation", "휴가"
    LEISURE = "leisure", "놀이"
    PARENTS = "parents", "친정"
    # 운동
    EXERCISE_GOODS = "exercise_goods", "운동용품"
    EXERCISE_FEE = "exercise_fee", "운동이용료"
    # 미상
    UNKNOWN = "unknown", "미상"
    # 청약
    SUBSCRIPTION = "subscription", "청약"
    # 자기개발
    LEARNING = "learning", "학습"
    # 경조사
    CELEBRATION = "celebration", "경조사"
    # 기타
    INSURANCE = "insurance", "보험료"
    ETC = "etc", "기타"
    # 미정산
    UNSETTLED = "unsettled", "미정산"


CATEGORY_SUBCATEGORY_MAP: dict[str, list[str]] = {
    ExpenseCategoryEnum.BEAUTY: [
        ExpenseSubCategoryEnum.BEAUTY,
    ],
    ExpenseCategoryEnum.HOUSEHOLD: [
        ExpenseSubCategoryEnum.HOUSEHOLD,
    ],
    ExpenseCategoryEnum.PHONE_BILL: [
        ExpenseSubCategoryEnum.PHONE_BILL,
    ],
    ExpenseCategoryEnum.ALLOWANCE: [
        ExpenseSubCategoryEnum.ALLOWANCE_MS,
        ExpenseSubCategoryEnum.ALLOWANCE_MK,
    ],
    ExpenseCategoryEnum.FOOD: [
        ExpenseSubCategoryEnum.ALCOHOL,
        ExpenseSubCategoryEnum.BEVERAGE,
        ExpenseSubCategoryEnum.DELIVERY,
        ExpenseSubCategoryEnum.DINING_OUT,
        ExpenseSubCategoryEnum.COOKING,
        ExpenseSubCategoryEnum.COMPANY_MEAL,
    ],
    ExpenseCategoryEnum.MEDICAL: [
        ExpenseSubCategoryEnum.HOSPITAL_ETC,
        ExpenseSubCategoryEnum.REGULAR_CHECKUP,
    ],
    ExpenseCategoryEnum.TRANSPORT: [
        ExpenseSubCategoryEnum.TRANSPORT,
    ],
    ExpenseCategoryEnum.HOUSING: [
        ExpenseSubCategoryEnum.ELECTRICITY,
        ExpenseSubCategoryEnum.WATER,
        ExpenseSubCategoryEnum.GAS,
        ExpenseSubCategoryEnum.MAINTENANCE,
        ExpenseSubCategoryEnum.LEASE_INTEREST,
        ExpenseSubCategoryEnum.INTERNET,
    ],
    ExpenseCategoryEnum.CLOTHING: [
        ExpenseSubCategoryEnum.CLOTHING_BUY,
        ExpenseSubCategoryEnum.CLOTHING_CARE,
    ],
    ExpenseCategoryEnum.EVENT: [
        ExpenseSubCategoryEnum.VACATION,
        ExpenseSubCategoryEnum.LEISURE,
        ExpenseSubCategoryEnum.PARENTS,
    ],
    ExpenseCategoryEnum.EXERCISE: [
        ExpenseSubCategoryEnum.EXERCISE_GOODS,
        ExpenseSubCategoryEnum.EXERCISE_FEE,
    ],
    ExpenseCategoryEnum.UNKNOWN: [
        ExpenseSubCategoryEnum.UNKNOWN,
    ],
    ExpenseCategoryEnum.SUBSCRIPTION: [
        ExpenseSubCategoryEnum.SUBSCRIPTION,
    ],
    ExpenseCategoryEnum.SELF_DEV: [
        ExpenseSubCategoryEnum.LEARNING,
    ],
    ExpenseCategoryEnum.CELEBRATION: [
        ExpenseSubCategoryEnum.CELEBRATION,
    ],
    ExpenseCategoryEnum.ETC: [
        ExpenseSubCategoryEnum.INSURANCE,
        ExpenseSubCategoryEnum.ETC,
    ],
    ExpenseCategoryEnum.UNSETTLED: [
        ExpenseSubCategoryEnum.UNSETTLED,
    ],
}


class ExpensePaymentMethodEnum(models.TextChoices):
    SHINHAN = "shinhan", "신한Big카드"
    WOORI = "woori", "우리은행통장"
    CASH = "cash", "현금"
