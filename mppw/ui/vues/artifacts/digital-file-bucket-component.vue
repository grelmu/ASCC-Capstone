<template>
  <div v-if="artifact && root">
    <digital-file-bucket-node-component
      :artifactId="artifact['id']"
      :node="root"
      :selectable="true"
      @upload-file="onUploadFileSelect"
      @rename-file="onRenameFile"
    ></digital-file-bucket-node-component>

    <div class="mt-3 text-end">
      <o-button
        @click="onDeleteFiles()"
        variant="danger"
        class="text-end"
        :disabled="isDeleting"
        >Delete Selected</o-button
      >
    </div>
  </div>
</template>

<script>
import DigitalFileBucketNodeComponent from "./digital-file-bucket-node-component.vue";
export default {
  components: {
    "digital-file-bucket-node-component": RemoteVue.asyncComponent(
      "vues/artifacts/digital-file-bucket-node-component.vue"
    ),
  },

  data() {
    return {
      artifact: null,
      root: null,
      isDeleting: false,
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
      this.root = null;

      return this.$root
        .apiFetchArtifact(this.artifactId)
        .then((artifact) => {
          this.artifact = artifact;
          return this.$root.apiFetchFileBucketListing(this.artifactId);
        })
        .then((listing) => {
          this.root = {
            name: "/",
            isFolder: true,
            children: this.listingToNodes(listing),
          };
        });
    },
    listingToNodes(listing) {
      let nodes = [];
      listing.sort((x, y) => x.name.localeCompare(y.name));

      let folders = {};
      for (let i = 0; i < listing.length; ++i) {
        let node = listing[i];
        let path_segments = node.name.split("/");
        let path = "/";
        let lastFolder = null;

        for (let j = 0; j < path_segments.length - 1; ++j) {
          if (path_segments[j] == "") continue;
          path = path + path_segments[j] + "/";

          let folder = folders[path];
          if (!folder) {
            folder = {
              name: path,
              isFolder: true,
              children: [],
            };
            folders[path] = folder;

            if (lastFolder) lastFolder.children.push(folder);
            else nodes.push(folder);
          }

          lastFolder = folder;
        }

        let folder = folders[path];
        if (lastFolder) lastFolder.children.push(node);
        else nodes.push(node);
      }

      return nodes;
    },
    onUploadFileSelect(event) {
      return this.$root
        .apiUploadFile(this.artifactId, event.path, event.file)
        .finally(() => {
          return this.refreshArtifact();
        });
    },
    onRenameFile(event) {
      return this.$root
        .apiRenameFile(this.artifactId, event.node.name, event.newName)
        .finally(() => {
          return this.refreshArtifact();
        });
    },
    getSelectedNodes() {
      let fringe = [[false, this.root]];
      let selectedNodes = [];

      while (fringe.length > 0) {
        let next = fringe.pop();
        let parentSelected = next[0];
        let node = next[1];

        let selected = node.selected || parentSelected;
        if (node.isFolder) {
          for (let i = 0; i < node.children.length; ++i) {
            fringe.push([selected, node.children[i]]);
          }
        } else if (selected) {
          selectedNodes.push(node);
        }
      }

      return selectedNodes;
    },
    onDeleteFiles() {
      let selectedNodes = this.getSelectedNodes();

      if (
        !confirm(
          "Are you sure you want to delete " + selectedNodes.length + " files?"
        )
      )
        return;

      this.isDeleting = true;
      let deletePromises = [];
      for (let i = 0; i < selectedNodes.length; ++i) {
        deletePromises.push(
          this.$root.apiDeleteFile(this.artifactId, selectedNodes[i].name)
        );
      }

      return Promise.all(deletePromises).finally(() => {
        this.isDeleting = false;
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
