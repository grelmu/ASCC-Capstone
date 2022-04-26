<template>
  <div v-if="(attachmentNodes || []).length > 0 || attachmentKinds.length > 0">
    <div class="mt-4 row">
      <div class="col-auto">
        <o-button
          @click="onAttachArtifactBegin()"
          class="text-end"
          :disabled="attachmentKinds.length == 0"
          >Attach Artifact</o-button
        >
      </div>
      <div class="col-auto" style="flex: auto"><hr /></div>
    </div>

    <div
      v-for="attachmentNode in attachmentNodes || []"
      :key="attachmentNode['kind_urn']"
    >
      <h3 v-if="attachmentNode['artifacts']" class="mt-4">
        {{ attachmentNode["kind_urn"] }}
      </h3>
      <h3
        v-if="!attachmentNode['artifacts']"
        class="mt-4 text-muted fw-lighter"
      >
        {{ attachmentNode["kind_urn"] }}
      </h3>

      <div
        v-for="artifactNode in attachmentNode['artifacts']"
        :key="artifactNode['artifact_id']"
      >
        <div class="row">
          <div class="ms-4 col">
            <operation-artifact-node
              :projectId="projectId"
              :opId="opId"
              :artifactPath="
                artifactPath.concat([
                  attachmentNode['kind_urn'],
                  artifactNode['artifact_id'],
                ])
              "
              :artifactNode="artifactNode"
              :attachmentKind="attachmentKindFor(attachmentNode['kind_urn'])"
            ></operation-artifact-node>
          </div>
          <div class="col-auto my-auto">
            <o-icon
              :icon="artifactNode['is_input'] ? 'link-off' : 'trash-can'"
              @click="
                onDetachArtifact(
                  attachmentNode['kind_urn'],
                  artifactNode['artifact_id'],
                  artifactNode['is_input']
                )
              "
              style="color: red"
            ></o-icon>
          </div>
        </div>
      </div>
    </div>

    <o-modal v-model:active="isAttachingArtifact">
      <h2>Attach New Artifact</h2>

      <o-field label="Attachment Kind">
        <o-select
          placeholder="Select an attachment kind"
          v-model="newKindUrn"
          @update:modelValue="onAttachmentKindSelected"
        >
          <option
            v-for="kind in attachmentKinds || []"
            :key="kind.kind_urn"
            :value="kind.kind_urn"
          >
            {{ kind.kind_urn }}
          </option>
        </o-select>
        &nbsp;<b>:</b>&nbsp;
        <o-input v-model="newKindKey" placeholder="(optional key)"></o-input>
      </o-field>

      <div v-if="newKind">
        <div class="mt-3 row">
          <div class="col-md-auto">
            <o-radio
              v-model="newAttachType"
              name="name"
              native-value="output"
            ></o-radio>
          </div>
          <div class="col-md-auto">
            <h5>New Artifact</h5>
            <div v-if="newAttachType == 'output'">
              <o-field label="Artifact Type">
                <o-select
                  placeholder="Select an artifact type"
                  v-model="newTypeUrn"
                >
                  <option
                    v-for="artifactType in newKind.types"
                    :key="artifactType['type_urn']"
                    :value="artifactType['type_urn']"
                  >
                    {{ artifactType["type_urn"] }}
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
          </div>
        </div>
        <div class="mt-3 row">
          <div class="col-md-auto">
            <o-radio
              v-model="newAttachType"
              name="name"
              native-value="input"
            ></o-radio>
          </div>
          <div class="col-md-auto">
            <h5>Existing Artifact</h5>
            <div v-if="newAttachType == 'input'">
              <o-field label="Find an operation">
                <o-autocomplete
                  rounded
                  expanded
                  :data="operationsTextQueryResult"
                  field="name"
                  placeholder="Operation Name"
                  icon="text-search"
                  clearable
                  :loading="isTextQueryingOperations"
                  :debounce-typing="500"
                  @typing="onTextQueryOperations"
                  @select="onOperationSelected"
                >
                  <template v-slot:empty>No results found</template>
                  <template v-slot:default="props">
                    {{ props.option.name }}
                  </template>
                </o-autocomplete>
              </o-field>

              <div v-if="selectedOperationCandidates">
                <o-select
                  :placeholder="
                    selectedOperationCandidates.length > 0
                      ? 'Select an artifact'
                      : 'No artifacts of correct types found'
                  "
                  v-model="selectedCandidate"
                >
                  <option
                    v-for="candidate in selectedOperationCandidates || []"
                    :key="candidate.id"
                    :value="candidate"
                  >
                    {{ candidate.name ? candidate.name + " @ " : ""
                    }}{{ candidate.kind_urn }}.{{ candidate.id }}
                  </option>
                </o-select>
              </div>
            </div>
          </div>
        </div>
      </div>

      <o-button @click="onAttachArtifactSubmit()" class="mt-4"
        >Attach new artifact</o-button
      >
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
      newAttachType: "output",

      newTypeUrn: null,
      newName: null,
      newDescription: null,

      isTextQueryingOperations: false,
      operationsTextQuery: null,
      operationsTextQueryResult: null,
      selectedOperation: null,
      selectedOperationCandidates: null,
      selectedCandidate: null,
    };
  },

  props: {
    projectId: String,
    opId: String,
    artifactPath: Array,
    attachmentKinds: Array,
  },

  methods: {
    refreshAttachments() {
      this.attachmentNodes = null;

      console.log(this.attachmentKinds);
      console.log(this.artifactPath);

      return this.$root
        .apiFetchOperationArtifacts(this.opId, {
          parent_artifact_path: this.artifactPath,
        })
        .then((artifactNodes) => {
          // Group into attachment nodes by attachment kind
          let attachmentNodes = {};

          for (let i = 0; i < artifactNodes.length; ++i) {
            let artifactNode = artifactNodes[i];
            let kindUrn = this.kindPathToUrn(artifactNode["kind_path"]);
            let attachmentNode = attachmentNodes[kindUrn];
            if (!attachmentNode) {
              attachmentNodes[kindUrn] = attachmentNode = {
                kind_urn: kindUrn,
                artifacts: [artifactNode],
              };
            }
          }

          this.attachmentNodes = Object.values(attachmentNodes);

          // Add empty attachment nodes for any attachment kinds we're missing
          for (let i = 0; i < this.attachmentKinds.length; ++i) {
            let attachmentKind = this.attachmentKinds[i];
            if (this.findSimilarAttachmentNode(attachmentKind.kind_urn) == null)
              this.attachmentNodes.push({
                kind_urn: attachmentKind.kind_urn,
                artifacts: [],
              });
          }

          // Sort all the attachments
          this.sortAttachments();
        });
    },

    splitKindKey(kindUrn) {
      let splitAt = kindUrn.lastIndexOf(":");
      if (splitAt == 0) splitAt = -1;
      if (splitAt < 0) return [kindUrn, null];
      return [
        kindUrn.substring(0, splitAt),
        kindUrn.substring(splitAt + 1, kindUrn.length),
      ];
    },

    kindPathToUrn(kindPath) {
      return kindPath.length > 0 ? kindPath[kindPath.length - 1] : "";
    },

    sortAttachments() {
      let kindIndices = {};
      for (let i = 0; i < this.attachmentKinds.length; ++i) {
        kindIndices[this.attachmentKinds[i].kind_urn] = i;
      }

      this.attachmentNodes.sort((a, b) => {
        let splitA = this.splitKindKey(a.kind_urn);
        let kindA = splitA[0];
        let keyA = splitA[1];

        let splitB = this.splitKindKey(b.kind_urn);
        let kindB = splitB[0];
        let keyB = splitB[1];

        let aIndex = kindIndices[kindA];
        let bIndex = kindIndices[kindB];

        // Unknown types, just compare full kind urns
        if (aIndex == null && bIndex == null)
          return a.kind_urn.localeCompare(b.kind_urn);
        if (aIndex == null) return 1;
        if (bIndex == null) return -1;

        // Return order based on registered kind urns
        let cmp = aIndex - bIndex;
        if (cmp != 0) return cmp;

        // Return order based on kind key
        return (keyA || "").localeCompare(keyB || "");
      });
    },

    findSimilarAttachmentNode(kindUrn) {
      for (let i = 0; i < this.attachmentNodes.length; ++i) {
        let attachmentKindUrn = this.attachmentNodes[i].kind_urn;
        if (
          attachmentKindUrn == kindUrn ||
          kindUrn.startsWith(attachmentKindUrn + ":")
        )
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
      this.newAttachType = "output";
      this.newKindKey = null;
      this.newTypeUrn = null;
      this.newName = null;
      this.newDescription = null;
      this.isAttachingArtifact = true;

      this.isTextQueryingOperations = false;
      this.operationsTextQuery = null;
      this.operationsTextQueryResult = null;
      this.selectedOperation = null;
      this.selectedOperationCandidates = null;
      this.selectedCandidate = null;
    },
    onAttachmentKindSelected(kindUrn) {
      this.newKindUrn = kindUrn;
      this.newKind = this.findSimilarAttachmentKind(this.newKindUrn);
    },
    onTextQueryOperations(textQuery) {
      if (this.isTextQueryingOperations) return;
      textQuery = textQuery.trim();
      if (this.operationsTextQuery == textQuery) return;
      this.operationsTextQuery = textQuery;

      if (
        this.operationsTextQuery == null ||
        this.operationsTextQuery.length == 0
      ) {
        this.operationsTextQueryResult = null;
        return;
      }

      this.isTextQueryingOperations = true;
      this.operationsTextQuery = textQuery;

      return this.$root
        .apiTextQueryOperations(this.operationsTextQuery, this.projectId)
        .then((result) => {
          this.operationsTextQueryResult = result;
        })
        .finally(() => {
          this.isTextQueryingOperations = false;
        });
    },
    onOperationSelected(selected) {
      this.selectedOperation = selected;
      this.selectedOperationCandidates = null;
      this.selectedCandidate = null;

      return this.$root
        .apiFetchArtifactsLs(this.selectedOperation.id)
        .then((listing) => {
          let typeUrns = this.newKind.types.map(
            (t) => "urn:x-mfg:artifact" + t["type_urn"]
          );
          this.selectedOperationCandidates = listing.filter(
            (c) => typeUrns.indexOf(c.type_urn) >= 0
          );
        });
    },

    onAttachArtifactSubmit() {
      if (this.newAttachType == "output")
        return this.onAttachOutputArtifactSubmit();
      else if (this.newAttachType == "input")
        return this.onAttachInputArtifactSubmit();
    },

    onAttachInputArtifactSubmit() {
      let fullKindUrn =
        this.newKindUrn + (this.newKindKey ? ":" + this.newKindKey : "");

      return this.$root
        .apiAttachArtifact(
          this.opId,
          this.artifactPath,
          fullKindUrn,
          this.selectedCandidate["id"],
          true
        )
        .then(() => {
          return this.refreshAttachments();
        })
        .finally(() => {
          this.isAttachingArtifact = false;
        });
    },

    onAttachOutputArtifactSubmit() {
      let artifact = {
        type_urn: this.newTypeUrn,
        project: this.projectId,
        name: this.newName,
        description: this.newDescription,
      };

      if (artifact["type_urn"].startsWith(":"))
        artifact["type_urn"] = "urn:x-mfg:artifact" + artifact["type_urn"];

      return this.$root
        .apiCreateArtifact(artifact)
        .then((artifact) => {
          let fullKindUrn =
            this.newKindUrn + (this.newKindKey ? ":" + this.newKindKey : "");

          return this.$root
            .apiInitArtifact(artifact["id"], {})
            .then(() => {
              return this.$root.apiAttachArtifact(
                this.opId,
                this.artifactPath,
                fullKindUrn,
                artifact["id"]
              );
            })
            .then(() => {
              return this.refreshAttachments();
            });
        })
        .finally(() => {
          this.isAttachingArtifact = false;
        });
    },
    onDetachArtifact(kindUrn, artifactId, isInput) {
      if (
        !confirm("Are you sure you want to detach a " + kindUrn + " artifact?")
      )
        return;

      return this.$root
        .apiDetachArtifact(
          this.opId,
          this.artifactPath,
          kindUrn,
          artifactId,
          isInput
        )
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

<style scoped></style>
