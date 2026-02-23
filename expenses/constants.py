from django.db import models


class ExpenseCategoryEnum(models.TextChoices):
    BEAUTY = "BEAUTY", "미용"
    HOUSEHOLD = "HOUSEHOLD", "생활용품"
    PHONE_BILL = "PHONE_BILL", "통신비"
    ALLOWANCE = "ALLOWANCE", "자유금"
    FOOD = "FOOD", "식대"
    MEDICAL = "MEDICAL", "병원비"
    TRANSPORT = "TRANSPORT", "교통비"
    HOUSING = "HOUSING", "주거"
    CLOTHING = "CLOTHING", "의복"
    EVENT = "EVENT", "이벤트"
    EXERCISE = "EXERCISE", "운동"
    UNKNOWN = "UNKNOWN", "미상"
    SUBSCRIPTION = "SUBSCRIPTION", "청약"
    SELF_DEV = "SELF_DEV", "자기개발"
    CELEBRATION = "CELEBRATION", "경조사"
    ETC = "ETC", "기타"
    UNSETTLED = "UNSETTLED", "미정산"


class ExpenseSubCategoryEnum(models.TextChoices):
    # 미용
    BEAUTY = "BEAUTY", "미용"
    # 생활용품
    HOUSEHOLD = "HOUSEHOLD", "생활용품"
    # 통신비
    PHONE_BILL = "PHONE_BILL", "통신비"
    # 자유금
    ALLOWANCE_MS = "ALLOWANCE_MS", "민성자유금"
    ALLOWANCE_MK = "ALLOWANCE_MK", "민근자유금"
    # 식대
    ALCOHOL = "ALCOHOL", "주류"
    BEVERAGE = "BEVERAGE", "음료"
    DELIVERY = "DELIVERY", "배달/포장"
    DINING_OUT = "DINING_OUT", "외식"
    COOKING = "COOKING", "요리"
    COMPANY_MEAL = "COMPANY_MEAL", "회사식대"
    # 병원비
    HOSPITAL_ETC = "HOSPITAL_ETC", "기타병원비"
    REGULAR_CHECKUP = "REGULAR_CHECKUP", "정기진료"
    # 교통비
    TRANSPORT = "TRANSPORT", "교통비"
    # 주거
    ELECTRICITY = "ELECTRICITY", "전기요금"
    WATER = "WATER", "수도요금"
    GAS = "GAS", "가스요금"
    MAINTENANCE = "MAINTENANCE", "관리비"
    LEASE_INTEREST = "LEASE_INTEREST", "전세이자"
    INTERNET = "INTERNET", "인터넷요금"
    # 의복
    CLOTHING_BUY = "CLOTHING_BUY", "의복구입"
    CLOTHING_CARE = "CLOTHING_CARE", "의복관리"
    # 이벤트
    VACATION = "VACATION", "휴가"
    LEISURE = "LEISURE", "놀이"
    PARENTS = "PARENTS", "친정"
    # 운동
    EXERCISE_GOODS = "EXERCISE_GOODS", "운동용품"
    EXERCISE_FEE = "EXERCISE_FEE", "운동이용료"
    # 미상
    UNKNOWN = "UNKNOWN", "미상"
    # 청약
    SUBSCRIPTION = "SUBSCRIPTION", "청약"
    # 자기개발
    LEARNING = "LEARNING", "학습"
    # 경조사
    CELEBRATION = "CELEBRATION", "경조사"
    # 기타
    INSURANCE = "INSURANCE", "보험료"
    ETC = "ETC", "기타"
    # 미정산
    UNSETTLED = "UNSETTLED", "미정산"

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
    SHINHAN = "SHINHAN", "신한Big카드"
    WOORI = "WOORI", "우리은행통장"
    CASH = "CASH", "현금"
