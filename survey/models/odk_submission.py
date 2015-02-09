import os
import mimetypes
from django.conf import settings
from tempfile import NamedTemporaryFile
from hashlib import md5
from django.core.files.storage import get_storage_class
from django.db import models
from survey.models.base import BaseModel
from survey.models.investigator import Investigator
from survey.models.surveys import Survey
from survey.models.households import HouseholdMember


class ODKSubmission(BaseModel):
    investigator = models.ForeignKey(Investigator, related_name="odk_submissions")
    survey = models.ForeignKey(Survey, related_name="odk_submissions")
    household_member = models.ForeignKey(HouseholdMember, related_name="odk_submissions")
    form_id = models.CharField(max_length=256)
    instance_id = models.CharField(max_length=256)
    xml = models.TextField()

    class Meta:
        app_label = 'survey'

    def save_attachments(self, media_files):
        for f in media_files:
            content_type = f.content_type if hasattr(f, 'content_type') else ''
            attach, created = Attachment.objects.get_or_create(submission=self,
                                             media_file=f,
                                             mimetype=content_type)

def upload_to(attachment, filename):
    return os.path.join(
        settings.SUBMISSION_UPLOAD_BASE,
        str(attachment.submission.pk),
        'attachments')


class Attachment(BaseModel):
    submission = models.ForeignKey(ODKSubmission, related_name="attachments")
    media_file = models.FileField(upload_to=upload_to)
    mimetype = models.CharField(
        max_length=50, null=False, blank=True, default='')

    class Meta:
        app_label = 'survey'

    def save(self, *args, **kwargs):
        if self.media_file and self.mimetype == '':
            # guess mimetype
            mimetype, encoding = mimetypes.guess_type(self.media_file.name)
            if mimetype:
                self.mimetype = mimetype
        super(Attachment, self).save(*args, **kwargs)

