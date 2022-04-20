<template>
  <div v-if="artifact">
    <h1>Point-cloud component works!</h1>
    {{ artifact }}<!-- raw JSON -->
    <!--TODO: add text inputs here -->
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
      // root is API object (sorta). Replace "apiFetchArtifact" with 
      // the proper API call.
      // TODO: Get proper API call
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
