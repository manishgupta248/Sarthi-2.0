class AllRecordsAdminMixin:
    """Lets the admin site see archived (soft-deleted) records so they can be restored."""

    def get_queryset(self, request):
        return self.model.all_objects.all()
