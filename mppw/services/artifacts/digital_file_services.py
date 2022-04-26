import furl

from .. import ArtifactServices
from ... import models


class FileServices(ArtifactServices):

    URN_PREFIX = f"{models.DigitalArtifact.URN_PREFIX}:file"

    def can_download(self, artifact: models.DigitalArtifact):
        file_furl = furl.furl(artifact.url_data)
        return file_furl.scheme in self.repo_layer.buckets.allowed_file_bucket_schemes

    def download(self, artifact: models.DigitalArtifact):
        return self.repo_layer.buckets.get_file_by_url(artifact.url_data)
