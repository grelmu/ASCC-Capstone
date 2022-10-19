<template>
  <div v-if="artifact">
    <h1>{{ artifact.name || defaultName() }}</h1>

    <details class="card">
      <summary>Artifact</summary>
      <p>{{ artifact }}</p>
    </details>

    <h2>Provenance</h2>

    <!-- Provenance DAG goes here: -->
    <svg></svg>

    <div class="pan-zoom-btn-container">
      <div class="pan-zoom-btn">
        <o-button outlined @click="centerZoom">Center</o-button>
      </div>

      <div class="pan-zoom-btn">
        <o-button outlined @click="resetZoom">Reset Zoom</o-button>
      </div>
    </div>

    <details v-if="provenance" class="card">
      <summary>Provenance</summary>
      <p>
        {{ provenance }}
      </p>
    </details>

  </div>
</template>

<script>
export default {
  data() {
    return {
      artifactId: null,
      artifact: null,
      provenance: null,
      graphElId: null,
      graphWidth: null,
      graphHeight: null
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
        .apiFetchArtifactProvenance(this.artifactId, "ancestors")
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
      let network = { nodes: [], links: [] };

      let nodeIdFor = function (node) {
        return (
          node["artifact_id"] || node["operation_id"] 
        );
      };

      let nodeTitleFor = (node) => {
        if (node["artifact"]) {
          return node["artifact"]["type_urn"].replace("urn:x-mfg:artifact", "");
        } else {
          return (
            node["operation"]["type_urn"].replace("urn:x-mfg:operation", "") +
            (node["name"] != ":default" ? " " + node["name"] : "")
          );
        }
      };

      let nodeTextFor = (node) => {
        if (node["artifact"]) {
          return node["artifact"]["name"] || node["artifact_id"];
        } else {
          return node["operation"]["name"] || node["operation_id"];
        }
      };

      let nodeHrefFor = (node) => {
        if (node["artifact"]) {
          // NOTE that we need a unique parameter to force a reload with our current anchor-based routing
          return this.$router
            .resolve("/artifacts/" + node["artifact_id"])
            .href.replace("#", "?link=" + uuidv4() + "#");
        } else {
          return this.$router.resolve("/operations/" + node["operation_id"])
            .href;
        }
      };

      for (let i = 0; i < this.provenance["nodes"].length; ++i) {
        let node = this.provenance["nodes"][i];
        let networkNode = Object.assign(
          {
            id: nodeIdFor(node),
            title: nodeTitleFor(node),
            text: nodeTextFor(node),
            href: nodeHrefFor(node),
            group: node["artifact_id"] ? 0 : 1,
            highlight: node["artifact_id"] == this.artifact.id,
          },
          node
        );
        network.nodes.push(networkNode);
      }

      for (let i = 0; i < this.provenance["edges"].length; ++i) {
        let edge = this.provenance["edges"][i];
        let networkLink = {
          source: nodeIdFor(edge["from_node"]),
          target: nodeIdFor(edge["to_node"]),
          value: 1,
          edge,
        };
        network.links.push(networkLink);
      }

      // Build DAG structure to pass to dag-module
      // TODO: make this process less wasteful (complexity-wise)
      let parsedLinks = [];
      network.links.forEach(link => {
        let datapoint = {
          id: link.source, 
          parentIds: network.links.filter(
            ln => ln.target == link.source 
          ).map(l => {return l.source})
        }
        parsedLinks.push(datapoint);
      })

      // Collect any nodes with out degree 0
      network.nodes.forEach(n => {
        if (parsedLinks.filter(ln => ln.id == n.id).length == 0) {
          parsedLinks.push(
            {
              id: n.id, parentIds: network.links.filter(ln => ln.target == n.id)
                .map(l => {return l.source})
            }
          )
        }
      })

      // Drop duplicates from parsedLinks:
      let i1 = []; // intermediate array #1 holds unique node IDs
      let i2 = []; // intermediate array #2 holds unique node objects
      parsedLinks.forEach(l => {if (!i1.includes(l.id)) {
        i1.push(l.id); i2.push(l)
      }});

      let dagGraph = Dag(i2, network, {
        nodeGroup: (d) => d.group,
        nodeHighlight: (d) => d.highlight,
        nodeHighlightColor: "orange",
        icons: ["\u{F01A6}", "\u{F072A}"]
      })

      this.graphWidth = dagGraph[0];
      this.graphHeight = dagGraph[1];

      d3.select('svg').call(this.zoom());

    },
    defaultName() {
      return (
        this.artifact["type_urn"].replace("urn:x-mfg:artifact", "") +
        " (" +
        this.artifact["id"] +
        ")"
      );
    },
    zoom() {
      return d3.zoom().on('zoom', this.handleZoom)
    },
    handleZoom(e) {
      d3.selectAll('svg g')
        // Get the first two <g>s, which are the nodes and edges
        .filter(function(d, i) { return i == 0 || i == 1; })
        // apply transformations to the graph
        .attr('transform', e.transform);
    },
    resetZoom() {
      d3.select('svg')
        .transition()
        .call(this.zoom().scaleTo, 1);
    },
    centerZoom () {
      d3.select('svg')
        .transition()
        .call(this.zoom().translateTo, this.graphWidth / 2, this.graphHeight / 2);
    }
  },
  created() {
    this.artifactId = this.$route.params.id;
    this.graphElId = "provenance-" + this.$.uid;
    return this.refreshArtifactAndProvenance();
  },
};
</script>

<style scoped>
details {padding: 5px;}
summary::marker {color: #888888;}
.pan-zoom-btn-container {
  display: flex;
  flex-direction: row;
  justify-content: center;
  align-items: center;
}
.pan-zoom-btn {margin: 5px;}
</style>
