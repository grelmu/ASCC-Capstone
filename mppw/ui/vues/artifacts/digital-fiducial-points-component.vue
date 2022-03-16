<template>
  <div v-if="artifact">
    <json-schema-form-component
      v-model="artifact.local_data"
      :schema="schema"
      :formFooter="{ show: false, cancelBtn: 'Cancel', okBtn: 'Submit' }"
      class="auto-js-form"
    >
    </json-schema-form-component>

    <h5>JSON Value</h5>
    {{ artifact.local_data }}

    <div class="mt-3 text-end">
      <o-button @click="onSaveArtifact()" class="text-end" variant="primary"
        >Save Changes</o-button
      >
    </div>
  </div>
</template>

<script>
const schema = {
  type: "object",
  properties: {
    points: {
      title: "Fiducial Point Coordinates",
      type: "array",
      items: {
        type: "object",
        properties: {
          label: {
            type: "string",
            title: "Feature Label",
          },
          x: {
            type: "number",
            title: "x",
          },
          y: {
            type: "number",
            title: "y",
          },
          z: {
            type: "number",
            title: "z",
          },
        },
      },
    },
    units: {
      type: "string",
      title: "Units",
    },
  },
};

export default {
  components: {
    "json-schema-form-component": JsonSchemaFormComponent,
  },

  data() {
    return {
      artifact: null,
      schema,
    };
  },
  props: {
    opId: String,
    artifactId: String,
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
    refreshArtifact() {
      this.artifact = null;
      return this.apiFetchArtifact(this.artifactId).then((artifact) => {
        this.artifact = artifact;
        this.artifact.local_data = this.artifact.local_data || {};
      });
    },
    onSaveArtifact() {
      return this.apiUpdateArtifact(this.artifact)
        .then(() => {
          return this.refreshArtifact();
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
  },
  created() {
    return this.refreshArtifact();
  },
};
</script>

<style>
.auto-js-form .genFormLabel {
  font-size: 1.25em;
  color: black;
}
.auto-js-form .fieldGroupWrap .fieldGroupWrap_title {
  font-size: 1.5em;
}

.auto-js-form div.arrayOrderList {
  background: none;
}

.auto-js-form p.arrayOrderList_bottomAddBtn {
  text-align: left;
  padding: 10px 10px 0px;
}

.auto-js-form button.bottomAddBtn {
  background: lightgray;
}
</style>