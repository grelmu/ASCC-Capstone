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
              <!-- e.g.: [[-100000, -100000, -100000], [100000, 100000, 100000]] -->
              <o-input placeholder="[[x1, y1, z1], [x2, y2, z2]]"
                v-model="formData.space_bounds"></o-input>
            </o-field>
            <o-field label="time_bounds_start">
              <!-- e.g.: ["2022-02-04T16:02:47.633000", "2022-02-04T16:02:47.90"] -->
              <o-datetimepicker
                rounded placeholder="Click to select..." :timepicker="{ enableSeconds, hourFormat }"
                icon="calendar" v-model="timeBoundsStart" @update:modelValue="normalizeTimeBounds">
              </o-datetimepicker>
            </o-field>
            <o-field label="time_bounds_end">
              <o-datetimepicker
                rounded placeholder="Click to select..." :timepicker="{ enableSeconds, hourFormat }"
                icon="calendar" v-model="timeBoundsEnd" @update:modelValue="normalizeTimeBounds">
              </o-datetimepicker>
            </o-field>
            <div class="mt-3 text-end pcl-btns">
              <o-button @click="getPointCloud()"
                class="text-end">
                Get Point Cloud
              </o-button><br/>
              <o-button
                @click="downloadPointCloud()"
                class="text-end"
                variant="info">
                  Download Full Point Cloud
              </o-button>
              <o-button
                v-if="response[0]"
                @click="toggleThree()"
                class="text-end"
                variant="info">
                  Visualize
              </o-button>
            </div>

            <p id="dl-label" v-if="tbChunks.length > 0">
              Incremental Downloads
            </p>

            <div class="mt-3 text-end pcl-btns scrolling-btn-row">
              <o-button v-if="tbChunks.length > 0"
                id="l-scroll-btn" @click="scb(-300)">←</o-button>
              <div v-for="(chunk, index) in tbChunks"
                class="text-end chunk-btn-wrapper o-btn"
                outlined
                :title="'FROM:\n' + chunk['start'] + '\n\nTO:\n' + chunk['end']"
                :key="chunk['start']">
                <div class="chunk-btn-ctr">
                  <o-button inverted @click="(e) => {
                      downloadPointCloud(e, chunk, `pc_chunk_${index}`)
                    }"><o-icon :icon="'download'"></o-icon>
                  </o-button>
                  <o-button inverted @click="(e) => {
                      getPointCloudChunk(e, chunk)
                    }"><o-icon :icon="'eye'"></o-icon>
                  </o-button>
                </div>
                <p>Chunk {{index}}</p>
              </div><br/>
              <o-button v-if="tbChunks.length > 0"
                id="r-scroll-btn" @click="scb(300)">→</o-button>
            </div>
          </div>
        </div>

        <div class="col-6 border rounded pcl-res-container">
          <!--
            TODO: 
              Paginate the results for large data (once API supports this)
          -->
          <div v-if="!visualizePoints" class="large-warning-ctr">
            <pre v-if="response.length < 5000" class="col-12">
              {{ JSON.stringify(response, null, 2) }}
            </pre>
            <div class="large-warning" v-else-if="response.length >= 5000"> 
              <p>
                Large response &lpar;{{response.length}} items&rpar;
                not displayed for page performance.
                <br />
                <br />
                <b>Please download to view data.</b>
              </p>
            </div>
          </div>
          <div id="three-parent-container">
            <scatter-plot v-if="response[0]" :importData=response :key=response></scatter-plot>
          </div>
        </div>
      </o-collapse>
    </section>
   
  </div>
</template>

<script>
import scatterPlot from '../scatter-plot.vue';
export default {
  components: { scatterPlot },
  data() {
    return {
      artifact: null,
      enableSeconds: true,
      formData: {
        'space_bounds': '',
        'time_bounds': '',
        'coerce_dt_bounds': true,
      },
      hourFormat: '24',
      locale: undefined,
      timeBoundsStart: null,
      timeBoundsEnd: null,
      response: null,
      tbChunks: [],
      visualizePoints: false
    };
  },
  props: {
    opId: String,
    artifactId: String,
  },
  methods: {
    toggleThree(){
      this.visualizePoints ? this.hideThree() : this.showThree();
    },
    showThree() {
      this.visualizePoints = true;
      let container = document.querySelector("#three-parent-container");
      container.classList.add("three-show");
    },
    hideThree() {
      this.visualizePoints = false;
      document.querySelector('#three-parent-container')
      .classList.remove('three-show');
    },
    refreshArtifact() {
      this.artifact = null;
      this.timeBoundsStart = new Date();
      this.timeBoundsEnd = new Date();
      return this.$root.apiFetchArtifact(this.artifactId).then((artifact) => {
        this.artifact = artifact;
        this.response ||= {};
        this.getBoundLimits();
      });
    },
    getBoundLimits() {
        this.$root.apiFetchPointCloudBounds(this.artifactId).then((bounds) => {

          // This api returns the time and space bounds combined like this:
          //      [ [x1,y1,z1,t1], [x2,y2,z2,t2] ]

          let time_bounds = [bounds[0].pop(), bounds[1].pop()];

          // These two bind to the inputs and expect a Date object
          this.timeBoundsStart = new Date(time_bounds[0]);
          this.timeBoundsEnd = new Date(time_bounds[1]);

          this.formData.time_bounds = JSON.stringify(time_bounds);
          this.formData.space_bounds = JSON.stringify(bounds);
          
        });
    },
    normalizeTimeBounds() {
      this.formData.time_bounds = this.normTB(
        {
          "start": this.timeBoundsStart,
          "end": this.timeBoundsEnd
        }
      )
    },
    normTB(tb) {
      /*
        toISOString() results in Zulu time, which is +5 from New York.
        We reapply the timezone offset between the user's timezone and Zulu 
        so that what the user enters is what is queried on the backend.
      */
      return JSON.stringify(
        [
          new Date(tb["start"].getTime() - (tb["start"].getTimezoneOffset() * 60 * 1000)).toISOString(),
          new Date(tb["end"].getTime() - (tb["end"].getTimezoneOffset() * 60 * 1000)).toISOString()
        ]
      );
    },
    getPointCloud() {
      this.visualizePoints = false;
      // Clear style on previously clicked chunk buttons:
      document.querySelectorAll('.clicked-dl-btn').forEach(item => {item.classList.remove('clicked-dl-btn')})
      return this.$root.apiFetchPointcloud(
        this.artifactId,
        this.formData).then((result) => {
          this.response = result;

          this.tbChunks = this.getDateChunks(
            new Date(this.timeBoundsStart),
            new Date(this.timeBoundsEnd),
            // This means chunks are 60 minutes long: 
            60
          );
      });
    },
    // Get point cloud, but for a chunk not the whole range 
    getPointCloudChunk(e, chunk) {
      this.hideThree();
      // Update styling so the current chunk button is visually selected
      document.querySelectorAll('.selected-chunk').forEach(el =>{el.classList.remove('selected-chunk')});
      let targ = e.target;
      while (targ.classList.contains('chunk-btn-wrapper') == false) {
        targ = targ.parentElement;
      }
      targ.classList.add("selected-chunk");

      // Query for the chunk's data and display in the pane on the right
      this.$root.apiFetchPointcloud(this.artifactId, 
      {
        space_bounds: this.formData.space_bounds,
        time_bounds: this.normTB(chunk),
        coerce_dt_bounds: this.formData.coerce_dt_bounds
      }).then(res => {
        this.response = res;
      });
    },
    /**
     * This function redirects to a download link to the points specified by the query
     */
    downloadPointCloud(e = null, chunk = null, fname = "point_cloud") {
      let url;

      // Create an anchor tag and then click it to start the download
      let a = document.createElement('a');
      a.download = `${fname}.json`;

      if (chunk == null) {
        // We clicked the full download button, not a specific chunk
        url = this.$root.apiUrl(this.$root.apiFetchPointcloudUrl(this.artifactId, this.formData));
      } else {
        url = this.buildIntervalURL(e, chunk);
      }
      a.href = url;
      a.click();
    },
    /**
     * Divide a specified time range into n smaller [start, end] pairs
     * based on a given subset size (i.e. 2 minute subsets)
     * 
     * Parameters:
     * - start: the start time of the full range
     * - end: the end time of the full range
     * - chunkSize: the size of each smaller constituent time range in minutes
     * 
     * Returns:
     * - an array of {start: Date(), end: Date()} objects representing
     *   constituent chunks of the parent range
     */
    getDateChunks(start, end, chunkSize) {
      let result = [];
      let s = new Date(start);
      while (s < end) {
        let e = new Date(s);
        e.setMinutes(e.getMinutes() + chunkSize);
        result.push({start:new Date(s), end: e <= end? e : new Date(end)});
        s.setMinutes(s.getMinutes() + chunkSize + 1); 
      }
      return result;
    },
    /**
     * Creates a URL to download point cloud for a specified time range.
     * Parameters:
     * - chunk: an object with a start time and end time e.g:
     *          {start: Date(), end: Date()}
     * Returns:
     * - url string usable to download a subset of the overall pointcloud
     */
    buildIntervalURL(e, chunk) {
      let targ = e.target;
      // doing this because if the user clicks on the text inside
      // the button the event target isn't the button.
      while (targ.classList.contains('chunk-btn-wrapper') == false) {
        targ = targ.parentElement;
      }
      targ.classList.add('clicked-dl-btn');

      let url = this.$root.apiUrl(
        this.$root.apiFetchPointcloudUrl(this.artifactId, 
        {
          space_bounds: this.formData.space_bounds,
          time_bounds: this.normTB(chunk),
          coerce_dt_bounds: this.formData.coerce_dt_bounds
        })
      );
      return url;
    },
    // Scroll Chunk Button function
    scb(x) {
      document.querySelector('.scrolling-btn-row').scrollBy({
        top: 0,
        left: x,
        behavior: 'smooth'
      });
    },
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
  overflow-x: hidden;
  overflow-y: auto;
  margin: 10px 0px 0px 0px;
  position: relative;
}
.pcl-res-container pre {
  margin-right: 10px;
  height: 100%;
}
.pcl-btns {
  display: flex;
  flex-direction: row;
  justify-content: flex-start;
}
.pcl-btns:not(.scrolling-btn-row) {
  flex-wrap: wrap;
}
.pcl-btns button.o-btn {
  /* TODO: fix this for chunk buttons */
  margin: 5px;
}
.pcl-btns button.o-btn:first-of-type {
  margin-left: 0px;
}
.large-warning-ctr {height: 100%;}
.large-warning {
  width: 100%;
  height: 100%;
  display: flex;
  text-align: center;
  justify-content: center;
  align-items: center;
  background-color: rgb(235, 235, 235);
  color: rgb(56, 56, 56);
}
.large-warning p {
  margin: 25px;
}
#dl-label {
  text-align: left;
  margin: 20px 0px 0px 0px;
  font-weight: bold;
}
.scrolling-btn-row {
  position: relative;
  max-width: 100%;
  height: 55px;
  overflow: hidden;
  overflow-x: auto;
  justify-content: initial;
  align-items: center;
  border-radius: 4px;
  margin-top: 0px !important;
}
.chunk-btn-wrapper {
  margin: 0px 5px 0px 5px;
  position: relative;
  min-width: 130px;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
}
.chunk-btn-wrapper p {
  position: absolute;
  margin: 0 auto;
  width: 100%;
  text-align: center;
}
.chunk-btn-wrapper .chunk-btn-ctr {
  opacity: 0%;
}
.chunk-btn-wrapper:hover .chunk-btn-ctr {
  opacity: 100%;
}
.chunk-btn-ctr {
  position: absolute;
  width: 100%;
  height: 100%;
  background-color: #bababa;
  display: flex;
  justify-content: space-evenly;
  align-items: center;
}
.chunk-btn-ctr button {
  z-index: 10;
  margin: 0px !important;
  width: 50%;
  border-radius: 0px;
}
#l-scroll-btn, #r-scroll-btn {
  z-index: 15;
  box-shadow: 0px 0px 5px #c0c0c0;
}
#l-scroll-btn {
  position: sticky; left: 0px;
  margin-left: 0px;
}
#r-scroll-btn {position: sticky; right: 0px;}

.scrolling-btn-row .clicked-dl-btn {
  border-color: #c0c0c0 !important;
  color: #c0c0c0 !important;
  background-color: white;
}
.scrolling-btn-row .clicked-dl-btn:hover {
  background-color: white !important;
  border-color: #c0c0c0 !important;
  color: #c0c0c0 !important;
}
.selected-chunk {
  box-shadow: 0px 0px 5px black;
}
#three-parent-container {
  display: none;
  position:absolute;
  width: 100%;
  height: 100%;
  /* max-height: 400px; */
  top: 0;
}
#three-parent-container.three-full-screen {
  position: fixed;
  width: calc(100vw );
  height: calc(100vh - 48px);
  top: 48px;
  z-index: 1000;
  right: 0px;
}

#three-parent-container.three-show {
  display: block;
}
</style>

