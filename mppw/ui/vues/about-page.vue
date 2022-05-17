<template>
  <div>
    <h1>MPPW Deployment</h1>

    <h2>Version: {{ version ? version : "(unknown)" }}</h2>

    <div
      v-if="releaseNotesHtml"
      v-html="releaseNotesHtml"
      class="mt-5 about-page-markdown"
    ></div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      version: null,
      releaseNotes: null,
      releaseNotesHtml: null,
    };
  },
  methods: {
    fetchVersion() {
      return this.$root
        .apiFetch("../version?with_release_notes=True", { method: "GET" })
        .then((response) => {
          if (response.status == 200) return response.json();
          else return {};
        })
        .then((json) => {
          this.version = json["version"];
          this.releaseNotes = json["release_notes"];
          this.releaseNotesHtml = window["markdownit"]().render(
            this.releaseNotes
          );
        });
    },
  },
  created() {
    this.fetchVersion();
  },
};
</script>

<style>
.about-page-markdown h1 {
  font-size: 1.5em;
}
</style>
