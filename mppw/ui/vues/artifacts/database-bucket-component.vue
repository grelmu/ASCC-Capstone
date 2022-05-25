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
      <div class="tab-pane fade show active" id="pills-home" role="tabpanel" aria-labelledby="pills-home-tab"><p><b>MongoDB Read-Only URL: </b> {{read_only_url}} </p> </div>
      <div class="tab-pane fade" id="pills-profile" role="tabpanel" aria-labelledby="pills-profile-tab"><p><b>MongoDB Read-Write URL: </b> {{local_url}} </p> </div>
  </div>
   
    <div>
    <p><b>Total Size: </b> {{this.shortenBytes(stats.size_bytes)}}</p>
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
      local_url: null,
      read_only_url:null,
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
        this.local_url=this.replace_mongo_local(artifact.url_data)
        this.read_only_url=this.generate_read_only_link(artifact.url_data)
        this.getData(artifact.id)
      });
    },
    //Function to get the stats data using the api
    async getData(id) {
      try {
        let response = await fetch("http://localhost:8000/api/artifacts/"+ id +"/services/database-bucket/stats");
        this.stats = await response.json();;
      } catch (error) {
        console.log(error); 
      }
    },
    // Takes amount in bytes and returns it in Mb, Gb, Tb where appropiate
    shortenBytes(amount){
      let units = ["Bytes", "MB", "GB", "TB", "PB"];
      let currentUnit = 0; // Points to position in ^^^

      while (amount >= 1000 && currentUnit < 4){
        amount /= 1000;
        currentUnit += 1;
      }
      amount = Math.round(amount * 10) / 10 // Round to one decimal place

      return amount + " " + units[currentUnit];

    },
    //This function replaces window.location instead of mongodb.mppw.local in the database URL
    replace_mongo_local(URL){
      return URL.replaceAll('mongodb.mppw.local','window.location.origin');
    },

    //This function slices the user password into half to generate readonly url link 
    generate_read_only_link(URL){
      //Gets the data between "user:" and "@" in the URL i.e. the password
      let user_password = URL.slice(
      URL.indexOf('user:') + 5,
      URL.lastIndexOf('@'),
      );
      //Divides the password into half
      let new_user_password=user_password.slice(0, (user_password.length/2));
      //Replace the original url with half of the password and changes user to user-ro
      return this.replace_mongo_local(URL.replaceAll(user_password,new_user_password).replaceAll("user","user-ro"));
    }
  },
  created() {
    return this.refreshArtifact();
  },
   
};
</script>

<style>

</style>
