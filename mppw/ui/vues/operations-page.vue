<template>
  <div v-if="op">
    <operation-metadata
    :metadata="op"></operation-metadata>

    <operation-artifact-node
      v-if="opSchema"
      class="mb-5"
      :projectId="op.project"
      :opId="opId"
      :artifactPath="[]"
      :attachmentKind="{
        kind_urn: null,
        types: [opSchema.attachments],
      }"
    ></operation-artifact-node>
  </div>
</template>

<script>
import OperationMetadata from './operation-metadata.vue';
export default {
  components: {
    "operation-artifact-node": RemoteVue.asyncComponent(
      "vues/operation-artifact-node.vue"
    ),
    "operation-metadata": RemoteVue.asyncComponent(
      "vues/operation-metadata.vue"
    ),
  },

  data() {
    return {
      // Loaded from path
      opId: null,

      op: null,
      opSchema: null,
    };
  },

  methods: {
    refreshOperation() {
      this.op = null;
      this.opSchema = null;
      return this.$root.apiFetchOperation(this.opId).then((op) => {
        return this.$root.apiFetchOperationType(op.type_urn).then((schema) => {
          this.op = op;
          this.opSchema = schema;
        });
      });
    },
  },
  created() {
    this.opId = this.$route.params.id;
    return this.refreshOperation();
  },
};
</script>

<style scoped></style>
