import os
import zc.lockfile

from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            l = zc.lockfile.LockFile('.handle_mail_lock')
        except zc.lockfile.LockError:
            return

        try:
            try:
                from cciw.mail.lists import handle_all_mail
                handle_all_mail()
            except:
                from django.core.mail import mail_admins
                import traceback
                import sys
                subject = 'Sending mail error'
                exc_info = sys.exc_info()
                message = '\n'.join(traceback.format_exception(*exc_info))
                mail_admins(subject, message, fail_silently=True)
        finally:
            # Delete the lock
            l.close()
