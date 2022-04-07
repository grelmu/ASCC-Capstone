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
        types: [{ type_urn: null, child_kinds: attachmentKinds }],
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
        .apiFetchArtifactsRoot(this.opId)
        .then((artifactsRoot) => {
          this.artifactsRoot = artifactsRoot;
        });
    },
    refreshAttachmentKinds() {
      this.attachmentKinds = null;
      return this.$root
        .apiFetchAttachmentKinds(this.op.type_urn)
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
