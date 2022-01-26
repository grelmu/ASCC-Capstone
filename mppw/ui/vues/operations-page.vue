<template>
  <div v-if="op">
    <h1>{{ op.name }}</h1>

    <p>{{ op }}</p>

    <h2>Artifacts</h2>
    <div v-for="artifactKind in Object.keys(artifactGraph || {})" :key="artifactKind">
      <h3>{{ artifactKind }}</h3>
      <div v-for="artifact in artifactGraph[artifactKind]" :key="artifact.id">
        {{ artifact }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      opId: null,
      op: null,
      artifactGraph: null,
    };
  },
  methods: {
    fetchOperation(id) {
      return this.$root
        .apiFetch("operations/" + id, { method: "GET" })
        .then((response) => {
          if (response.status == 200) return response.json();
          else return { version: "" };
        })
    },
    fetchArtifact(id) {
      return this.$root
        .apiFetch("artifacts/" + id, { method: "GET" })
        .then((response) => {
          if (response.status == 200) return response.json();
          else return { version: "" };
        })
    },
    fetchArtifactGraph(operation) {
      let fetches = [];
      let graph = {};
      operation["artifact_transform_graph"].forEach((transform) => {

        graph[transform.kind_urn] = []
        let inputs = transform["input_artifacts"] || [];
        let outputs = transform["output_artifacts"] || [];

        (inputs.concat(outputs)).forEach((artifactId) => {
          fetches.push(
            this.fetchArtifact(artifactId)
              .then((artifact) => {
                graph[transform.kind_urn].push(artifact);
              })
          )
        })
      });

      return Promise.all(fetches)
        .then(() => {
          return graph;
        });
    },
  },
  created() {
    this.opId = this.$route.params.id;
    this.fetchOperation(this.opId)
      .then((op) => {
        this.op = op;
        return this.fetchArtifactGraph(op);
      })
      .then((artifactGraph) => {
        this.artifactGraph = artifactGraph;
      });
  },
};
</script>

<style scoped></style>