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
    apiFetchArtifact(id) {
      return this.$root
        .apiFetch("artifacts/" + id, { method: "GET" })
        .then((response) => {
          if (response.status == 200) return response.json();
          else return { version: "" };
        });
    },
    refreshArtifact() {
      this.artifact = null;
      return this.apiFetchArtifact(this.artifactId).then((artifact) => {
        this.artifact = artifact;
        this.artifact.local_data ||= {};
        this.artifact.local_data.text ||= "";
      });
    },
    onSaveArtifact() {
      return this.apiUpdateArtifact(this.artifact)
        .then(() => {
          return this.refreshArtifact();
        });
    },
    apiUpdateArtifact(artifact) {
      return this.$root
        .apiFetch("artifacts/" + artifact["id"], {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(artifact),
        })
        .then((response) => {
          if (response.status == 200) return response.json();
          this.$root.throwApiResponseError(
            response,
            "Unknown response when updating artifact"
          );
        });
    },
  },
  created() {
    return this.refreshArtifact();
  },
};
</script>

<style scoped>
</style>