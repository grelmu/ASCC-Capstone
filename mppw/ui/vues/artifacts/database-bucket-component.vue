<template>
  <div v-if="artifact">
     

    <ul class="nav nav-pills mb-3" id="pills-tab" role="tablist">
  <li class="nav-item">
    <a class="nav-link active" id="pills-home-tab" data-toggle="pill" href="#pills-home" role="tab" aria-controls="pills-home" aria-selected="true">Read Only URL</a>
  </li>
  <li class="nav-item">
    <a class="nav-link" id="pills-profile-tab" data-toggle="pill" href="#pills-profile" role="tab" aria-controls="pills-profile" aria-selected="false">Read and Write URL</a>
  </li>
  </ul>
  <div class="tab-content" id="pills-tabContent">
    <div class="tab-pane fade show active" id="pills-home" role="tabpanel" aria-labelledby="pills-home-tab"><p><b>MongoDB Read-Only URL: </b> {{artifact.url_data}} </p></div>
    <div class="tab-pane fade" id="pills-profile" role="tabpanel" aria-labelledby="pills-profile-tab"><p><b>MongoDB Read-Write URL: </b> {{artifact.url_data}} </p></div>
  </div>
   
    <div>
    <p><b>Total Size: </b> {{this.shortenBytes(stats.size_bytes)}}<p>
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
      url: null,
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

<style>

</style>
