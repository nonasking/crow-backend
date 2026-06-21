# Schema migration: Expense.auto_classified BooleanField 추가.
#
# 결정성 기반 자동분류(배치)가 채운 행을 표시하는 플래그.
# 기존 행은 모두 default=False (전부 수동 분류분)로 채워진다.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("expenses", "0005_normalize_sms_items"),
    ]

    operations = [
        migrations.AddField(
            model_name="expense",
            name="auto_classified",
            field=models.BooleanField(
                default=False,
                help_text="결정성 기반 자동분류 규칙으로 채워진 행이면 True. 수동 분류분은 False.",
                verbose_name="자동분류여부",
            ),
        ),
    ]
