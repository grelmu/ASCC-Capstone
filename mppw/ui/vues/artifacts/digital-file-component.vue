<template>
  <div v-if="artifact">
    <div class="mt-3 row" v-if="opAttachments">
      <div class="col-md-auto">
        <o-radio
          v-model="storageType"
          name="name"
          native-value="attachment"
        ></o-radio>
      </div>
      <div class="col-md-auto">
        <o-field label="Local File Attachment">
          <o-input
            v-if="storageType == 'attachment'"
            v-model="attachmentPath"
          ></o-input>
          <o-button
            v-if="
              storageType == 'attachment' &&
              computeStorageType(artifact) == 'attachment' &&
              !uploadFile
            "
            variant="primary"
            @click="onDownloadFile"
            ><o-icon icon="download" size="small"></o-icon
            >&nbsp;Download</o-button
          >
          <o-upload
            v-if="storageType == 'attachment'"
            @update:modelValue="onUploadFileSelected"
          >
            <o-button tag="a" variant="info"
              ><o-icon icon="upload" size="small"></o-icon
              >&nbsp;Upload</o-button
            >
          </o-upload>
          <o-button
            v-if="storageType == 'attachment' && uploadFile"
            variant="warning"
            @click="onUploadFileRemoved"
            ><o-icon icon="trash-can" size="small"></o-icon
            >&nbsp;Cancel</o-button
          >
        </o-field>
        <div v-if="uploadFile">
          <o-icon icon="upload"></o-icon
          ><span class="font-monospace"
            ><span class="fw-bold">.../{{ uploadFile.name }}</span> ({{
              uploadFile.size
            }}
            bytes)</span
          >
        </div>
        <div v-if="isProbablyImageFile()">
          <img :src="this.buildDownloadUrl()" style="width: 30%" />
        </div>
      </div>
    </div>
    <div class="mt-3 row">
      <div class="col-md-auto">
        <o-radio
          v-model="storageType"
          name="name"
          native-value="remote"
        ></o-radio>
      </div>
      <div class="col-md-auto">
        <o-field label="Remote File URL">
          <o-input v-if="storageType == 'remote'" v-model="remoteUrl"></o-input>
          <o-button
            v-if="
              storageType == 'remote' &&
              computeStorageType(artifact) == 'remote' &&
              !uploadFile
            "
            variant="primary"
            @click="onFollowUrl"
            ><o-icon icon="arrow-right" size="small"></o-icon>&nbsp;Go</o-button
          >
        </o-field>
      </div>
    </div>

    <div class="mt-3 text-end">
      <o-button @click="onSaveArtifact()" class="text-end" variant="primary"
        >Save Changes</o-button
      >
    </div>

    <o-loading
        :full-page="true"
        :active="isUploading"
        :can-cancel="false"
      >
        <o-icon icon="file-upload" size="large" spin> </o-icon>
    </o-loading>

  </div>
</template>

<script>
export default {
  data() {
    return {
      artifact: null,
      opAttachments: null,
      storageType: null,

      attachmentPath: null,
      uploadFile: null,
      isUploading: false,
      remoteUrl: null,
    };
  },
  props: {
    opId: String,
    artifactKind: String,
    artifactId: String,
  },
  methods: {
    refreshArtifact() {
      this.artifact = null;
      this.opAttachments = null;
      this.storageType = null;
      this.attachmentPath = null;
      this.uploadFile = null;
      this.remoteUrl = null;

      return this.$root
        .apiFetchArtifact(this.artifactId)
        .then((artifact) => {
          this.artifact = artifact;
          return this.$root.apiFetchOpAttachments(this.opId);
        })
        .then((opAttachments) => {
          this.opAttachments = opAttachments;

          this.storageType = this.computeStorageType(this.artifact);
          if (this.storageType == "attachment") {
            this.attachmentPath = this.toOpAttachmentPath(
              this.artifact["url_data"]
            );
          } else if (this.storageType == "remote") {
            this.remoteUrl = this.artifact["url_data"];
          }
        });
    },
    isOpAttachmentsUrl(url) {
      if (!this.opAttachments) return false;
      let attachmentsUrl = this.opAttachments["url_data"];
      if (!attachmentsUrl.endsWith("/")) attachmentsUrl += "/";
      return url.startsWith(attachmentsUrl);
    },
    toOpAttachmentPath(url) {
      return url.replace(this.opAttachments["url_data"], "");
    },
    toOpAttachmentsUrl(path) {
      while (path.startsWith("/")) path = path.substr(1, path.length);
      return this.opAttachments["url_data"] + "/" + path;
    },
    computeStorageType(artifact) {
      return this.artifact["url_data"]
        ? this.isOpAttachmentsUrl(this.artifact["url_data"])
          ? "attachment"
          : "remote"
        : null;
    },
    onFollowUrl() {
      window.open(
        this.$root.apiUrl(
          "artifacts/" + this.artifact["id"] + "/services/file/download"
        ),
        "_blank"
      );
    },
    isProbablyImageFile() {
      if (!this.artifact || !this.artifact["url_data"]) return false;
      let extSplit = this.artifact["url_data"].split(".");
      if (extSplit.length < 2) return false;
      let ext = extSplit[extSplit.length - 1].toLowerCase();
      return ["gif", "png", "jpg", "jpeg"].indexOf(ext) >= 0;
    },
    buildDownloadUrl() {
      if (!this.artifact) return null;
      return this.$root.apiUrl(
        "artifacts/" + this.artifact["id"] + "/services/file/download"
      );
    },
    onDownloadFile() {
      const link = document.createElement("a");
      link.href = this.buildDownloadUrl();
      let filename = this.artifact["url_data"].split("/");
      filename = filename[filename.length - 1];
      link.download = filename;
      link.click();
    },
    onUploadFileSelected(uploadFile) {
      this.uploadFile = uploadFile;
      if (!this.uploadFile) return;
      this.attachmentPath =
        "/" +
        this.artifactKind.replaceAll(":", "") +
        "/" +
        this.uploadFile.name;
    },
    onUploadFileRemoved() {
      this.uploadFile = null;
      this.attachmentPath = null;
      if (this.computeStorageType(this.artifact) == "attachment") {
        this.attachmentPath = this.toOpAttachmentPath(
          this.artifact["url_data"]
        );
      }
    },
    onSaveArtifact() {
      let urlPromise = null;

      if (this.storageType == "attachment") {
        if (this.uploadFile) {
          this.isUploading = true;
          urlPromise = this.$root.apiUploadAttachment(
            this.opAttachments["id"],
            this.attachmentPath,
            this.uploadFile
          );
        } else {
          urlPromise = Promise.resolve(
            this.toOpAttachmentsUrl(this.attachmentPath)
          );
        }
      } else if (this.storageType == "remote") {
        urlPromise = Promise.resolve(this.remoteUrl);
      }

      return urlPromise
        .then((file_url) => {
          let changes = [];
          changes.push({ op: "replace", path: "url_data", value: file_url });

          return this.$root.apiPatchArtifact(this.artifactId, changes);
        })
        .finally(() => {
          this.isUploading = false;
          return this.refreshArtifact();
        });
    },
  },
  created() {
    return this.refreshArtifact();
  },
};
</script>

<style scoped></style>
