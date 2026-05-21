# 안전망: 0003가 max_length=512로 만들어진 환경에서 컬럼을 255로 축소.
# 이미 255로 적용된 환경(이번 deploy 같은 신규 인스턴스)에선 사실상 no-op.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0005_alter_notification_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='devicetoken',
            name='token',
            field=models.CharField(max_length=255, unique=True, verbose_name='FCM 토큰'),
        ),
    ]
