from django.db import migrations


def set_existing_approval(apps, schema_editor):
    # 기존 번개는 그동안 apply가 항상 pending으로 동작(사실상 승인제)했으므로,
    # 자동승인 회귀를 막기 위해 기존 데이터를 승인제(True)로 명시한다.
    BandSchedule = apps.get_model("band", "BandSchedule")
    BandSchedule.objects.filter(requires_approval=False).update(requires_approval=True)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("band", "0035_bandschedule_gender_quota_and_more"),
    ]

    operations = [
        migrations.RunPython(set_existing_approval, noop),
    ]
