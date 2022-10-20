<template>
  <div v-if="artifact">
    <o-tabs
      vertical
      type="boxed"
      v-model="activeTab"
      @update:modelValue="onTabChange"
      contentClass="digital-document-content"
    >
      <o-tab-item value="json" label="JSON">
        <o-input
          type="textarea"
          v-model="textJson"
          @change="onTextJsonChange"
          style="height: 15em; font-family: monospace;"
        ></o-input>
      </o-tab-item>

      <o-tab-item v-if="isFrameDocumentArtifact()" value="csv" label="CSV">
        <o-input
          type="textarea"
          v-model="textCsv"
          @change="onTextCsvChange"
          style="height: 15em; font-family: monospace;"
        ></o-input>
      </o-tab-item>

      <o-tab-item
        v-if="schema"
        value="editor"
        label="Editor"
        :disabled="editorDisabled"
      >
        <json-schema-form-component
          v-model="editorJson"
          :schema="schema"
          :formFooter="{ show: false, cancelBtn: 'Cancel', okBtn: 'Submit' }"
          class="auto-js-form"
          @change="onEditorJsonChange"
        >
        </json-schema-form-component>
      </o-tab-item>

      <o-tab-item
        v-if="isFrameDocumentArtifact()"
        value="explorer"
        label="Explorer"
        :disabled="explorerDisabled || (explorerFrame || []).length == 0"
      >
        <div
          :id="'pivottable-' + $.uid"
          style="background-color: snow; margin-bottom: 1em"
        ></div>
        <o-button
          @click="onClickFullscreen()"
          class="text-end"
          variant="info"
          rounded
          >Fullscreen</o-button
        >
      </o-tab-item>

      <o-tab-item value="padding" label="" :disabled="true"></o-tab-item>
    </o-tabs>

    <div class="mt-3 text-end">
      <o-button
        @click="onSaveArtifact()"
        class="text-end"
        variant="primary"
        :disabled="!isSaveAllowed()"
        >Save Changes</o-button
      >
    </div>
  </div>
</template>

<script>
export default {
  components: {
    "json-schema-form-component": JsonSchemaFormComponent,
  },
  data() {
    return {
      artifact: null,
      schema: null,
      activeTab: null,

      dirty: false,

      editorJson: null,
      editorJsonTouched: false,
      editorDisabled: false,

      textJson: null,
      textJsonTouched: false,

      textCsv: null,
      textCsvTouched: false,

      explorerFrame: null,
      explorerDisabled: false,
      isExploringFrame: false,
    };
  },
  props: {
    opId: String,
    artifactId: String,
  },
  methods: {
    refreshArtifact() {
      this.artifact = null;
      return this.$root.apiFetchArtifact(this.artifactId).then((artifact) => {
        return this.$root
          .apiFetchDigitalArtifactJsonSchema(this.artifactId)
          .then((schema) => {
            this.artifact = artifact;
            this.schema = schema;

            const data = this.artifact.local_data;
            let document = null;
            let frame = null;

            if (this.isFrameDocumentArtifact()) {
              document = this.artifact.local_data
                ? this.artifact.local_data.document
                : {};
              frame = this.artifact.local_data
                ? this.artifact.local_data.frame
                : [];
            } else {
              document = this.artifact.local_data || {};
            }

            this.editorJson = document;
            this.editorTouched = false;
            this.editorDisabled = false;

            this.textJson = JSON.stringify(document, null, 2);
            this.textTouched = false;

            if (this.isFrameDocumentArtifact()) {
              this.explorerFrame = frame;
              this.explorerDisabled = false;
              this.rebuildExplorer();

              this.textCsv = $.csv.fromArrays(frame);
              this.textCsvTouched = false;
            }
          });
      });
    },
    isFrameDocumentArtifact() {
      return (
        this.artifact.type_urn.indexOf("urn:x-mfg:artifact:digital:frame") == 0
      );
    },
    rebuildExplorer() {
      // Rebuild explorer
      if (!this.isFrameDocumentArtifact()) return;
      $("#pivottable-" + this.$.uid).empty();
      $("#pivottable-" + this.$.uid).append(
        '<div id="pivottable-ui-' + this.$.uid + '"></div>'
      );
      $("#pivottable-ui-" + this.$.uid).pivotUI(this.explorerFrame, {
        renderers: $.extend(
          $.pivotUtilities.renderers,
          $.pivotUtilities.plotly_renderers
        ),
      });
    },
    onTabChange(change) {
      if (this.activeTab == "explorer") {
        if (this.textCsvTouched) {
          this.rebuildExplorer();
        }

        this.textCsvTouched = false;
      }
    },
    onTextJsonChange(change) {
      this.dirty = true;
      this.textTouched = true;

      try {
        this.editorJson = JSON.parse(this.textJson);
        this.editorDisabled = false;
        this.editorTouched = false;
      } catch (ex) {
        this.editorDisabled = true;
      }
    },
    onEditorJsonChange(change) {
      this.dirty = true;
      this.editorTouched = true;

      this.textJson = JSON.stringify(this.editorJson, null, 2);
      this.textJsonTouched = false;
    },
    onTextCsvChange(change) {
      this.dirty = true;
      this.textCsvTouched = true;

      try {
        this.explorerFrame = $.csv.toArrays(this.textCsv);
        this.explorerDisabled = false;
      } catch (ex) {
        this.explorerDisabled = true;
      }
    },
    onClickFullscreen() {
      const pivotElem = document.querySelector("#pivottable-" + this.$.uid);
      screenfull.request(pivotElem);
    },
    isSaveAllowed() {
      return this.dirty && !this.explorerDisabled && !this.editorDisabled;
    },
    onSaveArtifact() {
      const new_local_data = this.isFrameDocumentArtifact()
        ? { document: this.editorJson, frame: this.explorerFrame }
        : this.editorJson;

      let changes = [];
      changes.push({
        op: "replace",
        path: "local_data",
        value: new_local_data,
      });

      return this.$root.apiPatchArtifact(this.artifactId, changes).then(() => {
        return this.refreshArtifact().then(() => {
          this.dirty = false;
          this.rebuildExplorer();
        });
      });
    },
  },
  created() {
    return this.refreshArtifact().then(() => {
      this.activeTab = this.schema
        ? "editor"
        : this.isFrameDocumentArtifact()
        ? "csv"
        : "json";
      this.dirty = false;
      this.rebuildExplorer();
    });
  },
};
</script>

<style>
.auto-js-form .genFormLabel {
  font-size: 1em;
  color: black;
}
.auto-js-form .genFormItem {
  display: flex;
}
.auto-js-form .fieldGroupWrap .fieldGroupWrap_title {
  font-size: 1em;
  font-weight: normal;
  color: black;
}

.auto-js-form .fieldGroupWrap .fieldGroupWrap_title:after {
  content: " :";
}

.auto-js-form .fieldGroupWrap_box div.fieldGroupWrap_box {
  padding-left: 1em;
  margin-left: 0.25em;
  border-left: 2px solid #eeeeee;
}

.auto-js-form div.arrayOrderList {
  background: none;
}

.auto-js-form .arrayOrderList .arrayOrderList_item {
  padding: 25px 1em 0px 0px;
  margin-bottom: 1em;
}

.auto-js-form .arrayOrderList_item .arrayListItem_operateTool {
  top: 1px;
  right: 1px;
}

.auto-js-form .arrayOrderList_item .arrayListItem_content {
  padding-top: 0.25em;
}

.auto-js-form p.arrayOrderList_bottomAddBtn {
  text-align: left;
  padding: 1em 1em 0px;
  border-top: 2px solid #eeeeee;
}

.auto-js-form button.bottomAddBtn {
  background: lightgray;
}

.auto-js-form.el-form--default.el-form--label-top
  .el-form-item
  .el-form-item__label {
  margin-bottom: 0.1em;
}

.auto-js-form .el-form-item--default {
  margin-bottom: 0.2em;
}

.auto-js-form .el-input {
  display: flex;
}

.auto-js-form .el-input input {
  font-family: monospace;
}

.auto-js-form .el-input input[type=text] {
  width: max-content;
}

section.digital-document-content {
  padding: 0em 0em 0em 1em;
}
</style>
