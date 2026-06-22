# Generated manually for Promotion model

import badmintok.fields
import badmintok.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('badmintok', '0012_visitorlog_app_version_visitorlog_source'),
    ]

    operations = [
        migrations.CreateModel(
            name='Promotion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100, verbose_name='식별용 제목')),
                ('image', badmintok.fields.WebPImageField(upload_to=badmintok.models.promotion_image_upload_to, verbose_name='이미지(2.3:1, 권장 1050×456)')),
                ('link_url', models.CharField(blank=True, max_length=500, verbose_name='링크(app:// 또는 https://)')),
                ('display_order', models.PositiveIntegerField(default=0, help_text='숫자가 낮을수록 먼저 노출됩니다.', verbose_name='정렬 순서')),
                ('is_active', models.BooleanField(default=True, verbose_name='노출')),
                ('start_at', models.DateTimeField(blank=True, help_text='비워두면 즉시 노출', null=True, verbose_name='노출 시작')),
                ('end_at', models.DateTimeField(blank=True, help_text='비워두면 무기한 노출', null=True, verbose_name='노출 종료')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='등록일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
            ],
            options={
                'verbose_name': '프로모션',
                'verbose_name_plural': '프로모션',
                'ordering': ['display_order', '-created_at'],
            },
        ),
    ]
