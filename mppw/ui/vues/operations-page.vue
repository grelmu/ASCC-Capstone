<template>
  <div v-if="op">
    <h1>{{ op.name }}</h1>

    <p>{{ op }}</p>

    <operation-artifact-node
      v-if="artifactsRoot && attachmentKinds"
      class="mb-5"
      :projectId="op.project"
      :opId="opId"
      :artifactPath="[]"
      :artifactNode="artifactsRoot"
      :attachmentKind="{
        kind_urn: null,
        types: [attachmentKinds],
      }"
    ></operation-artifact-node>
  </div>
</template>

<script>
export default {
  components: {
    "operation-artifact-node": RemoteVue.asyncComponent(
      "vues/operation-artifact-node.vue"
    ),
  },

  data() {
    return {
      opId: null,
      op: null,

      artifactsRoot: null,
      attachmentKinds: null,
    };
  },

  methods: {
    refreshOperation() {
      this.op = null;
      return this.$root.apiFetchOperation(this.opId).then((op) => {
        this.op = op;
        return this.refreshArtifactGraph();
      });
    },
    refreshArtifactGraph() {
      this.artifactGraph = null;
      this.artifactOpenIndexes = null;
      return this.$root
        .apiFetchOperationArtifacts(this.opId)
        .then((attachments) => {
          // TODO: Make sure this is now necessary
          let kindPathFor = function (attachment) {
            return attachment["kind_path"].join(".");
          };

          let artifactPathFor = function (attachment) {
            return (
              attachment["kind_path"].join(".") +
              (attachment["artifact_id"] != null
                ? "." + attachment["artifact_id"]
                : "")
            );
          };

          let parentArtifactPathFor = function (attachment) {
            if (attachment["kind_path"].length < 1) return null;
            return attachment["kind_path"]
              .slice(0, attachment["kind_path"].length - 1)
              .join(".");
          };

          attachments.sort((a, b) =>
            artifactPathFor(a).localeCompare(artifactPathFor(b))
          );

          let parentKindNodes = {};
          let parentArtifactNodes = {};

          for (let i = 0; i < attachments.length; ++i) {
            let attachment = attachments[i];

            let kindPath = kindPathFor(attachment);
            let kindNode = parentKindNodes[kindPath];
            if (kindNode == null) {
              kindNode = {
                kind_urn: kindPath,
                artifacts: [],
              };

              parentKindNodes[kindPath] = kindNode;

              let parentArtifactPath = parentArtifactPathFor(attachment);

              if (parentArtifactPath != null) {
                let parentArtifactNode =
                  parentArtifactNodes[parentArtifactPath];
                parentArtifactNode.attachments.push(kindNode);
              }
            }

            let artifactNode = {
              artifact_id: attachment["artifact_id"],
              is_input: attachment["attachment_mode"] == "input",
              attachments: [],
            };

            let artifactPath = artifactPathFor(attachment);
            parentArtifactNodes[artifactPath] = artifactNode;
            kindNode.artifacts.push(artifactNode);
          }

          console.log(parentArtifactNodes[""]);
          return parentArtifactNodes[""];
        })
        .then((artifactsRoot) => {
          this.artifactsRoot = artifactsRoot;
        });
    },
    refreshAttachmentKinds() {
      this.attachmentKinds = null;
      return this.$root
        .apiFetchOperationType(this.op.type_urn)
        .then((schema) => {
          console.log(schema.attachments);
          return schema.attachments;
        })
        .then((kinds) => {
          this.attachmentKinds = kinds;
        });
    },
  },
  created() {
    this.opId = this.$route.params.id;
    this.refreshOperation().then(() => {
      return this.refreshAttachmentKinds();
    });
  },
};
</script>

<style scoped>
.card {
  max-width: 100%;
  position: relative;
}
.card-header {
  align-items: stretch;
  display: flex;
}
.card-header-title {
  align-items: center;
  display: flex;
  flex-grow: 1;
  padding: 0.75rem;
  margin: 0;
}
.card-header-icon {
  align-items: center;
  cursor: pointer;
  display: flex;
  padding: 0.75rem;
  justify-content: center;
}
.card-content {
  padding: 1.5rem;
  width: 100%;
}
</style>
