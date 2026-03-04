from rest_framework import serializers

from receivers.externals.notion.api_client import NotionClient


class NotionMigrateSerializer(serializers.Serializer):
    skip_duplicates = serializers.BooleanField(default=False)

    def save(self):
        skip_duplicates = self.validated_data["skip_duplicates"]
        return NotionClient().migrate_to_db(skip_duplicates=skip_duplicates)
