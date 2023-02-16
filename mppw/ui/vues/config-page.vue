<template>
  <div>
    <h2>Configure Settings</h2>

    <o-tabs type="boxed" class="mt-3">
      <o-tab-item v-if="isUsersTabActive()">
        <template #header>
          <o-icon icon="account-multiple"></o-icon>
          <span>Users</span>
        </template>

        <div class="text-end">
          <o-button @click="onCreateUser()">Create User</o-button>
        </div>

        <section class="mt-3 mb-3">
          <o-table :data="projects != null && users != null ? users : []">
            <o-table-column #default="{ row }">
              <a @click="onEditUser(row['id'])" style="cursor: pointer"
                ><o-icon icon="circle-edit-outline"></o-icon
              ></a>
            </o-table-column>
            <o-table-column label="Username" #default="{ row }">
              {{ row["username"] }}
            </o-table-column>
            <o-table-column label="Scopes" #default="{ row }">
              {{ (row["allowed_scopes"] || []).map((id) => getScope(id).name) }}
            </o-table-column>
            <o-table-column label="Project Claims" #default="{ row }">
              {{
                ((row["local_claims"] || {})["projects"] || []).map(
                  (id) => getProject(id).name
                )
              }}
            </o-table-column>
            <o-table-column #default="{ row }">
              <a @click="onDeleteUser(row['id'])" style="cursor: pointer"
                ><o-icon icon="trash-can"></o-icon
              ></a>
            </o-table-column>
          </o-table>
        </section>

        <o-modal v-model:active="isCreatingUser">
          <h2>Create a new user</h2>

          <o-field label="Username">
            <o-input v-model="pendingUser.username"></o-input>
          </o-field>

          <o-field label="Project Claims">
            <o-inputitems
              v-model="pendingUser.local_claims.projects"
              :data="filteredProjects"
              field="name"
              icon="bookshelf"
              placeholder="Add a project"
              @typing="onTypingProjects"
              autocomplete
            >
            </o-inputitems>
          </o-field>

          <o-field label="Scopes">
            <o-inputitems
              v-model="pendingUser.allowed_scopes"
              :data="filteredScopes"
              field="name"
              icon="key-chain"
              placeholder="Add a security scope"
              @typing="onTypingScopes"
              autocomplete
            >
            </o-inputitems>
          </o-field>

          <o-field label="Password">
            <o-input type="password" v-model="pendingUser.password"> </o-input>
          </o-field>

          <o-field
            label="Re-enter Password"
            :variant="pendingPasswordsMatch() === false ? 'danger' : null"
            :message="
              pendingPasswordsMatch() === false ? 'Passwords do not match' : ''
            "
          >
            <o-input type="password" v-model="pendingUser.passwordValidate">
            </o-input>
          </o-field>

          <o-button
            @click="onCreateUserSubmit()"
            :disabled="!isPendingUserValid()"
            >Submit</o-button
          >
        </o-modal>

        <o-modal v-model:active="isEditingUser">
          <h2>Edit user</h2>

          <o-field label="Username">
            <o-input v-model="editableUser.username"></o-input>
          </o-field>

          <o-field label="Project Claims">
            <o-inputitems
              v-model="editableUser.local_claims.projects"
              :data="filteredProjects"
              field="name"
              icon="bookshelf"
              placeholder="Add a project"
              @typing="onTypingProjects"
              autocomplete
            >
            </o-inputitems>
          </o-field>

          <o-field label="Scopes">
            <o-inputitems
              v-model="editableUser.allowed_scopes"
              :data="filteredScopes"
              field="name"
              icon="key-chain"
              placeholder="Add a security scope"
              @typing="onTypingScopes"
              autocomplete
            >
            </o-inputitems>
          </o-field>

          <o-button
            @click="onEditUserSubmit()"
            :disabled="!isEditableUserValid()"
            >Submit</o-button
          >
        </o-modal>
      </o-tab-item>
    </o-tabs>
  </div>
</template>

<script>
export default {
  data() {
    return {
      users: null,
      projects: null,
      scopes: null,

      isCreatingUser: false,
      pendingUser: null,

      isEditingUser: false,
      editableUser: null,

      filteredScopes: [],
      filteredProjects: [],
    };
  },
  methods: {
    isUsersTabActive() {
      return this.users != null && this.projects != null && this.scopes != null;
    },
    refreshUsers() {
      return this.$root.apiFetchUsers().then((users) => {
        return (this.users = users);
      });
    },
    refreshProjects() {
      return this.$root.apiFetchProjects().then((projects) => {
        return (this.projects = projects);
      });
    },
    refreshScopes() {
      return this.$root.apiFetchScopes().then((scopes) => {
        return (this.scopes = Object.keys(scopes).map((scopeId) => {
          return { id: scopeId, name: scopes[scopeId] };
        }));
      });
    },
    getUser(id) {
      for (let user of this.users || []) {
        if (user["id"] == id) return user;
      }
      return null;
    },
    getProject(id) {
      for (let project of this.projects || []) {
        if (project["id"] == id) return project;
      }
      return { id, name: id };
    },
    getScope(id) {
      for (let scope of this.scopes || []) {
        if (scope["id"] == id) return scope;
      }
      return { id, name: id };
    },
    onCreateUser() {
      this.pendingUser = { local_claims: {} };
      this.isCreatingUser = true;
    },
    pendingPasswordsMatch() {
      if (
        this.pendingUser == null ||
        this.pendingUser.password == null ||
        this.pendingUser.passwordValidate == null
      )
        return null;
      return this.pendingUser.password == this.pendingUser.passwordValidate;
    },
    isPendingUserValid() {
      return (
        this.pendingUser != null &&
        (this.pendingUser.username || "").length > 0 &&
        (this.pendingUser.allowed_scopes || []).length > 0 &&
        this.pendingPasswordsMatch() === true
      );
    },
    onCreateUserSubmit() {
      let submitUser = JSON.parse(JSON.stringify(this.pendingUser));
      delete submitUser.passwordValidate;

      submitUser.allowed_scopes = submitUser.allowed_scopes.map(
        (scope) => scope.id
      );
      submitUser.local_claims.projects = submitUser.local_claims.projects.map(
        (project) => project.id
      );

      return this.$root
        .apiCreateUser(submitUser)
        .then(() => {
          this.isCreatingUser = false;
        })
        .finally(() => this.refreshUsers());
    },
    onEditUser(id) {
      this.editableUser = JSON.parse(JSON.stringify(this.getUser(id)));
      this.editableUser.allowed_scopes = (
        this.editableUser.allowed_scopes || []
      ).map((id) => this.getScope(id));
      this.editableUser.local_claims = this.editableUser.local_claims || {};
      this.editableUser.local_claims.projects = (
        this.editableUser.local_claims.projects || []
      ).map((id) => this.getProject(id));

      this.isEditingUser = true;
    },
    isEditableUserValid() {
      return (
        this.editableUser != null &&
        (this.editableUser.username || "").length > 0 &&
        (this.editableUser.allowed_scopes || []).length > 0
      );
    },
    onEditUserSubmit() {
      if (
        !confirm(
          "Are you sure you want to modify user " +
            this.editableUser.username +
            "?"
        )
      )
        return;

      let changes = [
        { op: "replace", path: "username", value: this.editableUser.username },
        {
          op: "replace",
          path: "allowed_scopes",
          value: this.editableUser.allowed_scopes.map((scope) => scope.id),
        },
        {
          op: "replace",
          path: "local_claims",
          value: {
            projects: this.editableUser.local_claims.projects.map(
              (project) => project.id
            ),
          },
        },
      ];

      return this.$root
        .apiPatchUser(this.editableUser.id, changes)
        .then(() => {
          this.isEditingUser = false;
        })
        .finally(() => this.refreshUsers());
    },
    onDeleteUser(id) {
      let user = this.getUser(id);
      if (
        !confirm("Are you sure you want to delete user " + user.username + "?")
      )
        return;

      return this.$root.apiDeleteUser(id).finally(() => this.refreshUsers());
    },
    onTypingScopes(text) {
      this.filteredScopes = this.scopes.filter((scope) => {
        return (
          scope["name"].toString().toLowerCase().indexOf(text.toLowerCase()) >=
          0
        );
      });
    },
    onTypingProjects(text) {
      this.filteredProjects = this.projects.filter((project) => {
        return (
          project["name"]
            .toString()
            .toLowerCase()
            .indexOf(text.toLowerCase()) >= 0
        );
      });
    },
  },
  created() {
    if (!this.$root.isAdminUser()) {
      this.$router.push("/");
      return;
    }

    this.refreshUsers();
    this.refreshProjects();
    this.refreshScopes();
  },
};
</script>

<style></style>
