# Variants become a property of the Book, with each Engine declaring the ones
# it accepts, and a Protocol being declared per Engine binary.
#
# The Books seeded by 0015 include a number of Fischer Random books. Until now
# the Client recognised those by inspecting the Book's name. Record that
# decision in the database instead, so the Server can verify a Workload before
# it is created. Any Book which does not look like FRC stays 'standard'.

from django.db import migrations, models

# Case-insensitive substrings that mark one of the seeded Books as FRC
FRC_MARKERS = ('frc', '960', 'dfrc', 'fischer')

def flag_frc_books(apps, schema_editor):

    Book = apps.get_model('OpenBench', 'Book')

    for book in Book.objects.all():

        if any(marker in book.name.lower() for marker in FRC_MARKERS):
            Book.objects.filter(pk=book.pk).update(variant='fischerandom')

class Migration(migrations.Migration):

    dependencies = [
        ('OpenBench', '0017_network_ob_compressed'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='variant',
            field=models.CharField(default='standard', max_length=16),
        ),
        migrations.AddField(
            model_name='engineconfig',
            name='variants',
            field=models.CharField(default='standard fischerandom', max_length=64),
        ),
        migrations.AddField(
            model_name='engineconfig',
            name='protocol',
            field=models.CharField(default='uci', max_length=16),
        ),
        migrations.RunPython(flag_frc_books, migrations.RunPython.noop),
    ]
