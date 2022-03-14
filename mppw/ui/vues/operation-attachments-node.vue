<template>

  <div v-if="(attachmentNodes || []).length > 0 || attachmentKinds.length > 0">
    <div class="mt-4 row">
      <div class="col-auto">
        <o-button @click="onAttachArtifactBegin()" class="text-end" :disabled="attachmentKinds.length == 0"
          >Attach Artifact</o-button>
      </div>
      <div class="col-auto" style="flex: auto;"><hr /></div>
    </div>

    <div
      v-for="attachmentNode in (attachmentNodes || [])"
      :key="attachmentNode['kind_urn']"
    >
      <h3 v-if="attachmentNode['artifacts']" class="mt-4">{{ attachmentNode["kind_urn"] }}</h3>
      <h3 v-if="!attachmentNode['artifacts']" class="mt-4 text-muted fw-lighter">{{ attachmentNode["kind_urn"] }}</h3>

      <div
        v-for="artifactNode in attachmentNode['artifacts']"
        :key="artifactNode['artifact_id']"
      >
        <div class="row">

          <div class="ms-4 col">

            <operation-artifact-node
              :projectId="projectId"
              :opId="opId"
              :artifactPath="artifactPath.concat([attachmentNode['kind_urn'], artifactNode['artifact_id']])"
              :artifactId="artifactNode['artifact_id']"
              :attachmentKind="attachmentKindFor(attachmentNode['kind_urn'])"
            ></operation-artifact-node>

          </div>
          <div class="col-auto my-auto">
              <o-icon
                :icon="'trash-can'"
                @click="onDetachArtifact(attachmentNode['kind_urn'], artifactNode['artifact_id'])"
                style="color: red"
              ></o-icon>
          </div>
        </div>
      </div>
    </div>

    <o-modal v-model:active="isAttachingArtifact">

      <h2>Attach New Artifact</h2>

      <o-field label="Attachment Kind">      
        <o-select placeholder="Select an attachment kind" v-model="newKindUrn" @update:modelValue="onAttachmentKindSelected">
          <option
            v-for="kind in (attachmentKinds || [])"
            :key="kind.kind_urn"
            :value="kind.kind_urn"
          >
            {{ kind.kind_urn }}
          </option>
        </o-select>
      </o-field>

      <div v-if="newKind">
        <o-field label="Artifact Type">
            <o-select placeholder="Select an artifact type" v-model="newTypeUrn">
              <option
                v-for="artifactType in newKind.types"
                :key="artifactType['type_urn']"
                :value="artifactType['type_urn']"
              >
                {{ artifactType['type_urn'] }}
              </option>
            </o-select>
        </o-field>

        <o-field label="Name">
          <o-input v-model="newName"></o-input>
        </o-field>

        <o-field label="Description">
          <o-input v-model="newDescription"></o-input>
        </o-field>

      </div>

      <o-button @click="onAttachArtifactSubmit()" class="mt-4">Attach new artifact</o-button>

    </o-modal>

  </div>
</template>

<script>
export default {
  components: {
    "operation-artifact-node": RemoteVue.asyncComponent(
      "vues/operation-artifact-node.vue"
    ),
  },

  data() {
    return {

      attachmentNodes: null,

      isAttachingArtifact: false,
      newKindUrn: null,
      newKind: null,
      newTypeUrn: null,
      newName: null,
      newDescription: null,
    };
  },

  props: {
    projectId: String,
    opId: String,
    artifactPath: Array,
    attachmentKinds: Array,
  },

  methods: {
    
    apiCreateArtifact(artifact) {
      return this.$root.apiFetch("artifacts/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(artifact),
      }).then((response) => {
        if (response.status == 201) return response.json();
        this.$root.throwApiResponseError(
          response,
          "Unknown response when creating artifact"
        );
      });
    },

    apiInitArtifact(artifactId, args) {
      return this.$root.apiFetch("artifacts/" + artifactId + "/services/artifact/init", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(args || {}),
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.$root.throwApiResponseError(
          response,
          "Unknown response when initializing artifact"
        );
      });
    },

    apiFetchAttachedArtifacts(opId, artifactPath) {
      return this.$root.apiFetch("operations/" + opId + "/artifacts?artifact_path=" + encodeURIComponent(artifactPath.join(".")), {
        method: "GET",
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.$root.throwApiResponseError(
          response,
          "Unknown response when querying attached artifact"
        );
      });
    },

    apiAttachArtifact(opId, artifactPath, kindUrn, artifactId, isInput) {
      
      let attachment = {
        kind_urn: kindUrn,
        artifact_id: artifactId,
        is_input: isInput || false,
        artifact_path: artifactPath,
      }

      return this.$root.apiFetch("operations/" + opId + "/artifacts/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(attachment),
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.$root.throwApiResponseError(
          response,
          "Unknown response when creating attachment"
        );
      });
    },
    apiDetachArtifact(opId, artifactPath, kindUrn, artifactId) {
      
      let attachment = {
        kind_urn: kindUrn,
        artifact_id: artifactId,
        artifact_path: artifactPath,
      }

      return this.$root.apiFetch("operations/" + opId + "/artifacts/", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(attachment),
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.$root.throwApiResponseError(
          response,
          "Unknown response when removing attachment"
        );
      });
    },

    refreshAttachments() {
      
      this.attachmentNodes = null;
      
      return this.apiFetchAttachedArtifacts(this.opId, this.artifactPath).then(
        (artifactNode) => {
          this.attachmentNodes = artifactNode['attachments'];
          for (let i = 0; i < this.attachmentKinds.length; ++i) {
            let attachmentKind = this.attachmentKinds[i];
            if (this.findSimilarAttachmentNode(attachmentKind.kind_urn) == null)
              this.attachmentNodes.push({ kind_urn: attachmentKind.kind_urn, attachments: [] });
          }

          this.sortAttachments();
        }
      );
    },

    sortAttachments() {
      
      let kindIndices = {};
      for (let i = 0; i < this.attachmentKinds.length; ++i) {
        kindIndices[this.attachmentKinds[i].kind_urn] = i;
      }

      this.attachmentNodes.sort((a, b) => {
        let aIndex = kindIndices[a.kind_urn];
        let bIndex = kindIndices[b.kind_urn];

        if (aIndex == null && bIndex == null) return a.kind_urn.localeCompare(b.kind_urn);
        if (aIndex == null) return 1;
        if (bIndex == null) return -1;

        return aIndex - bIndex;
      });
    },

    findSimilarAttachmentNode(kindUrn) {
      for (let i = 0; i < this.attachmentNodes.length; ++i) {
        let nextKindUrn = this.attachmentNodes[i]["kind_urn"];
        if (nextKindUrn == kindUrn || kindUrn.startsWith(nextKindUrn + ":"))
          return this.attachmentNodes[i];
      }
      return null;
    },

    findSimilarAttachmentKind(kindUrn) {
      for (let i = 0; i < this.attachmentKinds.length; ++i) {
        let nextKindUrn = this.attachmentKinds[i]["kind_urn"];
        if (nextKindUrn == kindUrn || kindUrn.startsWith(nextKindUrn + ":"))
          return this.attachmentKinds[i];
      }
      return null;
    },

    attachmentKindFor(kindUrn) {
      let existing = this.findSimilarAttachmentKind(kindUrn);
      if (existing != null) return existing;

      return { kind_urn: kindUrn, types: [] };
    },

    onAttachArtifactBegin() {
      this.newKindUrn = null;
      this.newKind = null;
      this.newTypeUrn = null;
      this.newName = null;
      this.newDescription = null;
      this.isAttachingArtifact = true;
    },
    onAttachmentKindSelected(kindUrn) {
      this.newKindUrn = kindUrn;
      this.newKind = this.findSimilarAttachmentKind(this.newKindUrn);
      console.log(this.newKind);
    },
    onAttachArtifactSubmit() {

      let artifact = {
        type_urn: this.newTypeUrn,
        project: this.projectId,
        name: this.newName,
        description: this.newDescription,
      }

      if (artifact['type_urn'].startsWith(":")) artifact['type_urn'] = "urn:x-mfg:artifact" + artifact['type_urn'];

      return this.apiCreateArtifact(artifact)
        .then((artifact) => {

          return this.apiInitArtifact(artifact['id'], {})
            .then(() => {
              return this.apiAttachArtifact(this.opId, this.artifactPath, this.newKindUrn, artifact['id']);
            })
            .then(() => {
              return this.refreshAttachments();
            });
        })
        .finally(() => {
          this.isAttachingArtifact = false;
        });
    },
    onDetachArtifact(kindUrn, artifactId) {
      if (!confirm("Are you sure you want to detach a " + kindUrn + " artifact?")) return;

      return this.apiDetachArtifact(this.opId, this.artifactPath, kindUrn, artifactId)
        .finally(() => {
          this.refreshAttachments();
        });
    },
  },
  created() {
    return this.refreshAttachments();
  },
};
</script>

<style scoped>
</style>