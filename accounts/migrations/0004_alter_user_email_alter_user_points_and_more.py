
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_user_email_alter_user_register_no'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=254, unique=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='points',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='user',
            name='register_no',
            field=models.CharField(max_length=10, unique=True),
        ),
    ]
