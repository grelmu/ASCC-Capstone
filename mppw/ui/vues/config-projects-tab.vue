<template>
  <div v-if="isReady()">
    <div class="text-end">
      <o-button @click="onCreateProject()">Create Project</o-button>
    </div>

    <section class="mt-3 mb-3">
      <o-table :data="projects || []">
        <o-table-column #default="{ row }">
          <a @click="onEditProject(row['id'])" style="cursor: pointer"
            ><o-icon icon="circle-edit-outline"></o-icon
          ></a>
        </o-table-column>
        <o-table-column label="Name" #default="{ row }">
          {{ row["name"] }}
        </o-table-column>
        <o-table-column #default="{ row }">
          <a @click="onDeleteProject(row['id'])" style="cursor: pointer"
            ><o-icon icon="trash-can"></o-icon
          ></a>
        </o-table-column>
      </o-table>
    </section>

    <o-modal v-model:active="isCreatingProject">
      <h2>Create a new project</h2>

      <o-field label="Name">
        <o-input v-model="pendingProject.name"></o-input>
      </o-field>

      <o-field label="Description">
        <o-input v-model="pendingProject.description"></o-input>
      </o-field>

      <o-button
        @click="onCreateProjectSubmit()"
        :disabled="!isPendingProjectValid()"
        >Submit</o-button
      >
    </o-modal>

    <o-modal v-model:active="isEditingProject">
      <h2>Edit project</h2>

      <o-field label="Name">
        <o-input v-model="editableProject.name"></o-input>
      </o-field>

      <o-field label="Description">
        <o-input v-model="editableProject.description"></o-input>
      </o-field>

      <o-button
        @click="onEditProjectSubmit()"
        :disabled="!isEditableProjectValid()"
        >Submit</o-button
      >
    </o-modal>
  </div>
</template>

<script>
export default {
  data() {
    return {
      projects: null,

      isCreatingProject: false,
      pendingProject: null,

      isEditingProject: false,
      editableProject: null,
    };
  },
  methods: {
    isReady() {
      return this.projects != null;
    },
    refreshProjects() {
      return this.$root.apiFetchProjects().then((projects) => {
        return (this.projects = projects);
      });
    },
    getProject(id) {
      for (let project of this.projects || []) {
        if (project["id"] == id) return project;
      }
      return { id, name: id };
    },
    onCreateProject() {
      this.pendingProject = {};
      this.isCreatingProject = true;
    },
    isPendingProjectValid() {
      return (
        this.pendingProject != null &&
        (this.pendingProject.name || "").length > 0
      );
    },
    onCreateProjectSubmit() {
      let submitProject = JSON.parse(JSON.stringify(this.pendingProject));

      return this.$root
        .apiCreateProject(submitProject)
        .then(() => {
          this.isCreatingProject = false;
        })
        .finally(() => this.refreshProjects());
    },
    onEditProject(id) {
      this.editableProject = JSON.parse(JSON.stringify(this.getProject(id)));
      this.isEditingProject = true;
    },
    isEditableProjectValid() {
      return (
        this.editableProject != null &&
        (this.editableProject.name || "").length > 0
      );
    },
    onEditProjectSubmit() {
      if (
        !confirm(
          "Are you sure you want to modify project " +
            this.editableProject.name +
            "?"
        )
      )
        return;

      let changes = [
        { op: "replace", path: "name", value: this.editableProject.name },
        {
          op: "replace",
          path: "description",
          value: this.editableProject.description,
        },
      ];

      return this.$root
        .apiPatchProject(this.editableProject.id, changes)
        .then(() => {
          this.isEditingProject = false;
        })
        .finally(() => this.refreshProjects());
    },
    onDeleteProject(id) {
      let project = this.getProject(id);
      if (
        !confirm(
          "Are you sure you want to delete project " + project.name + "?"
        )
      )
        return;

      return this.$root
        .apiDeleteProject(id)
        .finally(() => this.refreshProjects());
    },
  },
  created() {
    this.refreshProjects();
  },
};
</script>

<style></style>
