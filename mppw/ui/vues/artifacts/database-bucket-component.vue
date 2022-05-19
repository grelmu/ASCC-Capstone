<template>
  <div v-if="artifact">
    <p><b>MongoDB Read-Only URL: </b> {{artifact.url_data}} </p>
    <div>
    <p><b>Total Size: </b> {{stats.size_bytes}}<p>
    <br>
    <b> Collections: </b>

    <ul v-for="collection in stats.collections" v-bind:key="collection.name">
    <li> {{ collection.name }} : {{ this.shortenBytes(collection.size_bytes) }} </li>
    
    </ul>
    
  </div>
    
  </div>
  
</template>

<script>
export default {
  data() {
    return {
      artifact: null,
      stats:[],
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
      });
    },
    async getData() {
      try {
        let response = await fetch("http://localhost:8000/api/artifacts/62740771eeedc12a68378ddc/services/database-bucket/stats");
        this.stats = await response.json();;
      } catch (error) {
        console.log(error);
      }
    },
    shortenBytes(amount){
      // Takes amount in bytes and returns it in Mb, Gb, Tb where appropiate
      let units = ["Bytes", "MB", "GB", "TB", "PB"];
      let currentUnit = 0; // Points to position in ^^^

      while (amount >= 1000 && currentUnit < 4){
        amount /= 1000;
        currentUnit += 1;
      }
      amount = Math.round(amount * 10) / 10 // Round to one decimal place

      return amount + " " + units[currentUnit];

    },
  },
  created() {
    return this.refreshArtifact(),this.getData();
  },
};
</script>

<style scoped></style>
