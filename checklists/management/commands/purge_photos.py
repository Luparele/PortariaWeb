from django.core.management.base import BaseCommand
from django.utils import timezone
from checklists.models import ChecklistPhoto
from datetime import timedelta

class Command(BaseCommand):
    help = 'Deleta fotos de checklists com mais de 30 dias de criação'

    def handle(self, *args, **options):
        cutoff_date = timezone.now() - timedelta(days=30)
        old_photos = ChecklistPhoto.objects.filter(created_at__lt=cutoff_date)
        
        count = old_photos.count()
        
        for photo in old_photos:
            # The model's delete method already handles physical file removal
            photo.delete()
            
        self.stdout.write(self.style.SUCCESS(f'Sucesso: {count} fotos antigas foram removidas.'))
