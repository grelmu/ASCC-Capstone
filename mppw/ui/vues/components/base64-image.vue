<!--
    Component to render an image given as base64 data - also provides a polyfill for
    rendering tiff images in all browsers.
-->
<template>
  <div>
    <div
      v-if="imageType == 'image/tiff'"
      :id="'base64-image-tiff-' + $.uid"
      :class="getImageClass()"
    ></div>
    <img
      v-if="imageType != 'image/tiff'"
      :class="getImageClass()"
      :src="'data:' + imageType + ';base64,' + imageDataBase64"
    />
  </div>
</template>

<script>
export default {
  data() {
    return {
      // pass
    };
  },
  props: {
    imageType: String,
    imageDataBase64: String,
  },
  methods: {
    buildTiffImage() {
      // Use standard browser data base64 handling via data URIs
      let dataUri =
        "data:application/octet-stream;base64," + this.imageDataBase64;

      return fetch(dataUri)
        .then((result) => result.arrayBuffer())
        .then((buffer) => {
          let tiff = new Tiff({ buffer });
          let canvas = tiff.toCanvas();

          let tiffEl = this.getTiffElement();
          while (tiffEl.lastChild) tiffEl.removeChild(tiffEl.lastChild);
          tiffEl.appendChild(canvas);

          return canvas;
        });
    },
    getImageClass() {
      return (
        "base64-image base64-" + this.imageType.replaceAll(/[^A-Za-z0-9]/g, "-")
      );
    },
    getTiffElement() {
      return document.querySelector("#base64-image-tiff-" + this.$.uid);
    },
  },
  created() {
    // pass
  },
  mounted() {
    if (this.imageType == "image/tiff") return this.buildTiffImage();
  },
};
</script>

<style scoped></style>
