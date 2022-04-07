<template>
  <div>
    <div v-if="artifact">
      <o-collapse class="card" animation="slide" :open="false">
        <template v-slot:trigger="trigger">
          <div class="card-header" role="button">
            <router-link
              v-if="artifactNode['is_input']"
              :to="'/operations/' + artifactOpParent['id']"
              :title="artifactOpParent['name']"
              target="_blank"
              @click="onClickInputLink"
              class="card-header-icon"
            >
              <o-icon :icon="'link'"></o-icon>
            </router-link>
            <div class="card-header-title">
              <div style="flex-basis: 100%">
                <div v-if="!artifact['name']">
                  <div class="fs-4">
                    {{
                      (artifact["type_urn"] || "invalid").replace(
                        "urn:x-mfg:artifact",
                        ""
                      )
                    }}
                    &nbsp;&nbsp;
                    <a @click="onStartEditMeta" style="cursor: pointer"
                      ><o-icon icon="circle-edit-outline"></o-icon
                    ></a>
                  </div>
                </div>
                <div v-if="artifact['name']">
                  <div class="fs-4">
                    {{ artifact["name"] || "" }}&nbsp;&nbsp;
                    <a @click="onStartEditMeta" style="cursor: pointer"
                      ><o-icon icon="circle-edit-outline"></o-icon
                    ></a>
                  </div>
                  <div class="fs-5">
                    {{
                      (artifact["type_urn"] || "invalid").replace(
                        "urn:x-mfg:artifact",
                        ""
                      )
                    }}
                  </div>
                </div>
              </div>
              <div class="fw-light">{{ artifact["id"] }}</div>
            </div>
            <a class="card-header-icon">
              <o-icon
                :icon="
                  trigger.open
                    ? 'arrow-up-drop-circle'
                    : 'arrow-down-drop-circle'
                "
              ></o-icon>
            </a>
          </div>
        </template>
        <div class="card-content">
          <div class="mb-4" v-if="artifact['description']">
            {{ artifact["description"] || "" }}
          </div>

          <component
            :is="artifactComponentFor(artifact['type_urn'])"
            :opId="opId"
            :artifactKind="artifactKind"
            :artifactId="artifact['id']"
          ></component>

          <operation-attachments-node
            :projectId="projectId"
            :opId="opId"
            :artifactPath="artifactPath"
            :attachmentKinds="(artifactType || {})['child_kinds'] || []"
          ></operation-attachments-node>
        </div>
      </o-collapse>
    </div>

    <div v-if="!artifact">
      <operation-attachments-node
        :projectId="projectId"
        :opId="opId"
        :artifactPath="artifactPath"
        :attachmentKinds="(artifactType || {})['child_kinds'] || []"
      ></operation-attachments-node>
    </div>

    <o-modal v-model:active="isEditingMeta">
      <h2>Edit Artifact Metadata</h2>

      <o-field label="Name">
        <o-input v-model="newName"></o-input>
      </o-field>

      <o-field label="Description">
        <o-input v-model="newDescription"></o-input>
      </o-field>

      <div v-if="isDigitalArtifact()">
        <h3>Spatial Frame</h3>

        <o-field label="Parent Frame Artifact">
          <o-autocomplete
            rounded
            expanded
            v-model="selectedOperationName"
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

        <o-field v-if="selectedOperation || newSpatialFrame.parent_frame">
          <o-select
            placeholder="Select a spatial parent artifact"
            v-model="newSpatialFrame.parent_frame"
          >
            <option
              v-for="candidate in parentFrameCandidates || []"
              :key="candidate.id"
              :value="candidate.id"
            >
              <span v-if="candidate.kind_urn">
                {{ candidate.name ? candidate.name + " @ " : ""
                }}{{ candidate.kind_urn }}.{{ candidate.id }}
              </span>
              <span v-if="!candidate.kind_urn">
                {{ candidate.name || id }} (current) ({{ candidate.id }})
              </span>
            </option>
          </o-select>
        </o-field>

        <o-field label="Translation XYZ">
          <o-input
            type="number"
            step="any"
            v-model="newSpatialFrame['transform']['translation_xyz']['x']"
          ></o-input>
          <o-input
            type="number"
            step="any"
            v-model="newSpatialFrame['transform']['translation_xyz']['y']"
          ></o-input>
          <o-input
            type="number"
            step="any"
            v-model="newSpatialFrame['transform']['translation_xyz']['z']"
          ></o-input>
        </o-field>

        <o-field label="Rotation (Euler) αβγ">
          <o-input
            type="number"
            step="any"
            v-model="newSpatialFrame['transform']['rotation_euler_abg']['a']"
          ></o-input>
          <o-input
            type="number"
            step="any"
            v-model="newSpatialFrame['transform']['rotation_euler_abg']['b']"
          ></o-input>
          <o-input
            type="number"
            step="any"
            v-model="newSpatialFrame['transform']['rotation_euler_abg']['g']"
          ></o-input>
        </o-field>
      </div>

      <o-button
        @click="onSubmitMeta()"
        class="mt-4"
        :disabled="isDigitalArtifact() && parentFrameCandidates == null"
        >Save Changes</o-button
      >
    </o-modal>
  </div>
</template>

<script>
const componentMap = {
  "urn:x-mfg:artifact:digital:text": "digital-text-component",
  "urn:x-mfg:artifact:digital:file": "digital-file-component",
  "urn:x-mfg:artifact:digital:file-bucket": "digital-file-bucket-component",
  "urn:x-mfg:artifact:digital:fiducial-points":
    "digital-fiducial-points-component",
  default: "default-component",
};

export default {
  components: {
    "operation-attachments-node": RemoteVue.asyncComponent(
      "vues/operation-attachments-node.vue"
    ),
    // Artifact components
    "digital-text-component": RemoteVue.asyncComponent(
      "vues/artifacts/digital-text-component.vue"
    ),
    "digital-file-component": RemoteVue.asyncComponent(
      "vues/artifacts/digital-file-component.vue"
    ),
    "digital-file-bucket-component": RemoteVue.asyncComponent(
      "vues/artifacts/digital-file-bucket-component.vue"
    ),
    "digital-fiducial-points-component": RemoteVue.asyncComponent(
      "vues/artifacts/digital-fiducial-points-component.vue"
    ),
    "default-component": RemoteVue.asyncComponent(
      "vues/artifacts/default-component.vue"
    ),
  },

  data() {
    return {
      artifactId: null,
      artifact: null,
      artifactOpParent: null,
      artifactType: null,
      artifactKind: null,
      isCollapsed: true,

      isEditingMeta: false,
      newName: null,
      newDescription: null,

      isTextQueryingOperations: false,
      operationsTextQuery: null,
      operationsTextQueryResult: null,
      selectedOperation: null,
      selectedOperationName: null,

      newSpatialFrame: null,
      parentFrameCandidates: null,
    };
  },

  props: {
    projectId: String,
    opId: String,
    artifactPath: Array,
    artifactNode: Object,
    attachmentKind: Object,
  },

  methods: {
    refreshArtifact() {
      this.artifact = null;
      this.artifactOpParent = null;
      if (this.artifactId == null) {
        this.artifactType = this.attachmentKind["types"][0];
        return Promise.resolve(null);
      }

      return this.$root
        .apiFetchArtifact(this.artifactId)
        .then((artifact) => {
          if (!this.artifactNode["is_input"]) return artifact;
          return this.$root
            .apiFetchArtifactOperationParent(artifact["id"])
            .then((opParent) => {
              this.artifactOpParent = opParent;
              return artifact;
            });
        })
        .then((artifact) => {
          this.artifact = artifact;
          this.artifactType = this.findSimilarArtifactType(
            this.artifact["type_urn"].replace("urn:x-mfg:artifact", "")
          );
        });
    },
    refreshParentFrameCandidates() {
      let currentFramePromise = (
        this.newSpatialFrame.parent_frame
          ? this.$root.apiFetchArtifact(this.newSpatialFrame.parent_frame)
          : Promise.resolve(null)
      ).then((artifact) => {
        return artifact != null
          ? [{ id: artifact.id, name: artifact.name, kind_urn: null }]
          : [];
      });

      let candidatesPromise =
        this.selectedOperation != null
          ? this.$root.apiFetchArtifactFrameCandidates(
              this.selectedOperation.id,
              this.artifactPath
            )
          : Promise.resolve([]);

      return Promise.all([currentFramePromise, candidatesPromise]).then(
        (allCandidates) => {
          this.parentFrameCandidates = allCandidates[0].concat(
            allCandidates[1]
          );
          this.sortParentFrameCandidates();
        }
      );
    },
    sortParentFrameCandidates() {
      this.parentFrameCandidates.sort((a, b) => {
        if (a.kind_urn == null) return -1;
        if (b.kind_urn == null) return 1;

        if (a.name != null && b.name == null) return -1;
        if (a.name == null && b.name != null) return 1;

        return a.kind_urn.localeCompare(b.kind_urn);
      });
    },
    isDigitalArtifact() {
      return (
        this.artifact &&
        this.artifact.type_urn.startsWith("urn:x-mfg:artifact:digital:")
      );
    },
    findSimilarArtifactType(typeUrn) {
      let artifactTypes = this.attachmentKind.types;

      for (let i = 0; i < artifactTypes.length; ++i) {
        let nextTypeUrn = artifactTypes[i]["type_urn"];
        if (nextTypeUrn == typeUrn || typeUrn.startsWith(nextTypeUrn + ":"))
          return artifactTypes[i];
      }

      return null;
    },
    artifactComponentFor(type_urn) {
      if (type_urn) {
        for (let component_type_urn in componentMap) {
          if (
            type_urn == component_type_urn ||
            type_urn.startsWith(component_type_urn + ":")
          ) {
            return componentMap[component_type_urn];
          }
        }
      }
      return componentMap["default"];
    },
    onClickInputLink(event) {
      event.stopPropagation();
      event.target.closest("a").click();
    },
    onStartEditMeta() {
      this.newName = this.artifact["name"];
      this.newDescription = this.artifact["description"];
      this.isEditingMeta = true;

      this.isTextQueryingOperations = false;
      this.operationsTextQuery = null;
      this.operationsTextQueryResult = null;
      this.selectedOperation = null;

      event.stopPropagation();

      if (!this.isDigitalArtifact()) return;

      this.newSpatialFrame = Object.assign(
        {
          parent_frame: null,
        },
        this.artifact["spatial_frame"] || {}
      );

      this.newSpatialFrame.transform = Object.assign(
        {
          translation_xyz: {},
          rotation_euler_abg: {},
        },
        (this.artifact["spatial_frame"] || {}).transform
      );

      if (this.newSpatialFrame["parent_frame"] == null) return;

      return this.$root
        .apiFetchArtifactOperationParent(this.newSpatialFrame["parent_frame"])
        .then((parent) => {
          if (parent != null) {
            this.operationsTextQueryResult = [parent];
            this.selectedOperation = parent;
            this.selectedOperationName = parent["name"];
          }

          return this.refreshParentFrameCandidates();
        });
    },
    onTextQueryOperations(textQuery) {
      if (this.isTextQueryingOperations) return;
      textQuery = textQuery.trim();
      if (this.operationsTextQuery == textQuery) return;
      this.operationsTextQuery = textQuery;

      let emptyQuery =
        this.operationsTextQuery == null ||
        this.operationsTextQuery.length == 0;

      let queryPromise = this.$root.apiFetchOperation(this.opId);

      queryPromise = (
        !emptyQuery
          ? Promise.all([
              queryPromise,
              this.$root.apiTextQueryOperations(
                this.operationsTextQuery,
                this.projectId
              ),
            ])
          : Promise.all([queryPromise, Promise.resolve([])])
      ).then((results) => {
        return [results[0]].concat(results[1]);
      });

      this.isTextQueryingOperations = true;
      this.operationsTextQuery = textQuery;

      return queryPromise
        .then((result) => {
          this.operationsTextQueryResult = result;
        })
        .finally(() => {
          this.isTextQueryingOperations = false;
        });
    },
    onOperationSelected(selected) {
      this.selectedOperation = selected;
      this.newSpatialFrame.parent_frame = null;
      return this.refreshParentFrameCandidates();
    },
    onSubmitMeta() {
      let changes = [];
      changes.push({ op: "replace", path: "name", value: this.newName });
      changes.push({
        op: "replace",
        path: "description",
        value: this.newDescription,
      });

      if (this.isDigitalArtifact()) {
        for (let k in this.newSpatialFrame.transform.translation_xyz)
          this.newSpatialFrame.transform.translation_xyz[k] = Number.parseFloat(
            this.newSpatialFrame.transform.translation_xyz[k]
          );

        for (let k in this.newSpatialFrame.transform.rotation_euler_abg)
          this.newSpatialFrame.transform.rotation_euler_abg[k] =
            Number.parseFloat(
              this.newSpatialFrame.transform.rotation_euler_abg[k]
            );

        changes.push({
          op: "replace",
          path: "spatial_frame",
          value: this.newSpatialFrame,
        });
      }

      return this.$root
        .apiPatchArtifact(this.artifact.id, changes)
        .finally(() => {
          this.isEditingMeta = false;
          return this.refreshArtifact();
        });
    },
  },
  created() {
    this.artifactId = this.artifactNode["artifact_id"];
    if (this.artifactPath.length > 1)
      this.artifactKind = this.artifactPath[this.artifactPath.length - 2];
    return this.refreshArtifact();
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
