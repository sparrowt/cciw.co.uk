from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0005_auto_20150605_1738'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='full_maiden_name',
            field=models.CharField(max_length=100, help_text='Name before getting married.', blank=True, verbose_name='full maiden name'),
        ),
        migrations.AlterField(
            model_name='crbapplication',
            name='officer',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='crb_applications', on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='crbapplication',
            name='requested_by',
            field=models.CharField(max_length=20, default='unknown', choices=[('CCIW', 'CCiW'), ('other', 'Other organisation'), ('unknown', 'Unknown')]),
        ),
    ]
