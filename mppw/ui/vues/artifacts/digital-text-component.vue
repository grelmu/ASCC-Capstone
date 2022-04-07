<template>
  <div v-if="artifact">
    <o-input type="textarea" v-model="artifact.local_data.text"></o-input>

    <div class="mt-3 text-end">
      <o-button @click="onSaveArtifact()" class="text-end" variant="primary"
        >Save Changes</o-button
      >
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      artifact: null,
    };
  },
  props: {
    opId: String,
    artifactId: String,
  },
  methods: {
    refreshArtifact() {
      this.artifact = null;
      return this.$root.apiFetchArtifact(this.artifactId).then((artifact) => {
        this.artifact = artifact;
        this.artifact.local_data ||= {};
        this.artifact.local_data.text ||= "";
      });
    },
    onSaveArtifact() {
      let changes = [];
      changes.push({
        op: "replace",
        path: "local_data",
        value: this.artifact.local_data,
      });

      return this.$root.apiPatchArtifact(this.artifactId, changes).then(() => {
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
