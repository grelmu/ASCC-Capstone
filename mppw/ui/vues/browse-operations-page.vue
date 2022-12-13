<template>
  <div>
    <h1>Browse Operations</h1>

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

      <o-button v-if="$root.isAdminUser()" @click="onNewProject()">New Project</o-button>
    </o-field>

    <o-modal v-model:active="isCreatingNewProject">
      <h2>Create a new project</h2>

      <o-field label="Project Name">
        <o-input v-model="newProject.name"></o-input>
      </o-field>
      <o-field label="Description">
        <o-input v-model="newProject.description"></o-input>
      </o-field>

      <o-button @click="onNewProjectSubmit()">Submit</o-button>
    </o-modal>

    <div v-if="projectId" class="mt-5">
      <div class="mt-3 text-end">
        <o-button v-if="$root.isModifyProvenanceUser()" @click="onNewOp()">New Operation</o-button>
      </div>

      <o-modal v-model:active="isCreatingNewOp">
        <h2>Create a new operation</h2>

        <o-field label="Operation Type">
          <o-select
            placeholder="Select an operation type"
            v-model="newOp.type_urn"
            @update:modelValue="onOpTypeSelected"
          >
            <option
              v-for="opType in opTypes || []"
              :key="opType.type_urn"
              :value="opType.type_urn"
            >
              {{ opType.name }}
            </option>
          </o-select>
        </o-field>

        <o-field label="Operation Name">
          <o-input v-model="newOp.name"></o-input>
        </o-field>

        <o-field label="Description">
          <o-input v-model="newOp.description"></o-input>
        </o-field>

        <o-button @click="onNewOpSubmit()">Submit</o-button>
      </o-modal>

      <section>
        <o-table
          :loading="opsLoading"
          :data="opsRows || []"
          :current.sync="parameters.page_num"
          :debounce-search="750"
          :per-page="parameters.page_size"
          :paginated="isPaginated"
          backend-sorting
          @sort="onSort"
          backend-filtering
          @filters-change="onFilter"
          backend-pagination
          @page-change="onPageChange"
          :total="total"
        >
          <template v-for="column in opsColumns" :key="column.id">
            <o-table-column
              v-bind="column"
              :width="
                ['type_urn', 'status'].includes(column.field) ? 110 : null
              "
            >
              <template
                v-if="column.field == 'type_urn'"
                v-slot:searchable="props"
              >
                <o-select
                  @update:modelValue="(val) => (props.filters.type_urn = val)"
                >
                  <option :value="null">Select an operation type</option>
                  <option
                    v-for="opType in opTypes || []"
                    :key="opType.type_urn"
                    :value="opType.type_urn"
                    stye="align-items: flex-start;
                          display: flex;
                          text-align: left;"
                  >
                    {{ opType.name }}
                  </option>
                </o-select>
              </template>
              <template v-slot="props">
                <span v-if="column.field == 'type_urn'">
                  <span class="o-icon">
                    <i
                      class="mdi mdi-24px"
                      :class="getIconFromTypeName(props.row.type_urn)"
                      :title="
                        props.row.type_urn.replace('urn:x-mfg:operation:', '')
                      "
                    ></i>
                  </span>
                </span>
                <span v-else-if="column.field == 'name'">
                  <router-link :to="'/operations/' + props.row.id">
                    {{ props.row.name }}
                  </router-link>
                </span>
                <span
                  v-else-if="
                    column.field == 'start_at' || column.field == 'end_at'
                  "
                >
                  <span v-if="props.row[column.field] != null">
                    {{ new Date(props.row[column.field]).toLocaleDateString() }}
                  </span>
                </span>
                <span v-else>
                  {{ props.row[column.field] }}
                </span>
              </template>
            </o-table-column>
          </template>
        </o-table>
      </section>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      projects: null,
      opTypes: null,

      projectId: null,

      isCreatingNewProject: false,
      newProject: {},

      opsLoading: false,
      opsRows: null,
      isPaginated: true,
      parameters: {
        page_size: 10,
        page_num: 1,
      },
      total: 1000,
      opsColumns: [
        {
          field: "type_urn",
          label: "Type",
          sortable: true,
          searchable: true,
          position: "centered",
        },
        {
          field: "status",
          label: "Status",
          searchable: true,
          sortable: true,
        },
        {
          field: "name",
          label: "Name",
          searchable: true,
          sortable: true,
        },
        {
          field: "start_at",
          label: "Start",
          sortable: true,
        },
        {
          field: "end_at",
          label: "End",
          sortable: true,
        },
      ],

      isCreatingNewOp: false,
      newOp: {},
    };
  },
  methods: {
    // TODO: Move to $root app.vue
    apiCreateProject(project) {
      return this.$root
        .apiFetch("projects/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(project),
        })
        .then((response) => {
          if (response.status == 201) return response.json();
          this.$root.throwApiResponseError(
            response,
            "Unknown response when creating project"
          );
        });
    },
    apiFetchProjectOps(project_id) {
      return this.$root
        .apiFetch("operations/?project_ids=" + this.projectId, {
          method: "GET",
        })
        .then((response) => {
          if (response.status == 200) return response.json();
          this.$root.throwApiResponseError(
            response,
            "Unknown response when querying for project operations"
          );
        });
    },
    apiFetchProjectOpsPaged(project_id, parameters = {}) {
      let fetchUrl =
        `operations/paged/?project_ids=${project_id}&` +
        Object.keys(parameters)
          .map((key) => {
            return parameters[key]
              ? key + "=" + encodeURIComponent(parameters[key])
              : null;
          })
          .join("&");

      return this.$root
        .apiFetch(fetchUrl, {
          method: "GET",
        })
        .then((response) => {
          if (response.status == 200) return response.json();
          this.$root.throwApiResponseError(
            response,
            "Unknown response when querying for project operations"
          );
        });
    },
    apiCreateOp(op) {
      return this.$root
        .apiFetch("operations/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(op),
        })
        .then((response) => {
          if (response.status == 201) return response.json();
          this.$root.throwApiResponseError(
            response,
            "Unknown response when creating operation"
          );
        });
    },
    apiInitOp(opId, args) {
      return this.$root
        .apiFetch("operations/" + opId + "/services/operation/init", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(args || {}),
        })
        .then((response) => {
          if (response.status == 200) return response.json();
          this.$root.throwApiResponseError(
            response,
            "Unknown response when initializing operation"
          );
        });
    },
    getIconFromTypeName(type_urn) {
      switch (type_urn.replace("urn:x-mfg:operation:", "")) {
        case "fff":
          return "mdi-printer-3d";
        case "prepare:waterjetcut":
          return "mdi-water-pump";
        case "prepare:machining":
          return "mdi-hammer-wrench";
        case "characterize:dimensioning":
          return "mdi-ruler";
        case "characterize:tensile-test":
          return "mdi-weight-lifter";
        case "characterize:shear-test":
          return "mdi-weight-lifter";
        case "characterize:compression-test":
          return "mdi-weight-lifter";
        default:
          return "mdi-help-rhombus";
      }
    },
    refreshProjects() {
      this.projects = null;
      this.projectId = null;
      return this.$root.apiFetchProjects().then((projects) => {
        this.projects = projects;
      });
    },
    refreshOpTypes() {
      this.opTypes = null;
      this.newOpTypeUrn = null;
      return this.$root.apiFetchOpTypes().then((opTypes) => {
        this.opTypes = opTypes;
      });
    },

    onProjectSelected(projectId) {
      this.projectId = projectId;
      this.resetOpsTable();
      if (this.projectId) this.loadOpsTable();
    },

    loadOpsTable() {
      this.opsLoading = true;
      return this.apiFetchProjectOpsPaged(this.projectId).then((ops) => {
        this.opsRows = ops.results;
        this.total = ops.total;
        this.opsLoading = false;
      });
    },
    resetOpsTable() {
      this.opsLoading = false;
      this.opsRows = null;
    },

    onNewProject() {
      this.isCreatingNewProject = true;
      this.newProject = {};
    },
    onNewProjectSubmit() {
      this.apiCreateProject(this.newProject).finally(() => {
        this.isCreatingNewProject = false;
        this.refreshProjects();
      });
    },

    onNewOp() {
      this.isCreatingNewOp = true;
      this.newOp = {};
    },
    onOpTypeSelected(opTypeUrn) {
      this.newOp.type_urn = opTypeUrn;
    },
    onNewOpSubmit() {
      this.newOp.project = this.projectId;

      this.apiCreateOp(this.newOp)
        .then((op) => {
          return this.apiInitOp(op["id"]);
        })
        .finally(() => {
          this.isCreatingNewOp = false;
          this.resetOpsTable();
          this.loadOpsTable();
        });
    },
    onPageChange(page) {
      this.opsLoading = true;
      this.parameters.page_num = page;
      return this.apiFetchProjectOpsPaged(this.projectId, this.parameters).then(
        (ops) => {
          console.log(ops);
          this.opsRows = ops.results;
          this.total = ops.total;
          this.opsLoading = false;
        }
      );
    },
    onFilter(parameters) {
      Object.keys(parameters).map((key) => {
        this.parameters[key] = parameters[key];
      });
      this.opsLoading = true;
      return this.apiFetchProjectOpsPaged(this.projectId, this.parameters).then(
        (ops) => {
          this.opsRows = ops.results;
          this.total = ops.total;
          this.opsLoading = false;
          console.log(ops);
        }
      );
    },
    onSort(field, dir, event) {
      this.parameters.sort_col = field;
      this.parameters.sort_dir = dir;
      return this.apiFetchProjectOpsPaged(this.projectId, this.parameters).then(
        (ops) => {
          this.opsRows = ops.results;
          this.total = ops.total;
          this.opsLoading = false;
          console.log(ops);
        }
      );
    },
  },

  mounted() {
    this.refreshProjects();
    this.refreshOpTypes();
  },
};
</script>

<style scoped>
/* empty */
</style>
