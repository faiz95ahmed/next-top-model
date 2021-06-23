from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

class JobStatus(TextChoices):
    PENDING = 'PENDING', _('Pending')
    RUNNING = 'RUNNING', _('Running')
    ENDING  = 'ENDING', _('Ending')
    FINISHED = 'FINISHED', _('Finished')
    PAUSING = 'PAUSING', _('Pausing')