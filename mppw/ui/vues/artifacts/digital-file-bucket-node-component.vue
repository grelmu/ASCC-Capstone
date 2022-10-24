<template>
  <div>
    <div v-if="node.isFolder">
      <o-collapse animation="slide" :open="true">
        <template v-slot:trigger="trigger">
          <div role="button">
            <o-checkbox
              v-model="node.selected"
              @update:modelValue="onFolderSelected"
              :disabled="!selectable"
            ></o-checkbox
            >&nbsp;
            <o-icon :icon="trigger.open ? 'folder-open' : 'folder'"></o-icon
            >&nbsp;&nbsp;{{ baseName(node) }}&nbsp;&nbsp;&nbsp;
            <!-- o-icon :icon="trigger.open ? 'arrow-up-drop-circle' : 'arrow-down-drop-circle'"> </o-icon-->
          </div>
        </template>

        <div
          v-for="(child, index) of (getChildren(node).concat([null]))"
          :key="index"
          style="padding-left: 2em"
        >
          <div v-if="child == null">
            <div role="button">
              <o-checkbox
                :disabled="true"
              ></o-checkbox
              >&nbsp;
              <o-upload v-if="child == null" 
                @update:modelValue="onUploadFileSelect">
                <o-icon :icon="'file-upload'" style="color: gray;"></o-icon>
            </o-upload>
            &nbsp;&nbsp;<span class="text-muted">Upload New File</span>
            </div>
          </div>

          <digital-file-bucket-node-component v-if="child != null"
            :artifactId="artifactId"
            :node="child"
            :selectable="selectable && childrenSelectable"
            @upload-file="onChildUploadFileSelect"
            @rename-file="onChildRenameFile"
          ></digital-file-bucket-node-component>
        </div>
      </o-collapse>
    </div>
    <div v-if="!node.isFolder">
      <o-checkbox v-model="node.selected" :disabled="!selectable"></o-checkbox
      >&nbsp; <o-icon icon="file"></o-icon>&nbsp;&nbsp;
      <a @click="onDownloadFile" style="cursor: pointer">{{ baseName(node) }}</a
      >&nbsp;&nbsp;
      <a @click="onStartRenameFile" style="cursor: pointer"
        ><o-icon icon="circle-edit-outline" size="small"></o-icon
      ></a>

      <o-modal :active="isRenaming">
        <h2>Rename File</h2>

        <o-field label="Filename">
          <o-input v-model="newName"></o-input>
        </o-field>

        <o-button @click="onSubmitRenameFile">Submit</o-button>
      </o-modal>
    </div>
  </div>
</template>

<script>
export default {
  components: {
    "digital-file-bucket-node-component": RemoteVue.asyncComponent(
      "vues/artifacts/digital-file-bucket-node-component.vue"
    ),
  },

  data() {
    return {
      isUploading: false,
      isRenaming: false,
      newName: null,
      childrenSelectable: true,
    };
  },
  props: {
    artifactId: String,
    node: Object,
    selectable: Boolean,
  },
  methods: {
    onFolderSelected(selected) {
      this.onSelected(selected);
      this.childrenSelectable = !this.node.isFolder || !this.node.selected;
    },
    onSelected(selected) {
      this.node.selected = selected;
    },
    onUploadFileSelect(file) {
      let path = this.node.name + file.name;
      this.$emit("upload-file", { node: this.node, path, file });
    },
    onChildUploadFileSelect(event) {
      this.$emit("upload-file", event);
    },
    onStartRenameFile() {
      this.isRenaming = true;
      this.newName = this.node.name;
    },
    onSubmitRenameFile() {
      if (this.newName == this.node.name) return;
      this.$emit("rename-file", { node: this.node, newName: this.newName });

      this.isRenaming = false;
      this.newName = null;
    },
    onChildRenameFile(event) {
      this.$emit("rename-file", event);
    },
    onDownloadFile() {
      const link = document.createElement("a");
      link.href = this.$root.apiUrl(
        "artifacts/" +
          this.artifactId +
          "/services/file-bucket/download?path=" +
          this.node.name
      );
      link.download = this.baseName(this.node);
      link.click();
    },
    baseName(node) {
      let nameSplit = node.name.split("/");
      if (node.isFolder) {
        return nameSplit[nameSplit.length - 2] + "/";
      } else {
        return nameSplit[nameSplit.length - 1];
      }
    },
    getChildren(node) {
      if (typeof node.children === "function") {
        return node.children() || [];
      }
      return node.children || [];
    },
  },
  created() {},
};
</script>

<style scoped>
.small-button {
  height: 1.25em;
  width: 1.25em;
  padding-left: 0.1em;
  padding-right: 0.1em;
  vertical-align: middle;
}
</style>
