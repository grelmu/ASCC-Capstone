<template>
  <div v-if="op">
    <h1>{{ op.name }}</h1>

    <p>{{ op }}</p>
    
    <div class="mt-3 text-end">
      <o-button @click="onAttachArtifactBegin()" class="text-end">Attach new artifact</o-button>
    </div>

    <o-modal v-model:active="isAttachingArtifact">

      <h2>Attach New Artifact</h2>

      <o-field label="Attachment kind">      
        <o-select placeholder="Select an attachment kind" v-model="newAttachment.kind_urn" @update:modelValue="onAttachmentKindSelected">
          <option
            v-for="kind in (attachmentKinds || [])"
            :key="kind.kind_urn"
            :value="kind.kind_urn"
          >
            {{ kind.kind_urn }}
          </option>
        </o-select>
      </o-field>

      <o-field label="Artifact type">
        <div v-if="newAttachmentArtifactTypes">
          <o-select placeholder="Select an artifact type" v-model="newAttachment.new_output_artifacts[0].type_urn" @update:modelValue="onArtifactTypeSelected">
            <option
              v-for="type_urn in newAttachmentArtifactTypes"
              :key="type_urn"
              :value="type_urn"
            >
              {{ type_urn }}
            </option>
          </o-select>
        </div>
      </o-field>

      <o-button @click="onAttachArtifactSubmit()">Attach new artifact</o-button>

    </o-modal>

    <h2>Artifacts</h2>

    <div v-for="artifactKind in Object.keys(artifactGraph || {})" :key="artifactKind">

      <h3>{{ artifactKind }}</h3>
    
      <o-collapse class="card" animation="slide" v-for="(artifact, index) of artifactGraph[artifactKind]" :key="index" :open="artifactOpenIndexes[artifactKind] == index" @open="artifactOpenIndexes[artifactKind] = index">
        <template v-slot:trigger="trigger">
          <div class="card-header" role="button">
            <div class="card-header-title">
              <div class="fs-4" style="flex-basis: 100%">{{ (artifact["type_urn"] || "invalid").replace("urn:x-mfg:artifact", "") }}</div>
              <div class="fw-light" >{{ artifact["id"] }}</div>
            </div>
            <a class="card-header-icon">
              <o-icon :icon="trigger.open ? 'arrow-up-drop-circle' : 'arrow-down-drop-circle'"> </o-icon>
              <o-icon :icon="'trash-can'" @click="onDetachArtifact(artifactKind, artifact['_id'])" style="color: red;"></o-icon>
            </a>
          </div>
        </template>
        <div class="card-content">
          <component :is="artifactComponentFor(artifact['type_urn'])" :opId="opId" :artifactKind="artifactKind" :artifactId="artifact['id']"></component>
        </div>
      </o-collapse>

    </div>
  </div>
</template>

<script>

const componentMap = {
  "urn:x-mfg:artifact:digital:file": "digital-file-component",
  "urn:x-mfg:artifact:digital:file-bucket": "digital-file-bucket-component",
  "default": "default-component",
}

export default {

  components: {
    "digital-file-component": RemoteVue.asyncComponent("vues/artifacts/digital-file-component.vue"),
    "digital-file-bucket-component": RemoteVue.asyncComponent("vues/artifacts/digital-file-bucket-component.vue"),
    "default-component": RemoteVue.asyncComponent("vues/artifacts/default-component.vue"),
  },

  data() {
    return {
      
      opId: null,
      op: null,
      artifactGraph: null,
      artifactOpenIndexes: null,
      
      attachmentKinds: null,

      isAttachingArtifact: false,
      newAttachment: {},
      newAttachmentArtifactTypes: null,
    };
  },

  methods: {
    apiFetchOperation(id) {
      return this.$root
        .apiFetch("operations/" + id, { method: "GET" })
        .then((response) => {
          if (response.status == 200) return response.json();
          else return { version: "" };
        })
    },
    apiFetchArtifact(id) {
      return this.$root
        .apiFetch("artifacts/" + id, { method: "GET" })
        .then((response) => {
          if (response.status == 200) return response.json();
          else return { version: "" };
        })
    },
    apiFetchArtifactGraph(operation) {
      let fetches = [];
      let graph = {};
      operation["artifact_transform_graph"].forEach((transform) => {

        graph[transform.kind_urn] = []
        let inputs = transform["input_artifacts"] || [];
        let outputs = transform["output_artifacts"] || [];

        (inputs.concat(outputs)).forEach((artifactId) => {
          fetches.push(
            this.apiFetchArtifact(artifactId)
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
    apiFetchAttachmentKinds(type_urn) {
      return this.$root.apiFetch("operation-services/" + type_urn.replace("urn:x-mfg:operation:", "") + "/attachment-kinds", {
        method: "GET",
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.$root.throwApiResponseError(
          response,
          "Unknown response when querying for serviced operation attachment kinds"
        );
      });
    },
    apiAttachArtifact(attachment) {
      
      for (let i = 0; i < (attachment.new_output_artifacts || []).length; ++i) {
        let new_output_artifact = attachment.new_output_artifacts[i];
        if (new_output_artifact.type_urn.startsWith(":")) {
          new_output_artifact.type_urn = "urn:x-mfg:artifact" + new_output_artifact.type_urn;
        }
      }

      return this.$root.apiFetch("operations/" + this.op.id + "/artifacts/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(attachment),
      }).then((response) => {
        if (response.status == 201) return response.json();
        this.$root.throwApiResponseError(
          response,
          "Unknown response when creating attachment"
        );
      });
    },
    apiDetachArtifact(attachment) {

      return this.$root.apiFetch("operations/" + this.op.id + "/artifacts/, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(attachment),
      }).then((response) => {
        if (response.status == 201) return response.json();
        this.$root.throwApiResponseError(
          response,
          "Unknown response when creating attachment"
        );
      });
    },
    refreshOperation() {
      this.op = null;
      return this.apiFetchOperation(this.opId)
        .then((op) => {
          this.op = op;
          return this.refreshArtifactGraph();
        });
    },
    refreshArtifactGraph() {
      this.artifactGraph = null;
      this.artifactOpenIndexes = null;
      return this.apiFetchArtifactGraph(this.op)
        .then((artifactGraph) => {
          this.artifactGraph = artifactGraph;
          this.artifactOpenIndexes = {};
        })
    },
    refreshAttachmentKinds() {
      this.attachmentKinds = null;
      return this.apiFetchAttachmentKinds(this.op.type_urn)
        .then((kinds) => {
          this.attachmentKinds = kinds;
        });
    },
    onAttachArtifactBegin() {
      this.newAttachment = {
        new_output_artifacts: [{
          "project": this.op.project,
        }]
      }
      this.newAttachmentArtifactTypes = null;
      this.isAttachingArtifact = true;
    },
    onAttachmentKindSelected(kind_urn) {
      this.newAttachment.kind_urn = kind_urn
      for (let i = 0; i < this.attachmentKinds.length; ++i) {
        if (this.attachmentKinds[i].kind_urn == this.newAttachment.kind_urn) {
          this.newAttachmentArtifactTypes = this.attachmentKinds[i].artifact_type_urns;
          break;
        }
      }
    },
    onArtifactTypeSelected(type_urn) {
      this.newAttachment.new_output_artifacts[0].type_urn = type_urn
    },
    onAttachArtifactSubmit() {
      return this.apiAttachArtifact(this.newAttachment)
        .then(() => {
          return this.refreshOperation();
        })
        .finally(() => {
          this.isAttachingArtifact = false;
        });
    },
    onDetachArtifact(kindUrn, artifactId) {
      if (!confirm("Are you sure you want to detach a " + kindUrn + " artifact?")) return;
      return this.detach
    },
    artifactComponentFor(type_urn) {
      if (type_urn) {
        for (let component_type_urn in componentMap) {
          if (type_urn == component_type_urn || type_urn.startsWith(component_type_urn + ":")) {
            return componentMap[component_type_urn];
          }
        }
      }
      return componentMap["default"]
    },
  },
  created() {
    this.opId = this.$route.params.id;
    this.refreshOperation()
      .then(() => {
        return this.refreshAttachmentKinds();
      });
  },
};
</script>

<style scoped>

  .card {
    max-width: 100%;
    position: relative;
  }
  .card-header {
    align-items: stretch;
    display: flex;
  }
  .card-header-title {
    align-items: center;
    display: flex;
    flex-grow: 1;
    padding: 0.75rem;
    margin: 0;
  }
  .card-header-icon {
    align-items: center;
    cursor: pointer;
    display: flex;
    padding: 0.75rem;
    justify-content: center;
  }
  .card-content {
    padding: 1.5rem;
    width: 100%;
  }

</style>