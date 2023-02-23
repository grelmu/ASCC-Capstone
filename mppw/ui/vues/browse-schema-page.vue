<template>
  <div>
    <h1>Browse Schema</h1>

    <o-field label="Project">
      <o-select
        placeholder="Select a project"
        v-model="projectId"
        @update:modelValue="onProjectSelected"
      >
        <option
          v-for="project in projects || []"
          :key="project.id"
          :value="project.id"
        >
          {{ project.name }}
        </option>
      </o-select>
    </o-field>

    <div v-if="projectId != null && projectSchemas != null" class="mt-5">
      <section class="mt-3 mb-3">
        <div class="mt-3 mb-1 text-end">
          <o-button
            v-if="$root.isModifyProvenanceUser()"
            @click="onNewSchema(templateOperation)"
            >New Operation Schema</o-button
          >
          <br />
          <o-button
            class="mt-1"
            v-if="$root.isModifyProvenanceUser()"
            @click="onNewSchema(templateDigitalArtifact)"
            >New Digital Artifact Schema</o-button
          >
        </div>

        <o-table :data="projectSchemas">
          <o-table-column #default="{ row }">
            <a
              title="Edit Schema"
              v-if="row['module'] == null"
              @click="onEditSchema(row)"
              style="cursor: pointer"
              ><o-icon icon="circle-edit-outline"></o-icon
            ></a>
          </o-table-column>
          <o-table-column #default="{ row }">
            <a
              title="Create Similar Schema"
              @click="onNewSchema(row)"
              style="cursor: pointer"
              ><o-icon icon="pencil-box-multiple-outline"></o-icon
            ></a>
          </o-table-column>
          <o-table-column label="Type" #default="{ row }">
            {{ row["type_urn"] }}
          </o-table-column>
          <o-table-column label="Name" #default="{ row }">
            {{ row["schema_model"]["name"] }}
          </o-table-column>
          <o-table-column label="Source" #default="{ row }">
            {{ row["module"] != null ? row["module"] : "(user)" }}
          </o-table-column>
          <o-table-column #default="{ row }">
            <a
              title="Delete Schema"
              v-if="row['module'] == null"
              @click="onDeleteSchema(row)"
              style="cursor: pointer"
              ><o-icon icon="trash-can"></o-icon
            ></a>
          </o-table-column>
        </o-table>
      </section>

      <o-modal v-model:active="activeNewSchema">
        <h2>Create a new schema</h2>

        <o-field label="Content">
          <o-input
            type="textarea"
            v-model="newSchema.storage_schema_json5"
            style="height: 15em; font-family: monospace; min-width: 30em"
          ></o-input>
        </o-field>

        <o-button @click="onNewSchemaSubmit">Submit</o-button>
      </o-modal>

      <o-modal v-model:active="activeEditSchema">
        <h2>Edit Schema</h2>

        <o-field label="Content">
          <o-input
            type="textarea"
            v-model="editSchema.storage_schema_json5"
            style="height: 15em; font-family: monospace; min-width: 30em"
          ></o-input>
        </o-field>

        <o-button @click="onEditSchemaSubmit">Submit</o-button>
      </o-modal>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      templateDigitalArtifact: null,
      templateOperation: null,

      projects: null,

      projectId: null,
      projectSchemas: null,

      newSchema: null,
      activeNewSchema: false,

      editSchema: null,
      activeEditSchema: false,
    };
  },
  methods: {
    refreshSchemaTemplates() {
      let fetchTemplates = Promise.all([
        this.$root.apiFetchModuleSchemaByType(
          "urn:x-mfg:artifact:digital:template"
        ),
        this.$root.apiFetchModuleSchemaByType("urn:x-mfg:operation:template"),
      ]);
      return fetchTemplates.then((results) => {
        this.templateDigitalArtifact = results[0];
        this.templateOperation = results[1];
        return results;
      });
    },
    refreshProjects() {
      this.projects = null;
      this.projectId = null;
      return this.$root.apiFetchProjects().then((projects) => {
        this.projects = projects;
      });
    },
    onProjectSelected(projectId) {
      this.projectId = projectId;
      if (this.projectId) {
        return this.refreshProjectSchemas();
      } else {
        return Promise.resolve(null);
      }
    },
    refreshProjectSchemas() {
      return this.$root
        .apiFetchProjectSchemas(this.projectId)
        .then((projectSchemas) => {
          this.projectSchemas = projectSchemas.sort((a, b) => {
            if (a["module"] != b["module"]) return b["module"] ? -1 : 1;
            return a["type_urn"].localeCompare(b["type_urn"]);
          });
          return this.projectSchemas;
        });
    },
    getTemplateJson5FromSchema(baseSchema) {
      let templateJson5 =
        baseSchema["storage_schema_json5"] || baseSchema["storage_schema_json"];
      let newUrn =
        baseSchema["type_urn"] +
        ":" +
        new Date().toISOString().replaceAll(/[^0-9]/g, "");

      return templateJson5
        .replace(baseSchema["type_urn"], newUrn)
        .replace(/(.?abstract.?:)\strue/, "$1 false");
    },
    onNewSchema(baseSchema) {
      this.newSchema = {
        project: this.projectId,
        storage_schema_json5: this.getTemplateJson5FromSchema(baseSchema),
      };
      this.activeNewSchema = true;
    },
    onNewSchemaSubmit() {
      let apiSchema = JSON.parse(JSON.stringify(this.newSchema));
      apiSchema["type_urn"] = JSON5.parse(apiSchema["storage_schema_json5"])[
        "type_urn"
      ];
      return this.$root
        .apiCreateUserSchema(apiSchema)
        .then((schema) => {
          this.activeNewSchema = false;
        })
        .finally(() => {
          return this.refreshProjectSchemas();
        });
    },
    onEditSchema(schema) {
      this.editSchema = {
        id: schema.id,
        project: schema.project,
        storage_schema_json5:
          schema["storage_schema_json5"] || schema["storage_schema_json"],
      };
      this.activeEditSchema = true;
    },
    onEditSchemaSubmit() {
      let changes = [
        {
          op: "replace",
          path: "type_urn",
          value: JSON5.parse(this.editSchema["storage_schema_json5"])[
            "type_urn"
          ],
        },
        {
          op: "replace",
          path: "storage_schema_json5",
          value: this.editSchema["storage_schema_json5"],
        },
      ];

      return this.$root
        .apiPatchUserSchema(this.editSchema["id"], changes)
        .then(() => {
          this.activeEditSchema = false;
        })
        .finally(() => {
          return this.refreshProjectSchemas();
        });
    },
    onDeleteSchema(schema) {
      if (
        !confirm(
          "Are you sure you want to delete schema " + schema["type_urn"] + "?"
        )
      )
        return;

      return this.$root
        .apiDeleteUserSchema(schema["id"])
        .finally(() => this.refreshProjectSchemas());
    },
  },
  created() {
    return this.refreshSchemaTemplates().then(() => this.refreshProjects());
  },
};
</script>

<style scoped>
.o-table__wrapper--mobile {
  overflow-x: visible;
}
</style>
