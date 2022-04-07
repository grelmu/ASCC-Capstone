<template>
  <div>
    <h1>About this deployment</h1>

    <p>Version: {{ version }}</p>
  </div>
</template>

<script>
export default {
  data() {
    return {
      version: "",
    };
  },
  methods: {
    fetchVersion() {
      return this.$root
        .apiFetch("../version", { method: "GET" })
        .then((response) => {
          if (response.status == 200) return response.json();
          else return { version: "" };
        })
        .then((json) => {
          this.version = json.version;
        });
    },
  },
  created() {
    this.fetchVersion();
  },
};
</script>

<style scoped></style>
