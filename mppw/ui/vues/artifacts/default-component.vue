<template>
  <div v-if="artifact">

    {{ artifact }}
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
      });
    },
  },
  created() {
    return this.refreshArtifact();
  },
};
</script>

<style scoped></style>
