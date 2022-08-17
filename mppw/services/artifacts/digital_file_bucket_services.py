from .. import ArtifactServices
from ... import models


class FileBucketServices(ArtifactServices):
    def init(self, artifact: models.DigitalArtifact, scheme=None, **kwargs):

        bucket_id = f"artfiles-{str(artifact.id)}"
        scheme = scheme or self.repo_layer.buckets.default_file_bucket_scheme
        artifact.url_data = self.repo_layer.buckets.create_file_bucket(
            bucket_id, scheme
        )

        self.repo_layer.artifacts.update(artifact)
        return artifact

    def upload(self, artifact: models.DigitalArtifact, path: str, file, replace=False):
        return self.repo_layer.buckets.add_file_to_bucket(
            artifact.url_data, path, file, replace=replace
        )

    def download(self, artifact: models.DigitalArtifact, path: str):
        return self.repo_layer.buckets.get_file_by_path(artifact.url_data, path)

    def ls(self, artifact: models.DigitalArtifact, path: str):
        return self.repo_layer.buckets.ls_bucket(artifact.url_data, path)

    def rename(self, artifact: models.DigitalArtifact, path: str, new_path: str):
        return self.repo_layer.buckets.rename_file(artifact.url_data, path, new_path)

    def delete(self, artifact: models.DigitalArtifact, path: str):
        return self.repo_layer.buckets.delete_file_by_path(artifact.url_data, path)
