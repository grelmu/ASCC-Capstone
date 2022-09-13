<!--
    Component to render a text box with (potentially) very large JSON values
-->
<template>
  <div>
    <div class="row border rounded big-json-container">
      <div v-if="!shouldShowJson()" class="big-json-large-warning">
        <p>
          Large response &lpar;{{ obj.length }} items&rpar; not displayed for
          page performance.<br />
          <b>Please download to view data.</b>
        </p>
      </div>
      <pre v-if="shouldShowJson()">{{ JSON.stringify(obj, null, 2) }}</pre>
    </div>

    <div class="row" style="margin-top: 1em;">
      <div class="col-md-4">
        <o-button class="primary" @click="onDownloadClick">
          Download JSON
        </o-button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {};
  },
  props: {
    obj: Object,
    downloadName: String,
  },
  methods: {
    shouldShowJson() {
      return this.obj.length < 5000;
    },
    onDownloadClick() {
      let dataStr =
        "data:text/json;charset=utf-8," +
        encodeURIComponent(JSON.stringify(this.obj));
      var anchor = document.createElement("a");
      anchor.setAttribute("href", dataStr);
      anchor.setAttribute(
        "download",
        (this.downloadName || "samples") + ".json"
      );
      document.body.appendChild(anchor); // required for firefox
      anchor.click();
      anchor.remove();
    },
  },
  created() {
    //
  },
};
</script>
<style scoped>
.big-json-container {
  max-height: 25em;
  overflow-x: hidden;
  overflow-y: auto;
}
.big-json-container >>> pre {
  font-size: x-small;
}
.big-json-large-warning {
  display: flex;
  width: 100%;
  height: 15em;

  text-align: center;
  justify-content: center;
  align-items: center;

  background-color: rgb(235, 235, 235);
  color: rgb(56, 56, 56);
}
.big-json-large-warning >>> p {
  padding: 1em;
}
</style>
