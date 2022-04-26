<template>
  <div v-if="artifact">
    <h1>{{ artifact.name || defaultName() }}</h1>

    <p>{{ artifact }}</p>

    <div v-if="provenance">
      <h2>Provenance</h2>
      <p>{{ provenance }}</p>
    </div>

    <div :id="graphElId"></div>
  </div>
</template>

<script>
export default {
  components: {
    // "operation-artifact-node": RemoteVue.asyncComponent(
    //   "vues/operation-artifact-node.vue"
    // ),
  },

  data() {
    return {
      artifactId: null,
      artifact: null,
      provenance: null,
      graphElId: null,
    };
  },

  methods: {
    refreshArtifactAndProvenance() {
      this.artifact = null;
      return this.$root.apiFetchArtifact(this.artifactId).then((artifact) => {
        this.artifact = artifact;
        return this.refreshProvenance();
      });
    },
    refreshProvenance() {
      this.provenance = null;
      return this.$root
        .apiFetchArtifactProvenance(this.artifactId, "ancestors+3")
        .then((provenance) => {
          this.provenance = provenance;
        })
        .then(() => {
          let artifactPromises = {};
          let operationPromises = {};

          for (let node of this.provenance["nodes"]) {
            if (node["artifact_id"] && !artifactPromises[node["artifact_id"]]) {
              artifactPromises[node["artifact_id"]] =
                this.$root.apiFetchArtifact(node["artifact_id"]);
            } else if (
              node["operation_id"] &&
              !operationPromises[node["operation_id"]]
            ) {
              operationPromises[node["operation_id"]] =
                this.$root.apiFetchOperation(node["operation_id"]);
            }
          }

          return Promise.all([
            Promise.all(Object.values(artifactPromises)),
            Promise.all(Object.values(operationPromises)),
          ]);
        })
        .then((allEntities) => {
          let artifacts = {};
          let operations = {};

          allEntities[0].forEach((a) => (artifacts[a["id"]] = a));
          allEntities[1].forEach((o) => (operations[o["id"]] = o));

          for (let node of this.provenance["nodes"]) {
            if (node["artifact_id"]) {
              node["artifact"] = artifacts[node["artifact_id"]];
            } else if (node["operation_id"]) {
              node["operation"] = operations[node["operation_id"]];
            }
          }

          return this.refreshProvenanceChart();
        });
    },
    refreshProvenanceChart() {
      let graphEl = document.getElementById(this.graphElId);
      while (graphEl.children.length > 0)
        graphEl.removeChild(graphEl.children[0]);

      let network = { nodes: [], links: [] };

      let nodeIdFor = function (node) {
        return (
          node["artifact_id"] ||
          node["operation_id"] + node["context_path"] + node["name"]
        );
      };

      let nodeTitleFor = function (node) {
        if (node["artifact"]) {
          return (
            (node["artifact"]["name"] || node["artifact"]["type_urn"]) +
            " (" +
            node["artifact_id"] +
            ")"
          );
        } else {
          return (
            (node["operation"]["name"] || node["operation"]["type_urn"]) +
            node["name"] +
            " (" +
            node["operation_id"] +
            ")"
          );
        }
      };

      for (let i = 0; i < this.provenance["nodes"].length; ++i) {
        let node = this.provenance["nodes"][i];
        let networkNode = Object.assign(
          {
            id: nodeIdFor(node),
            title: nodeTitleFor(node),
            group: node["artifact_id"] ? 0 : 1,
          },
          node
        );
        network.nodes.push(networkNode);
      }

      for (let i = 0; i < this.provenance["edges"].length; ++i) {
        let edge = this.provenance["edges"][i];
        let networkLink = {
          source: nodeIdFor(edge[0]),
          target: nodeIdFor(edge[1]),
          value: 1,
          edge,
        };
        network.links.push(networkLink);
      }

      let graph = ForceGraph(network, {
        nodeId: (d) => d.id,
        nodeGroup: (d) => d.group,
        nodeTitle: (d) => d.title,
        nodeRadius: 30,
        linkStrokeWidth: (l) => Math.sqrt(l.value),
        width: 500,
        height: 600,
      });

      graphEl.appendChild(graph);
    },
    defaultName() {
      return (
        this.artifact["type_urn"].replace("urn:x-mfg:artifact", "") +
        " (" +
        this.artifact["id"] +
        ")"
      );
    },
  },
  created() {
    this.artifactId = this.$route.params.id;
    this.graphElId = "provenance-" + this.$.uid;
    return this.refreshArtifactAndProvenance();
  },
};
</script>

<style scoped></style>
