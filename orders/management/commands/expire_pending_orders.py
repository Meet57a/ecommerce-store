from django.core.management.base import BaseCommand

from orders.services import expire_pending_orders


class Command(BaseCommand):
    help = "Cancel pending orders older than the payment window and release stock."

    def handle(self, *args, **options):
        expired = expire_pending_orders()
        self.stdout.write(self.style.SUCCESS(f"Expired {len(expired)} pending order(s)."))
