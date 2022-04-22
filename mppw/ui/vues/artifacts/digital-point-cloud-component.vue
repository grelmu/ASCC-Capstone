<template>
  <div v-if="artifact">
    <!--
      TODO: 
      - Improve date/time (use a picker)
        - Maybe combo of calendar, clock, and text field (for milliseconds)
        - Have a button that duplicates the min time so they don't have to
          re-specify the date/hour for the upper bound?
      - Improve input for space bounds
      - Paginate the results using JS?? 
        - Better yet, paginate at the API layer
    -->

    <section>
      <o-collapse :open="false" class="card col-12" animation="slide" padding-botton="5px" style="margin-bottom: 5px;">
        <template #trigger="props">
          <div class="card-header" role="button" style="height: 40px;">
            <p class="card-header-title">
              Pull Point Cloud Data
            </p>
            <a class="card-header-icon">
              <o-icon :icon="props.open ? 'caret-up' : 'caret-down'"> </o-icon>
            </a>
          </div>
        </template>
        <div class="card-content col-6">
          <div class="content" style="padding: 20px;">
            <o-field label="id">
              <o-input v-model="artifact.local_data.id"></o-input>
            </o-field>
            <o-field label="space_bounds">
              <!-- e.g.: [[-100000, -100000, -100000], [100000, 100000, 100000]] -->
              <o-input placeholder="[[x1, y1, z1], [x2, y2, z2]]"
                v-model="artifact.local_data.space_bounds"></o-input>
            </o-field>
            <o-field label="time_bounds">
              <!-- e.g.: ["2022-02-04T16:02:47.633000", "2022-02-04T16:02:47.90"] -->
              <o-input placeholder="[ start_time , end_time ]"
                v-model="artifact.local_data.time_bounds"></o-input>
            </o-field>
            <o-field label="coerce_dt_bounds">
              <o-checkbox v-model="artifact.local_data.coerce_dt_bounds">True</o-checkbox>
            </o-field>
            <o-field label="format">
              <o-input v-model="artifact.local_data.format"></o-input>
            </o-field>
            <div class="mt-3 text-end">
            <o-button @click="getPointCloud()"
              class="text-end">
              Get Point Cloud
            </o-button>
            <o-button v-if="Object.keys(artifact.response).length > 0"
              @click="downloadPointCloud(artifact.response)"
              class="text-end btn-outline-secondary">
                Download Point Cloud
            </o-button>
            </div>
          </div>
        </div>

        <div class="col-6 border rounded pcl-res-container">
          <pre class="col-12">{{ JSON.stringify(artifact.response, null, 2) }}</pre>
        </div>

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

      return this.$root.apiFetchPointcloud(
        this.artifactId,
        this.artifact.local_data).then((result) => {
          this.artifact.response = result;
      });
    },
    downloadPointCloud(aft) {
      // "aft" - artifact.response JSON object

      // Stringify and format with 2 spaces for indentation
      const data = JSON.stringify(aft, null, 2);
      const blob = new Blob([data], {type: 'application/json'});
      // Create an anchor tag, append the blob, and then click it to
      // start the download
      let a = document.createElement('a');
      a.download = "point_cloud.json";
      a.href = window.URL.createObjectURL(blob);
      a.click();
    }
  },
  created() {
    return this.refreshArtifact();
  },
};
</script>

<style scoped>
.o-btn.btn-outline-secondary {
  color: initial;
  background-color: white;
  margin-left: 5px;
}
.pcl-res-container {
  max-height: 400px;
  overflow: hidden;
  margin: 10px 0px 0px 0px;
}
.pcl-res-container pre {
  margin-right: 10px;
  height: 100%;
}
</style>
