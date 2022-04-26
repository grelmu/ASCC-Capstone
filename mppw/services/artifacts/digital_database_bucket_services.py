from .. import ArtifactServices

from ... import models


class DatabaseBucketServices(ArtifactServices):
    def init(self, artifact: models.DigitalArtifact, scheme=None, **kwargs):

        bucket_id = f"artdb-{str(artifact.id)}"
        scheme = scheme or self.repo_layer.buckets.default_db_bucket_scheme
        artifact.url_data = self.repo_layer.buckets.create_db_bucket(bucket_id, scheme)

        self.repo_layer.artifacts.update(artifact)
        return artifact
