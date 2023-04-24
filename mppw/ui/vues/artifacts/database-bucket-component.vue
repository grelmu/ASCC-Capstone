<template>
  <div v-if="artifact">
    <ul class="nav nav-pills mb-3" id="pills-tab" role="tablist">
      <li class="nav-item">
        <a
          :class="showReadOnlyUrl ? 'nav-link active' : 'nav-link'"
          role="tab"
          @click="onClickReadOnly"
          >Read Only URL</a
        >
      </li>
      <li class="nav-item">
        <a
          :class="showReadOnlyUrl ? 'nav-link' : 'nav-link active'"
          role="tab"
          @click="onClickReadWrite"
          >Read and Write URL</a
        >
      </li>
    </ul>
    <div class="tab-content">
      <div
        :class="showReadOnlyUrl ? 'tab-pane fade show active' : 'tab-pane fade'"
        role="tabpanel"
      >
        <p><b>MongoDB Read-Only URL: </b> {{ read_only_url }}</p>
      </div>
      <div
        :class="showReadOnlyUrl ? 'tab-pane fade' : 'tab-pane fade show active'"
        role="tabpanel"
      > 
        <p><b>MongoDB Read-Write URL: </b> {{ local_url }}</p>
        <a :href="this.op_ui_url" target="_blank"><o-button variant="warning">Collect Data in OP UI</o-button></a>
      </div>
    </div>

    <div v-if="stats">
      <p><b>Total Size: </b> {{ this.shortenBytes(stats.size_bytes) }}</p>
      <br />
      <b> Collections: </b>
      <ul v-for="collection in stats.collections" v-bind:key="collection.name">
        <li>
          {{ collection.name }} : {{ this.shortenBytes(collection.size_bytes) }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      local_url: null,
      read_only_url: null,
      artifact: null,
      stats: null,

      showReadOnlyUrl: true,
    };
  },
  computed: {
    op_ui_url: function() {
      return "http://localhost:5000/dashboard?db_uri="+encodeURI(this.local_url)
    }
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
        this.local_url = this.replace_mongo_local(artifact.url_data);
        this.read_only_url = this.generate_read_only_link(artifact.url_data);
        return this.$root
          .apiFetchDatabaseBucketStats(artifact.id)
          .then((stats) => {
            this.stats = stats;
          });
      });
    },
    // Takes amount in bytes and returns it in Mb, Gb, Tb where appropiate
    shortenBytes(amount) {
      let units = ["Bytes", "KB", "MB", "GB", "TB", "PB"];
      let currentUnit = 0; // Points to position in ^^^

      while (amount >= 1000 && currentUnit < 4) {
        amount /= 1000;
        currentUnit += 1;
      }
      amount = Math.round(amount * 10) / 10; // Round to one decimal place

      return amount + " " + units[currentUnit];
    },
    //This function replaces window.location instead of mongodb.mppw.local in the database URL
    replace_mongo_local(URL) {
      let replaced = URL.replaceAll("mongodb.mppw.local", window.location.hostname);
      let dbName = URL.substr(URL.lastIndexOf("/") + 1)
      return replaced + "?authSource=" + dbName;
    },

    //This function slices the user password into half to generate readonly url link
    generate_read_only_link(URL) {
      //Gets the data between "user:" and "@" in the URL i.e. the password
      let user_password = URL.slice(
        URL.indexOf("user:") + 5,
        URL.lastIndexOf("@")
      );
      //Divides the password into half
      let new_user_password = user_password.slice(0, user_password.length / 2);
      //Replace the original url with half of the password and changes user to user-ro
      return this.replace_mongo_local(
        URL.replaceAll(user_password, new_user_password).replaceAll(
          "user",
          "user-ro"
        )
      );
    },
    onClickReadOnly() {
      this.showReadOnlyUrl = true;
    },
    onClickReadWrite() {
      this.showReadOnlyUrl = false;
    },
  },
  created() {
    return this.refreshArtifact();
  },
};
</script>

<style></style>
