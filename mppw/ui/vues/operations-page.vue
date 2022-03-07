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
      return this.apiFetchArtifactGraph(this.op)
        .then((artifactGraph) => {
          this.artifactGraph = artifactGraph;
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

<style scoped></style>