<template>
  <section v-if="artifact">
    <div class="row">
      <o-tabs type = "boxed">
        <o-tab-item label="Elapsed Time">
          <o-slider
            v-model="sliderVal"
            v-on:change="onSliderChange"
            :custom-formatter="sliderPosToTime"
            :min="0"
            :max="sliderMax"
            :step="tstep">
          </o-slider>
          <o-button v-if="!firstSelected" class="mt-3 text-end pcl-btns"
            @click="onFirstSelectorClick">
            Get Samples in Range
          </o-button>
        </o-tab-item>
        <o-tab-item label="Date & Time">
          <div class="row">
            <div class="col">
              <o-field label="Start Date & Time">
                <o-datetimepicker
                  v-model="datetime[0]"
                  icon="clock"
                  placeholder="Click to select..."
                  :timepicker="{ enableSeconds, hourFormat }"
                ></o-datetimepicker>
              </o-field>
            </div>
            <div class="col">
              <o-field label="End Date & Time">
                <o-datetimepicker
                  v-model="datetime[1]"
                  icon="clock"
                  placeholder="Click to select..."
                  :timepicker="{ enableSeconds, hourFormat }"
                ></o-datetimepicker>
              </o-field>
            </div>
          </div>
          <o-button class="mt-3 text-end pcl-btns"
            @click="onSelectorClick">
            Get Samples in Range
          </o-button>
        </o-tab-item>
      </o-tabs>
    </div>

    <o-loading
        :full-page="true"
        :active="isLoadingSampleDocs"
        :can-cancel="false"
      >
        <o-icon icon="loading" size="large" spin> </o-icon>
    </o-loading>

    <div class="row" v-if="sampleDocs">
      <o-tabs type="boxed">
        <o-tab-item label="JSON">
          <big-json :obj="sampleDocs" :downloadName="sampleDownloadName()"></big-json>
        </o-tab-item>
        <o-tab-item v-if = "isImageDocs" label="Image">
          <div class="row">
            <o-carousel v-model="selectedImage" :arrow="true" :arrow-hover="true" :items-to-show="1" :items-to-list="sampleDocs.length < 10 ? 1 : Math.ceil(sampleDocs.length / 10)" :has-drag="true">
              <o-carousel-item v-for="(sampleDoc, i) in sampleDocs" :key="i">
                <base64-image :imageType="inferDocImage(sampleDoc)['imageType']" :imageDataBase64="inferDocImage(sampleDoc)['imageDataBase64']"></base64-image>
              </o-carousel-item>
            </o-carousel>
          </div>
          <div class="row" style="margin-top: 1em;">
            <div class="col-md-4">
              <o-button class="primary"
                @click="onDownloadImagesClick">
                Download Images
              </o-button>
            </div>
          </div>
        </o-tab-item>
        <o-tab-item label="Chart">
          <pivot-table
            :inputData = "pivotData"
            :renderer = "'Scatter Chart'"
            :aggregator = "'List Unique Values'"
            :vertical = "true"
            :domain = "['t']"
            :plotWidthPx = "900"
          ></pivot-table>
        </o-tab-item>
      </o-tabs>
    </div>
  </section>
</template>

<script>
import digitalFrameDocumentComponentVue from './digital-frame-document-component.vue';
export default {
  components: {
    "base64-image": RemoteVue.asyncComponent(
      "vues/components/base64-image.vue"
    ),
    "pivot-table": RemoteVue.asyncComponent(
      "vues/components/pivot-table.vue"
    ),
    "big-json": RemoteVue.asyncComponent(
      "vues/components/big-json.vue"
    ),
  },
  data() {
    return {
      artifact: null,
      timeBounds: null,
      tstep: 1,
      sliderMax: 1,
      sliderVal:[0, 0],
      enableSeconds: true,
      hourFormat: 12,
      datetime: [null,null],
      sampleDocs:null,
      isImageDocs: false,
      selectedImage: null,
      pivotData: null,
      firstSelected: false,
      isLoadingSampleDocs: false,
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
        return this.refreshBounds();
      });
    },
    refreshBounds() {
      return this.$root.apiFetchTimeSeriesBounds(this.artifactId).then((bounds) => {

        let minBound = new Date(bounds[0]);
        let maxBound = new Date(bounds[1]);
        
        if (minBound > maxBound) {
          let swap = maxBound;
          maxBound = minBound;
          minBound = swap;
        }

        minBound.setMinutes(minBound.getMinutes(), minBound.getSeconds(), 0);
        maxBound.setMinutes(maxBound.getMinutes(), maxBound.getSeconds() + 1, 0);

        this.timeBounds = [minBound, maxBound]; // Going to store the bounds as dates
        this.datetime = [minBound, maxBound];   // This copy is for the date time selection

        // Set up the slider
        this.sliderMax = this.timeBoundsToSlider(this.timeBounds)[1];
      })
      .then(() => {
        let minSlider = Math.max(this.sliderMax * 0.9, this.sliderMax - 10)
        this.sliderVal = [minSlider, this.sliderMax];
      });
    },
    inferBoundsFromDocs(docs){
      if(docs.length > 0) {
        let bounds = [new Date(docs[0]["t"]), new Date(docs[docs.length-1]["t"])]; // Making the assumption that the documents are sorted by time
        this.datetime = bounds;
        this.sliderVal = this.timeBoundsToSlider(bounds);
      }
    },
    sliderToTimeBounds(sliderVal) {
      return [new Date(this.timeBounds[0].getTime() + (sliderVal[0] * 1000)),
              new Date(this.timeBounds[0].getTime() + (sliderVal[1] * 1000))];
    },
    timeBoundsToSlider(bounds) {
      return [Math.floor((bounds[0] - this.timeBounds[0]) / 1000),
              Math.ceil((bounds[1] - this.timeBounds[0]) / 1000)];
    },
    sliderPosToTime(sliderPos) {
      if (this.timeBounds == null || sliderPos == null) return "";
      return new Date(this.timeBounds[0].getTime() + (sliderPos * 1000)).toISOString();
    },
    onSliderChange(newSliderVal) {

      // console.log("Slider changed! " + newSliderVal);

      let sampleBounds = this.sliderToTimeBounds(newSliderVal);
      this.datetime = sampleBounds;

      return this.refreshSamples(sampleBounds);
    },
    onFirstSelectorClick() {
      return this.onSliderChange(this.sliderVal);
    },
    onSelectorClick() {

      // console.log("Selector clicked!" + this.datetime);

      if (this.datetime[1] < this.datetime[0]) {
        let swap = this.datetime[1];
        this.datetime[1] = this.datetime[0];
        this.datetime[0] = swap;
      }

      if (this.datetime[0] < this.timeBounds[0])
        this.datetime[0] = this.timeBounds[0];

      if (this.datetime[1] > this.timeBounds[1])
        this.datetime[1] = this.timeBounds[1];

      let sampleBounds = this.datetime;
      this.sliderVal = this.timeBoundsToSlider(sampleBounds);
      return this.refreshSamples(sampleBounds);
    },
    refreshSamples(sampleBounds, doc_limit = 0, byte_limit = 1000) {

      let sampleBoundsStr = [sampleBounds[0].toISOString(), sampleBounds[1].toISOString()];

      let data = {"time_bounds":JSON.stringify(sampleBoundsStr),
                  "limit":JSON.stringify(doc_limit),
                  "est_limit_bytes":JSON.stringify(byte_limit)};

      this.isLoadingSampleDocs = true;
      return this.$root.apiFetchTimeSeries(this.artifactId, data).then((result) => {
        this.sampleDocs = result;
        this.isImageDocs = (this.inferDocImage((this.sampleDocs || []).length > 0 ? this.sampleDocs[0] : {}) != null);
        this.pivotData = this.buildPivotData(this.sampleDocs);
        this.firstSelected = true;
      })
      .finally(() => {
        this.isLoadingSampleDocs = false;
        this.inferBoundsFromDocs(this.sampleDocs);
      });
    },
    toNameSlug(name) {
      return name.replaceAll(/[^A-Za-z0-9]/g, "_").toLowerCase();
    },
    toDtSlug(dt) {
      return dt.toISOString().replaceAll(/[-:.T]/g, "");
    },
    sampleDownloadName() {
      return this.toNameSlug(this.artifact["name"] || "samples") + "_" + this.toDtSlug(this.datetime[0]) + "_" + this.toDtSlug(this.datetime[1]);
    },
    inferDocImage(doc) {
      if ("ctx" in doc) doc = doc["ctx"];
      if ("image_tiff_b64" in doc) return { imageType: "image/tiff", imageDataBase64: doc["image_tiff_b64"]};
      if ("image_png_b64" in doc) return { imageType: "image/png", imageDataBase64: doc["image_png_b64"]};
      if ("image_jpeg_b64" in doc) return { imageType: "image/jpeg", imageDataBase64: doc["image_jpeg_b64"]};
      return null;
    },
    onDownloadImagesClick() {
      
      //
      // TODO: Pull this logic and related into a multi-image component?
      //

      let imageDownloads = [];
      for (let i = 0; i < this.sampleDocs.length; ++i) {
        
        let sampleDoc = this.sampleDocs[i];
        let docImage = this.inferDocImage(sampleDoc);

        if (!docImage) continue;
        let imageUri =
          "data:application/octet-stream;base64," + docImage.imageDataBase64;
        
        let imageTs = new Date(sampleDoc["t"]);
        let imageExt = "." + docImage.imageType.replaceAll(/image\//g, "");
        let imageName = this.toNameSlug(this.artifact["name"] || "sample") + "_" + this.toDtSlug(imageTs) + "_" +
          this.toNameSlug("" + i) + imageExt;

        imageDownloads.push(
          fetch(imageUri)
          .then((result) => result.arrayBuffer())
          .then((buffer) => {
            return { name: imageName, lastModified: imageTs, input: buffer };
          })
        );
      }

      return Promise.all(imageDownloads)
        .then((results) => {
          return downloadZip(results).blob();
        })
        .then((blob) => {
          const link = document.createElement("a");
          link.href = URL.createObjectURL(blob);
          link.download = "images" + "_" + this.sampleDownloadName() + ".zip";
          document.body.appendChild(link); // required for firefox
          link.click();
          link.remove();
        });
    },
    // Took this from: https://stackoverflow.com/questions/19098797/fastest-way-to-flatten-un-flatten-nested-javascript-objects#:~:text=Flatten%20a%20JSON%20object%3A,))%20%7B%20var%20length%20%3D%20table.
    flattenObject(obj){
      var result = {};
      function recurse(current,property){
        if(Object(current) !== current){ // handles case where current is not an object
          result[property] = current;
        } else if(Array.isArray(current)){ // array case
          for(var i = 0, l=current.length; i<l;i++){
            recurse(current[i], prop + "[" + i + "]");
          }
          if(l==0){
            result[property] = [];
          }
        } else {
          var empty = true;
          for(var prop in current){
            empty = false;
            recurse(current[prop],property ? property+"."+prop : prop);
          }
          if(empty && prop){
            result[prop] = {};
          }
        }
      }
      recurse(obj,"");
      return result;
    },

    buildPivotData(sample) {
      let data = [];
      for(var i=0;i<sample.length;i++){
        let row = this.flattenObject(sample[i]);
        data.push(row);
      }
      return data;
    },
  },
  created() {
    return this.refreshArtifact();
  },
};
</script>

<style scoped>

  
</style>