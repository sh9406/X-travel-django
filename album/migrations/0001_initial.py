# Generated by Django 4.0.4 on 2022-06-10 02:05

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Photo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('photo', models.ImageField(blank=True, null=True, upload_to='pic/')),
                ('thumbnail', models.ImageField(blank=True, null=True, upload_to='pic/')),
                ('author', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='photo_author', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PhotoTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tags', models.CharField(blank=True, default='', max_length=100, null=True)),
                ('create_date', models.DateTimeField(blank=True, null=True)),
                ('latitude', models.CharField(blank=True, default='', max_length=100, null=True)),
                ('longitude', models.CharField(blank=True, default='', max_length=100, null=True)),
                ('starScore', models.CharField(blank=True, default='', max_length=100, null=True)),
                ('review', models.CharField(blank=True, default='', max_length=100, null=True)),
                ('imgurl', models.ImageField(blank=True, null=True, upload_to='')),
                ('photo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='photo_id', to='album.photo')),
            ],
        ),
        migrations.CreateModel(
            name='AnalysisResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('location', models.CharField(blank=True, default='', max_length=100)),
                ('field3', models.CharField(blank=True, default='', max_length=100)),
                ('photo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='album.phototag')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_id', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
