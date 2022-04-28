<template>
  <div v-if="artifact">
    <section>
      <o-collapse :open="true" class="card col-12" animation="slide" padding-botton="5px" style="margin-bottom: 5px;">
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
            <o-field label="space_bounds">
              <!--
                TODO:
                  Change placeholder text to show upper/lower bounds
                  once it's added to the API endpoint
              -->
              <!-- e.g.: [[-100000, -100000, -100000], [100000, 100000, 100000]] -->
              <o-input placeholder="[[x1, y1, z1], [x2, y2, z2]]"
                v-model="formData.space_bounds"></o-input>
            </o-field>
            <o-field label="time_bounds_start">
              <!--
                TODO:
                  Change placeholder text to show upper/lower bounds
                  once it's added to the API endpoint
              -->
              <!-- e.g.: ["2022-02-04T16:02:47.633000", "2022-02-04T16:02:47.90"] -->
              <o-datetimepicker
                rounded placeholder="Click to select..." :timepicker="{ enableSeconds, hourFormat }"
                icon="calendar" v-model="timeBoundsStart">
              </o-datetimepicker>
            </o-field>
            <o-field label="time_bounds_end">
              <o-datetimepicker
                rounded placeholder="Click to select..." :timepicker="{ enableSeconds, hourFormat }"
                icon="calendar" v-model="timeBoundsEnd">
              </o-datetimepicker>
            </o-field>
            <o-field label="format">
              <o-input v-model="formData.format"></o-input>
            </o-field>
            <div class="mt-3 text-end">
            <o-button @click="getPointCloud()"
              class="text-end">
              Get Point Cloud
            </o-button>
            <o-button v-if="Object.keys(response).length > 0"
              @click="downloadPointCloud(response)"
              class="text-end btn-outline-secondary">
                Download Point Cloud
            </o-button>
            </div>
          </div>
        </div>

        <div class="col-6 border rounded pcl-res-container">
          <!--
            TODO: 
              Paginate the results for large data (once API supports this)
          -->
          <pre class="col-12">{{ JSON.stringify(response, null, 2) }}</pre>
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
      enableSeconds: true,
      formData: {
        'id': '',
        'space_bounds': '',
        'time_bounds': '',
        'coerce_dt_bounds': false,
        'format': 'pcb'
      },
      hourFormat: '24',
      locale: undefined,
      timeBoundsStart: null,
      timeBoundsEnd: null,
      response: null
    };
  },
  props: {
    opId: String,
    artifactId: String,
  },
  methods: {
    refreshArtifact() {
      this.artifact = null;
      this.timeBoundsStart = new Date();
      this.timeBoundsEnd = new Date();
      return this.$root.apiFetchArtifact(this.artifactId).then((artifact) => {
        console.log(artifact);
        this.artifact = artifact;
        this.formData.id = this.artifactId;
        this.response ||= {};
      });
    },
    getPointCloud() {
      /*
      toISOString() results in Zulu time, which is +5 from New York.
      We reapply the timezone offset between the user's timezone and Zulu 
      so that what the user enters is what is queried on the backend.
      */
      this.formData.time_bounds = JSON.stringify(
        [
          new Date(this.timeBoundsStart.getTime() - (this.timeBoundsStart.getTimezoneOffset() * 60 * 1000)).toISOString(),
          new Date(this.timeBoundsEnd.getTime() - (this.timeBoundsEnd.getTimezoneOffset() * 60 * 1000)).toISOString()
        ]
    );

      return this.$root.apiFetchPointcloud(
        this.artifactId,
        this.formData).then((result) => {
          this.response = result;
      });
    },
    /**
     * This function blobs the JSON response and downloads it as a file.
     * 
     * Args
     *    aft: the artifact.response JSON object to be blobbed
     */
    downloadPointCloud(aft) {
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
