<template>
  <div v-if="artifact">
    <h1>Point-cloud component works!</h1>
    <!-- {{ artifact }}raw JSON -->

    <section>
      <o-collapse :open="false" class="card" animation="slide" style="margin-bottom: 5px;">
        <template #trigger="props">
          <div class="card-header" role="button" style="height: 40px;">
            <p class="card-header-title">
              JSON
            </p>
            <a class="card-header-icon">
              <o-icon :icon="props.open ? 'caret-up' : 'caret-down'"> </o-icon>
            </a>
          </div>
        </template>
        <div class="card-content" style="width: 100%;">
          <div class="content" style="padding: 20px;">
            {{ artifact }}
          </div>
        </div>
      </o-collapse>

      <o-collapse :open="false" class="card" animation="slide" padding-botton="5px" style="margin-bottom: 5px;">
        <template #trigger="props">
          <div class="card-header" role="button" style="height: 40px;">
            <p class="card-header-title">
              Fields 
            </p>
            <a class="card-header-icon">
              <o-icon :icon="props.open ? 'caret-up' : 'caret-down'"> </o-icon>
            </a>
          </div>
        </template>
        <div class="card-content" style="width: 100%;">
          <div class="content" style="padding: 20px;">
            <o-field label="id">
              <o-input v-model="artifact.local_data.id"></o-input>
            </o-field>
            <o-field label="space_bounds">
              <o-input v-model="artifact.local_data.space_bounds"></o-input>
            </o-field>
            <o-field label="time_bounds">
              <o-input v-model="artifact.local_data.time_bounds"></o-input>
            </o-field>
            <o-field label="coerce_dt_bounds">
              <o-checkbox v-model="artifact.local_data.coerce_dt_bounds">True</o-checkbox>
            </o-field>
            <o-field label="format">
              <o-input v-model="artifact.local_data.format"></o-input>
            </o-field>
            <div class="mt-3 text-end">
            <o-button @click="getPointCloud()" class="text-end" variant="primary">Get Point Cloud</o-button>
            </div>
          </div>
        </div>

        {{ artifact.response }}
      </o-collapse>
    </section>
   
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
        console.log(artifact);
        this.artifact = artifact;
        this.artifact.response ||= {};
        this.artifact.local_data ||= {};
        this.artifact.local_data.id = this.artifactId;
        this.artifact.local_data.space_bounds = "";
        this.artifact.local_data.time_bounds = "";
        this.artifact.local_data.coerce_dt_bounds = false;
        this.artifact.local_data.format = "pcb";
      });
    },
    getPointCloud() {
      let changes = [];
      changes.push({
        op: "replace",
        path: "local_data",
        value: this.artifact.local_data,
      });

      console.log(this.artifact.local_data);

      return this.$root.apiFetchPointcloud(this.artifactId, this.local_data).then((result) => {
        this.artifact.response = result;
      });
    },
  },
  created() {
    return this.refreshArtifact();
  },
};
</script>

<style scoped></style>
