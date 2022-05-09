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

      <o-button @click="onNewProject()">New Project</o-button>
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
        <o-button @click="onNewOp()">New Operation</o-button>
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
              :key="opType.urn_prefix"
              :value="opType.urn_prefix"
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

      <!-- TODO: searching and pagination via API -->
      <section>
        <o-table :loading="opsLoading" :data="opsRows || []" 
        :current.sync="currentPage"
        :debounce-search="750" :per-page="perPage"   
        :paginated="isPaginated"
        backend-filtering @filters-change="onFilter">
        <!-- backend-pagination @page-change="onPageChange" :total="total"> -->
          <template v-for="column in opsColumns" :key="column.id">
            <o-table-column v-bind="column" sortable>
              <template v-slot="props">
                <span v-if="column.field == 'id'">
                  <router-link :to="'/operations/' + props.row.id">
                    {{ props.row.id }}
                  </router-link>
                </span>
                <span v-else-if="column.field == 'start_at' || column.field == 'end_at'">
                  {{ new Date(props.row[column.field]).toLocaleDateString() }}
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
      perPage: 10,
      currentPage: 1,
      opsColumns: [
        {
          field: 'id',
          label: 'ID'
        },
        {
          field: 'name',
          label: 'Name',
          searchable: true
        },
        {
          field: 'status',
          label: 'Status',
          searchable: true
        },
        {
          field: 'start_at',
          label: 'Start',
        },
        {
          field: 'end_at',
          label: 'End',
        }
      ],

      isCreatingNewOp: false,
      newOp: {},
    };
  },
  methods: {
    apiFetchProjects() {
      return this.$root
        .apiFetch("projects/", {
          method: "GET",
        })
        .then((response) => {
          if (response.status == 200) return response.json();
          this.$root.throwApiResponseError(
            response,
            "Unknown response when querying for projects"
          );
        });
    },
    apiFetchOpTypes() {
      return this.$root
        .apiFetch("operation-services/types/", {
          method: "GET",
        })
        .then((response) => {
          if (response.status == 200) return response.json();
          this.$root.throwApiResponseError(
            response,
            "Unknown response when querying for serviced operation types"
          );
        });
    },
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
    apiFetchProjectOps(project_id, parameters={}) {
      let fetchUrl = `operations/?project_ids=${project_id}&` +
      Object.keys(parameters).map(key => {
          return key + '=' + encodeURIComponent(parameters[key])
      }).join("&");

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
    refreshProjects() {
      this.projects = null;
      this.projectId = null;
      return this.apiFetchProjects().then((projects) => {
        this.projects = projects;
      });
    },
    refreshOpTypes() {
      this.opTypes = null;
      this.newOpTypeUrn = null;
      return this.apiFetchOpTypes().then((opTypes) => {
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
      return this.apiFetchProjectOps(this.projectId).then((ops) => {
        this.opsRows = ops;
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
    onPageChange(page){
      // Debug items below
      //
      // this.opsLoading = true;
      // return this.apiFetchProjectOps(this.projectId, this.parameters).then((ops) => {
      //   console.log(ops);
      //   this.opsRows = ops;
      //   this.opsLoading = false;
      // });
    },
    onFilter(parameters){
      parameters.page_num = this.currentPage
      parameters.page_size = this.perPage
      this.opsLoading = true;
      return this.apiFetchProjectOps(this.projectId, parameters).then((ops) => {
        this.opsRows = ops;
        this.opsLoading = false;
        console.log(ops);
      });
    }
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
