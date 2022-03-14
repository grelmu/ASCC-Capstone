<template>
  <div>
    <div v-if="artifact">
      <o-collapse class="card" animation="slide" :open="false">
        <template v-slot:trigger="trigger">
          <div class="card-header" role="button">
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

        <o-field label="Parent Frame">
          <o-input v-model="newSpatialFrame['parent_frame']"></o-input>
        </o-field>

        <o-field label="Translation XYZ">
          <o-input
            type="number"
            v-model="newSpatialFrame['transform']['translation_xyz']['x']"
          ></o-input>
          <o-input
            type="number"
            v-model="newSpatialFrame['transform']['translation_xyz']['y']"
          ></o-input>
          <o-input
            type="number"
            v-model="newSpatialFrame['transform']['translation_xyz']['z']"
          ></o-input>
        </o-field>

        <o-field label="Rotation (Euler) αβγ">
          <o-input
            type="number"
            v-model="newSpatialFrame['transform']['rotation_euler_abg']['a']"
          ></o-input>
          <o-input
            type="number"
            v-model="newSpatialFrame['transform']['rotation_euler_abg']['b']"
          ></o-input>
          <o-input
            type="number"
            v-model="newSpatialFrame['transform']['rotation_euler_abg']['g']"
          ></o-input>
        </o-field>
      </div>

      <o-button @click="onSubmitMeta()" class="mt-4">Save Changes</o-button>
    </o-modal>
  </div>
</template>

<script>
const componentMap = {
  "urn:x-mfg:artifact:digital:text": "digital-text-component",
  "urn:x-mfg:artifact:digital:file": "digital-file-component",
  "urn:x-mfg:artifact:digital:file-bucket": "digital-file-bucket-component",
  "urn:x-mfg:artifact:digital:fiducial-points": "digital-fiducial-points-component",
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
      artifact: null,
      artifactType: null,
      artifactKind: null,
      isCollapsed: true,

      isEditingMeta: false,
      newName: null,
      newDescription: null,
      newSpatialFrame: null,
    };
  },

  props: {
    projectId: String,
    opId: String,
    artifactPath: Array,
    artifactId: String,
    attachmentKind: Object,
  },

  methods: {
    apiFetchArtifact(id) {
      return this.$root
        .apiFetch("artifacts/" + id, { method: "GET" })
        .then((response) => {
          if (response.status == 200) return response.json();
          else return { version: "" };
        });
    },
    apiUpdateArtifact(artifact) {
      return this.$root
        .apiFetch("artifacts/" + artifact["id"], {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(artifact),
        })
        .then((response) => {
          if (response.status == 200) return response.json();
          this.$root.throwApiResponseError(
            response,
            "Unknown response when updating artifact"
          );
        });
    },
    refreshArtifact() {
      this.artifact = null;
      if (this.artifactId == null) {
        this.artifactType = this.attachmentKind["types"][0];
        return Promise.resolve(null);
      }

      return this.apiFetchArtifact(this.artifactId).then((artifact) => {
        this.artifact = artifact;
        this.artifactType = this.findSimilarArtifactType(
          this.artifact["type_urn"].replace("urn:x-mfg:artifact", "")
        );
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
    onStartEditMeta() {
      this.newName = this.artifact["name"];
      this.newDescription = this.artifact["description"];
      if (this.isDigitalArtifact()) {
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
      }
      this.isEditingMeta = true;
      event.stopPropagation();
      return false;
    },
    onSubmitMeta() {
      this.artifact.name = this.newName;
      this.artifact.description = this.newDescription;
      if (this.isDigitalArtifact()) {

        for (let k in this.newSpatialFrame.transform.translation_xyz)
          this.newSpatialFrame.transform.translation_xyz[k] =
            Number.parseFloat(this.newSpatialFrame.transform.translation_xyz[k]);
        for (let k in this.newSpatialFrame.transform.rotation_euler_abg)
          this.newSpatialFrame.transform.rotation_euler_abg[k] =
            Number.parseFloat(this.newSpatialFrame.transform.rotation_euler_abg[k]);
        
        this.artifact.spatial_frame = this.newSpatialFrame;
      }

      return this.apiUpdateArtifact(this.artifact).finally(() => {
        this.isEditingMeta = false;
        return this.refreshArtifact();
      });
    },
  },
  created() {
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