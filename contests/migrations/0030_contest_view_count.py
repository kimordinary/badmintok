from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contests", "0029_alter_contest_options_contest_pdf_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="contest",
            name="view_count",
            field=models.PositiveIntegerField(default=0, verbose_name="조회수"),
        ),
    ]
