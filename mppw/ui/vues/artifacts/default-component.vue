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

     apiFetchArtifact(id) {
      return this.$root
        .apiFetch("artifacts/" + id, { method: "GET" })
        .then((response) => {
          if (response.status == 200) return response.json();
          else return { version: "" };
        })
    },
    refreshArtifact() {
      this.artifact = null;
      return this.apiFetchArtifact(this.artifactId)
        .then((artifact) => {
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