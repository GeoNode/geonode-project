"""
Django management command to wipe ALL GeoNode resources and ALL non-admin
users — the "undo everything" counterpart to run_full_load_test /
create_real_datasets / create_bulk_users, for resetting an instance between
load-test runs.

DESTRUCTIVE. Deletes every ResourceBase (Datasets, Documents, Maps,
GeoApps, ...) via the ORM, which fires GeoNode's own pre_delete signals —
so a Dataset's real GeoServer layer/store gets removed too, not just the
DB row. Then deletes every User except superusers (kept by default — the
safest "don't lock yourself out" default) and any usernames in --keep-users.

USAGE
-----
    # ALWAYS preview first — this is the default, nothing is deleted:
    python manage.py cleanup_load_test_data

    # actually delete, after reviewing the preview:
    python manage.py cleanup_load_test_data --yes

    # also delete a specific non-superuser account you want to keep otherwise:
    python manage.py cleanup_load_test_data --yes --keep-users alice,bob

Options:
    --yes             actually perform the deletion (default: dry-run preview only)
    --keep-users      CSV of additional usernames to keep, beyond superusers
    --keep-superusers keep superuser accounts (default: true; pass
                       --keep-superusers false to delete them too — NOT
                       recommended, easy way to lock yourself out of the instance)
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from geonode.base.models import ResourceBase

User = get_user_model()


class Command(BaseCommand):
    help = "DESTRUCTIVE: delete all GeoNode resources and all non-admin users. Dry-run by default."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true",
                             help="actually delete — without this, only a preview is printed")
        parser.add_argument("--keep-users", type=str, default="",
                             help="CSV of extra usernames to keep besides superusers")
        parser.add_argument("--keep-superusers", type=lambda v: v.lower() != "false", default=True)

    def handle(self, *args, **opts):
        # AnonymousUser is a real DB row django-guardian uses to hold anonymous
        # permissions, not a load-test artifact — never delete it, regardless
        # of --keep-users/--keep-superusers.
        keep_usernames = {u.strip() for u in opts["keep_users"].split(",") if u.strip()} | {"AnonymousUser"}

        resources = ResourceBase.objects.all()
        resource_count = resources.count()

        user_qs = User.objects.exclude(username__in=keep_usernames)
        if opts["keep_superusers"]:
            user_qs = user_qs.exclude(is_superuser=True)
        users_to_delete = list(user_qs)

        kept_superusers = list(User.objects.filter(is_superuser=True).values_list("username", flat=True)) \
            if opts["keep_superusers"] else []

        self.stdout.write(self.style.WARNING(
            f"About to delete {resource_count} resource(s) and {len(users_to_delete)} user(s)."
        ))
        if kept_superusers:
            self.stdout.write(f"Superusers kept: {', '.join(kept_superusers)}")
        if keep_usernames:
            self.stdout.write(f"Extra usernames kept (if they exist): {', '.join(sorted(keep_usernames))}")
        if users_to_delete:
            names = [u.username for u in users_to_delete]
            self.stdout.write(f"Users to delete: {', '.join(names[:20])}" + (" ..." if len(names) > 20 else ""))

        if not opts["yes"]:
            self.stdout.write(self.style.NOTICE(
                "Dry run — nothing deleted. Re-run with --yes to actually delete."
            ))
            return

        if resource_count == 0 and not users_to_delete:
            self.stdout.write(self.style.SUCCESS("Nothing to delete."))
            return

        # resources first: Dataset deletion fires GeoNode's pre_delete signal
        # which also tears down the real GeoServer layer/store, not just the row.
        deleted_resources = 0
        for resource in resources.iterator():
            try:
                resource.get_real_instance().delete()
                deleted_resources += 1
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"Failed to delete resource {resource.id} ({resource.title!r}): {exc}"))

        deleted_users = 0
        for user in users_to_delete:
            try:
                user.delete()
                deleted_users += 1
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"Failed to delete user {user.username!r}: {exc}"))

        self.stdout.write(self.style.SUCCESS(
            f"Done. Deleted {deleted_resources}/{resource_count} resources, "
            f"{deleted_users}/{len(users_to_delete)} users."
        ))
