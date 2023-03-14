<template>
  <div class="when-ready" v-if="ready">
    <!-- LOGIN SCREEN -->
    <div class="when-no-api" v-if="!hasApiCredentials()">
      <main>
        <login-page
          :fetchOauth2PasswordBearer="apiFetchLocalOauth2PasswordBearer"
          @new-bearer-credentials="newApiCredentials"
        ></login-page>
      </main>
    </div>
    <!-- END LOGIN SCREEN -->

    <!-- APP UI -->
    <div class="when-api" v-if="hasApiCredentials()">
      <header
        class="navbar navbar-dark sticky-top bg-dark flex-md-nowrap p-0 shadow"
      >
        <a class="navbar-brand col-sm-2 col-md-2 col-lg-1 me-0 px-2" href="#"
          ><img src="favicon.ico" style="height: 30px" />&nbsp;&nbsp;
          <span
            style="
              position: relative;
              top: 0.4em;
              left: -1.1em;
              font-size: 0.9em;
            "
            >MPPW</span
          ></a
        >
        <button
          class="navbar-toggler position-absolute d-md-none collapsed"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#sidebarMenu"
          aria-controls="sidebarMenu"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span class="navbar-toggler-icon"></span>
        </button>
        <input
          class="form-control form-control-dark"
          type="text"
          placeholder="Search"
          aria-label="Search"
        />
        <div class="navbar-nav">
          <div class="nav-item text-nowrap">
            <span class="nav-link px-3">{{ currentUser.username }}</span>
          </div>
        </div>
        <div class="navbar-nav">
          <div class="nav-item text-nowrap">
            <a class="nav-link px-3" href="#" @click="resetApiCredentials"
              >Sign out</a
            >
          </div>
        </div>
      </header>

      <div class="container-fluid">
        <div class="row">
          <nav
            id="sidebarMenu"
            class="col-md-2 col-lg-1 d-md-block bg-light sidebar collapse"
          >
            <div class="position-sticky pt-3">
              <ul class="nav flex-column">
                <li class="nav-item">
                  <router-link to="/" class="nav-link">
                    <o-icon icon="printer-3d"></o-icon>&nbsp;&nbsp;Operations
                  </router-link>
                </li>
                <li v-if="isModifyProvenanceUser()" class="nav-item">
                  <router-link to="/schema" class="nav-link">
                    <o-icon icon="application-braces"></o-icon>&nbsp;&nbsp;Schema
                  </router-link>
                </li>
                <li v-if="isAdminUser()" class="nav-item mt-3">
                  <router-link to="/config" class="nav-link text-dark">
                    <o-icon icon="database-cog"></o-icon>&nbsp;&nbsp;Configure
                  </router-link>
                </li>
                <li class="nav-item mt-3">
                  <router-link to="/about" class="nav-link">
                    <o-icon icon="information"></o-icon>&nbsp;&nbsp;About
                  </router-link>
                </li>
              </ul>

              <!-- Bookmark section if needed -->
              <!--h6 class="sidebar-heading d-flex justify-content-between align-items-center px-3 mt-4 mb-1 text-muted">
                    <span>Saved reports</span>
                    <a class="link-secondary" href="#" aria-label="Add a new report">
                      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-plus-circle" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                    </a>
                  </h6>
                  <ul class="nav flex-column mb-2">
                    <li class="nav-item">
                      <a class="nav-link" href="#">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-file-text" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                        Current month
                      </a>
                    </li>
                    <li class="nav-item">
                      <a class="nav-link" href="#">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-file-text" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                        Last quarter
                      </a>
                    </li>
                  </ul-->
            </div>
          </nav>

          <main class="main-content col-sm-auto col-md-12 col-lg-12 ms-md-auto px-4 mt-4">
            <router-view></router-view>
          </main>
        </div>
      </div>
    </div>
    <!-- END APP UI -->
  </div>
</template>

<script>
const routes = [
  {
    path: "/",
    component: RemoteVue.lazyComponent("vues/browse-operations-page.vue"),
  },
  {
    path: "/schema",
    component: RemoteVue.lazyComponent("vues/browse-schema-page.vue"),
  },
  { path: "/about", component: RemoteVue.lazyComponent("vues/about-page.vue") },
  {
    path: "/config",
    component: RemoteVue.lazyComponent("vues/config-page.vue"),
  },
  {
    path: "/operations/:id",
    component: RemoteVue.lazyComponent("vues/operations-page.vue"),
  },
  {
    path: "/artifacts/:id",
    component: RemoteVue.lazyComponent("vues/artifacts-page.vue"),
  },
];

export default {
  routes: routes,

  components: {
    "login-page": RemoteVue.asyncComponent("vues/login-page.vue"),
  },
  props: {
    appName: String,
  },
  data() {
    return {
      ready: false,
      currentUser: null,
      credentials: {
        api: {},
      },
    };
  },
  methods: {
    hasApiCredentials() {
      return Object.keys(this.credentials.api).length != 0;
    },
    resetApiCredentials() {
      this.currentUser = null;
      this.credentials.api = {};
      localStorage.removeItem((this.appName || "mppw") + "CredentialsApi");
      return this.apiLogout();
    },
    newApiCredentials(credentials) {
      return (
        credentials.token
          ? this.apiFetchTokenCookie(credentials.token)
          : Promise.resolve(null)
      )
        .then(() => {
          credentials.token = null;
          credentials.cookie = true;
          return this.apiFetchCurrentUser();
        })
        .then((currentUser) => {
          this.currentUser = currentUser;
          this.credentials.api = credentials;
          localStorage.setItem(
            (this.appName || "mppw") + "CredentialsApi",
            JSON.stringify(credentials)
          );
        })
        .catch((err) => {
          console.error(err);
          return this.resetApiCredentials();
        });
    },
    isAdminUser() {
      if (!this.currentUser) return false;
      return this.currentUser["scopes"].includes("*");
    },
    isModifyProvenanceUser() {
      if (!this.currentUser) return false;
      return (
        this.isAdminUser() ||
        this.currentUser["scopes"].includes("modify:provenance")
      );
    },
    isModifyArtifactUser() {
      if (!this.currentUser) return false;
      return (
        this.isAdminUser() ||
        this.isModifyProvenanceUser() ||
        this.currentUser["scopes"].includes("modify:artifact")
      );
    },
    isModifyOperationUser() {
      if (!this.currentUser) return false;
      return (
        this.isAdminUser() ||
        this.isModifyProvenanceUser() ||
        this.currentUser["scopes"].includes("modify:operation")
      );
    },
    apiUrl(input) {
      return location.origin + "/api/" + input;
    },
    apiQueryFromParams(params) {
      if (!params) return "";
      let paramArr = [];
      for (let key in params) {
        paramArr.push(key + "=" + encodeURIComponent(params[key]));
      }
      if (paramArr.length == 0) return "";
      return "?" + paramArr.join("&");
    },
    apiFetch(input, init, token) {
      input = this.apiUrl(input);
      init.headers = init.headers || {};
      if (token || this.credentials.api.token)
        init.headers["Authorization"] =
          "Bearer " + (token != null ? token : this.credentials.api.token);
      return fetch(input, init).then((response) => {
        if (response.status == 401) {
          console.warn("User is no longer logged into API.");
          this.credentials.api = {};
        }
        return response;
      });
    },
    apiFetchLocalOauth2PasswordBearer(init) {
      return this.apiFetch("security/token", init);
    },
    apiFetchCurrentUser(token) {
      return this.apiFetch(
        "security/users/me",
        {
          method: "GET",
        },
        token
      ).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when checking user status",
          true
        );
      });
    },
    apiFetchTokenCookie(token) {
      return this.apiFetch(
        "security/token-to-cookie",
        {
          method: "POST",
        },
        token
      ).then((response) => {
        if (response.status == 200) return;
        this.throwApiResponseError(
          response,
          "Unknown response when converting token to cookie",
          true
        );
      });
    },
    apiLogout() {
      return this.apiFetch("security/logout", {
        method: "POST",
      }).then((response) => {
        if (response.status == 200) return;
        this.throwApiResponseError(
          response,
          "Unknown response when logging out",
          true
        );
      });
    },
    apiCreateUser(userWithPassword) {
      return this.apiFetch("security/users/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(userWithPassword),
      }).then((response) => {
        if (response.status == 201) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when creating user"
        );
      });
    },
    apiFetchUsers() {
      return this.apiFetch("security/users/", {
        method: "GET",
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when fetching users",
          true
        );
      });
    },
    apiPatchUser(id, changes) {
      return this.apiFetch("security/users/" + id, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(changes),
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when patching user"
        );
      });
    },
    apiDeleteUser(id) {
      return this.apiFetch("security/users/" + id, {
        method: "DELETE",
      }).then((response) => {
        if (response.status == 200 || response.status == 204)
          return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when deleting user"
        );
      });
    },
    apiFetchScopes() {
      return this.apiFetch("security/scopes/", {
        method: "GET",
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when fetching scopes",
          true
        );
      });
    },
    apiCreateProject(project) {
      return this.apiFetch("projects/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(project),
      }).then((response) => {
        if (response.status == 201) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when creating project"
        );
      });
    },
    apiPatchProject(id, changes) {
      return this.apiFetch("projects/" + id, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(changes),
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when patching project"
        );
      });
    },
    apiDeleteProject(id) {
      return this.apiFetch("projects/" + id, {
        method: "DELETE",
      }).then((response) => {
        if (response.status == 200 || response.status == 204)
          return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when deleting project"
        );
      });
    },
    apiFetchProjects() {
      return this.apiFetch("projects/", {
        method: "GET",
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when querying for projects"
        );
      });
    },
    apiFetchProjectSchemas(projectId) {
      return this.apiFetch(
        "projects/" + projectId + "/services/project/schema/",
        {
          method: "GET",
        }
      ).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when querying for project schemas"
        );
      });
    },
    apiFetchProjectOperationSchemas(projectId) {
      return this.apiFetch(
        "projects/" + projectId + "/services/project/schema/operations/",
        {
          method: "GET",
        }
      ).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when querying for project operation schemas"
        );
      });
    },
    apiFetchProjectSchemaByType(projectId, type_urn) {
      return this.apiFetch(
        "projects/" +
          projectId +
          "/services/project/schema/?type_urn=" +
          encodeURIComponent(type_urn),
        {
          method: "GET",
        }
      ).then((response) => {
        if (response.status == 200) {
          return response
            .json()
            .then((response_arr) =>
              response_arr.length > 0 ? response_arr[0] : null
            );
        }
        this.throwApiResponseError(
          response,
          "Unknown response when querying for project schema by type"
        );
      });
    },
    apiFetchDigitalArtifactJsonSchema(id) {
      return this.apiFetch(
        "artifacts/" + id + "/services/artifact/digital/json_schema",
        {
          method: "GET",
        }
      ).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when retrieving json schema for artifact"
        );
      });
    },
    apiCreateUserSchema(schema) {
      return this.apiFetch("schemas/user/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(schema),
      }).then((response) => {
        if (response.status == 201) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when creating user schema"
        );
      });
    },
    apiPatchUserSchema(id, changes) {
      return this.apiFetch("schemas/user/" + id, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(changes),
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when patching user schema"
        );
      });
    },
    apiDeleteUserSchema(id) {
      return this.apiFetch("schemas/user/" + id, {
        method: "DELETE",
      }).then((response) => {
        if (response.status == 200 || response.status == 204)
          return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when deleting user schema"
        );
      });
    },
    apiFetchModuleSchemaByType(type_urn) {
      return this.apiFetch(
        "schemas/module/?type_urn=" + encodeURIComponent(type_urn),
        {
          method: "GET",
        }
      ).then((response) => {
        if (response.status == 200) {
          return response
            .json()
            .then((response_arr) =>
              response_arr.length > 0 ? response_arr[0] : null
            );
        }
        this.throwApiResponseError(
          response,
          "Unknown response when querying for module schema by type"
        );
      });
    },
    apiCreateArtifact(artifact) {
      return this.apiFetch("artifacts/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(artifact),
      }).then((response) => {
        if (response.status == 201) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when creating artifact"
        );
      });
    },
    apiInitArtifact(artifactId, args) {
      return this.apiFetch(
        "artifacts/" + artifactId + "/services/artifact/init",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(args || {}),
        }
      ).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when initializing artifact"
        );
      });
    },
    apiFetchArtifact(id) {
      return this.apiFetch("artifacts/" + id, { method: "GET" }).then(
        (response) => {
          if (response.status == 200) return response.json();
          else return { version: "" };
        }
      );
    },
    apiFetchArtifactOperationParent(id) {
      return this.apiFetch("artifacts/" + id + "/services/artifact/parent", {
        method: "GET",
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when retrieving parent of artifact"
        );
      });
    },
    apiFetchArtifactProvenance(id, strategy) {
      return this.apiFetch(
        "artifacts/" +
          id +
          "/services/artifact/provenance" +
          this.apiQueryFromParams({ strategy }),
        {
          method: "GET",
        }
      ).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when retrieving artifact provenance"
        );
      });
    },
    apiUpdateArtifact(artifact) {
      return this.apiFetch("artifacts/" + artifact["id"], {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(artifact),
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when updating artifact"
        );
      });
    },
    apiPatchArtifact(id, changes) {
      return this.apiFetch("artifacts/" + id, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(changes),
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when patching artifact"
        );
      });
    },
    apiFetchPointCloudBounds(id) {
      return this.apiFetch(`artifacts/${id}/services/point-cloud/bounds`, {
        method: "GET",
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when retrieving json bounds for artifact"
        );
      });
    },
    apiFetchPointcloudUrl(id, data) {
      // Build query URL by encoding all existing props of 'data' obj
      let fetchUrl =
        `artifacts/${id}/services/point-cloud/points?` +
        Object.keys(data)
          .map((key) => {
            return key + "=" + encodeURIComponent(data[key]);
          })
          .join("&");

      return fetchUrl;
    },
    apiFetchPointcloud(id, data) {
      // Build query URL by encoding all existing props of 'data' obj
      let fetchUrl = this.apiFetchPointcloudUrl(id, data);

      return this.apiFetch(fetchUrl, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when retrieving json schema for artifact"
        );
      });
    },
    apiFetchTimeSeriesBounds(id) {
      // Obtain the bounds of a time series
      return this.apiFetch(`artifacts/${id}/services/time-series/bounds`, {
        method: "GET",
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when retrieving json bounds for artifact"
        );
      });
    },
    apiFetchTimeSeriesUrl(id, data) {
      // Build query URL by encoding all existing props of 'data' obj
      let fetchUrl =
        `artifacts/${id}/services/time-series/sample?` +
        Object.keys(data)
          .map((key) => {
            return key + "=" + encodeURIComponent(data[key]);
          })
          .join("&");

      return fetchUrl;
    },
    apiFetchTimeSeries(id, data) {
      // Build query URL by encoding all existing props of 'data' obj
      let fetchUrl = this.apiFetchTimeSeriesUrl(id, data);

      return this.apiFetch(fetchUrl, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when retrieving json schema for artifact"
        );
      });
    },
    //Function to get the stats data using the api
    apiFetchDatabaseBucketStats(id) {
      return this.apiFetch(
        "artifacts/" + id + "/services/database-bucket/stats",
        { method: "GET" }
      ).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when querying database bucket stats"
        );
      });
    },
    apiFetchFileBucketListing(id) {
      return this.apiFetch("artifacts/" + id + "/services/file-bucket/ls", {
        method: "POST",
        /*headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(artifact),*/
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Bad response when fetching file bucket listing"
        );
      });
    },
    apiUploadFile(id, path, file) {
      let formData = new FormData();
      formData.append("path", path);
      formData.append("file", file);

      return this.apiFetch("artifacts/" + id + "/services/file-bucket/upload", {
        method: "POST",
        body: formData,
      }).then((response) => {
        if (response.status == 201) return response.json();
        this.throwApiResponseError(
          response,
          "Bad response when uploading attachment"
        );
      });
    },
    apiRenameFile(id, path, newPath) {
      return this.apiFetch("artifacts/" + id + "/services/file-bucket/rename", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ path, new_path: newPath }),
      }).then((response) => {
        if (response.status == 200) return;
        this.throwApiResponseError(response, "Bad response when deleting file");
      });
    },
    apiDeleteFile(id, path) {
      return this.apiFetch("artifacts/" + id + "/services/file-bucket/delete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(path),
      }).then((response) => {
        if (response.status == 200) return;
        this.throwApiResponseError(response, "Bad response when deleting file");
      });
    },
    apiTextQueryOperations(text_query, projectId) {
      let query = "?fulltext_query=" + encodeURIComponent(text_query);
      if (projectId)
        query = query + "&project_id=" + encodeURIComponent(projectId);

      return this.apiFetch("operations/" + query, {
        method: "GET",
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when text searching operations"
        );
      });
    },
    apiFetchOperation(id) {
      return this.apiFetch("operations/" + id, { method: "GET" }).then(
        (response) => {
          if (response.status == 200) return response.json();
          this.throwApiResponseError(
            response,
            "Unknown response when fetching operation"
          );
        }
      );
    },
    apiPatchOperation(id, changes) {
      return this.apiFetch("operations/" + id, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(changes),
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when patching operation"
        );
      });
    },
    apiPutOperation(id, op) {
      return this.$root
        .apiFetch("operations/" + id + "/", {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(op),
        })
        .then((response) => {
          if (response.status == 200) return response.json();
          this.$root.throwApiResponseError(
            response,
            "Unknown response when saving operation"
          );
        });
    },
    apiFetchArtifactGraph(operation) {
      let fetches = [];
      let graph = {};
      operation["artifact_transform_graph"].forEach((transform) => {
        graph[transform.kind_urn] = [];
        let inputs = transform["input_artifacts"] || [];
        let outputs = transform["output_artifacts"] || [];

        inputs.concat(outputs).forEach((artifactId) => {
          fetches.push(
            this.apiFetchArtifact(artifactId).then((artifact) => {
              graph[transform.kind_urn].push(artifact);
            })
          );
        });
      });

      return Promise.all(fetches).then(() => {
        return graph;
      });
    },
    apiAttachArtifact(opId, kindPath, artifactId, attachmentMode) {
      let attachment = {
        kind_path: kindPath,
        artifact_id: artifactId,
        attachment_mode: attachmentMode,
      };

      return this.apiFetch("operations/" + opId + "/artifacts/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(attachment),
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when creating attachment"
        );
      });
    },
    apiFetchAttachedArtifacts(id, queryParams) {
      if (
        "artifact_path" in queryParams &&
        Array.isArray(queryParams["artifact_path"])
      )
        queryParams["artifact_path"] = queryParams["artifact_path"].join(".");

      if (
        "parent_artifact_path" in queryParams &&
        Array.isArray(queryParams["parent_artifact_path"])
      )
        queryParams["parent_artifact_path"] =
          queryParams["parent_artifact_path"].join(".");

      return this.apiFetch(
        "operations/" +
          id +
          "/artifacts/" +
          this.apiQueryFromParams(queryParams),
        {
          method: "GET",
        }
      ).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when querying operation artifacts"
        );
      });
    },
    apiClaimArtifact(opId, kindPath, artifactId, attachmentMode) {
      let attachment = {
        kind_path: kindPath,
        artifact_id: artifactId,
        attachment_mode: attachmentMode,
      };

      return this.apiFetch("operations/" + opId + "/artifacts/claim", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(attachment),
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when claiming attachment"
        );
      });
    },
    apiDetachArtifact(opId, kindPath, artifactId, attachmentMode) {
      let attachment = {
        kind_path: kindPath,
        artifact_id: artifactId,
        attachment_mode: attachmentMode,
      };

      return this.apiFetch("operations/" + opId + "/artifacts/", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(attachment),
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when removing attachment"
        );
      });
    },
    apiFetchAllArtifactCandidates(opId) {
      return this.apiFetch("operations/" + opId + "/artifacts/all", {
        method: "GET",
      }).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when querying all artifact candidates"
        );
      });
    },
    apiFetchArtifactFrameCandidates(opId, artifactPath) {
      return this.apiFetch(
        "operations/" +
          opId +
          "/artifacts/frame_candidates?strategy=operation_local&artifact_path=" +
          encodeURIComponent(artifactPath.join(".")),
        {
          method: "GET",
        }
      ).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Unknown response when querying frame candidates"
        );
      });
    },
    apiFetchOpAttachments(opId) {
      return this.apiFetch(
        "operations/" + opId + "/artifacts/attachments/default",
        { method: "GET" }
      ).then((response) => {
        if (response.status == 200) return response.json();
        this.throwApiResponseError(
          response,
          "Bad response when fetching attachments"
        );
      });
    },
    apiUploadAttachment(attachments_id, path, file) {
      let formData = new FormData();
      formData.append("path", path);
      formData.append("file", file);

      return this.apiFetch(
        "artifacts/" + attachments_id + "/services/file-bucket/upload",
        {
          method: "POST",
          body: formData,
        }
      ).then((response) => {
        if (response.status == 201) return response.json();
        this.throwApiResponseError(
          response,
          "Bad response when uploading attachment"
        );
      });
    },
    throwApiResponseError(response, msg, showAlert) {
      const err = new Error(
        (msg ? msg + ": " : "") + response.status + " " + response.statusText
      );
      if (showAlert) alert(err.message);
      throw err;
    },
  },
  created() {
    let savedCredentials = null;
    try {
      savedCredentials =
        JSON.parse(
          localStorage.getItem((this.appName || "mppw") + "CredentialsApi")
        ) || null;
    } catch (ex) {
      // Unknown credentials
    }

    return (
      savedCredentials == null
        ? this.resetApiCredentials()
        : this.newApiCredentials(savedCredentials)
    ).finally(() => {
      this.ready = true;
    });
  },
};
</script>

<style scoped>
.feather {
  width: 16px;
  height: 16px;
  vertical-align: text-bottom;
}

/*
 * Sidebar
 */

.sidebar {
  position: fixed;
  top: 0;
  /* rtl:raw:
  right: 0;
  */
  bottom: 0;
  /* rtl:remove */
  left: 0;
  z-index: 100; /* Behind the navbar */
  padding: 48px 0 0; /* Height of navbar */
  box-shadow: inset -1px 0 0 rgba(0, 0, 0, 0.1);
  width: 130px;
}

@media (max-width: 767.98px) {
  .sidebar {
    top: 5rem;
    width: 100%;
  }
}

.sidebar-sticky {
  position: relative;
  top: 0;
  height: calc(100vh - 48px);
  padding-top: 0.5rem;
  overflow-x: hidden;
  overflow-y: auto; /* Scrollable contents if viewport is shorter than content. */
}

.sidebar .nav-link {
  font-weight: 500;
  color: #333;
  padding: 0.5rem 0.75rem;
  display: flex;
  align-items: center;
  font-size: 0.9em;
}

.sidebar .nav-link .feather {
  margin-right: 4px;
  color: #727272;
}

.sidebar .nav-link.active {
  color: #2470dc;
}

.sidebar .nav-link:hover .feather,
.sidebar .nav-link.active .feather {
  color: inherit;
}

.sidebar-heading {
  font-size: 0.75rem;
  text-transform: uppercase;
}

/*
 * Navbar
 */

.navbar-brand {
  padding-top: 0.5rem;
  padding-bottom: 1rem;
  box-shadow: inset -1px 0 0 rgba(0, 0, 0, 0.25);
  text-align: center;
  width: 130px;
}

.navbar .navbar-toggler {
  top: 0.5rem;
  right: 0.5rem;
}

.navbar .form-control {
  padding: 0.75rem 1rem;
  border-width: 0;
  border-radius: 0;
}

.form-control-dark {
  color: #fff;
  background-color: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.1);
}

.form-control-dark:focus {
  border-color: transparent;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.25);
}

.main-content {
  padding-left: 145px !important;
}

@media (max-width: 767.98px) {
  .main-content {
    padding-left: 15px !important;
  }
}

</style>

<style>
.o-modal {
  z-index: 1030;
}

.o-modal__content {
  overflow: visible;
  max-height: fit-content;
}

.o-modal__content h2 {
  font-size: 1.5em;
}

.o-modal__content h3 {
  font-size: 1.25em;
}

.o-modal--mobile .o-modal__content {
  width: 95%;
}

.o-modal__close {
  top: -5px;
  right: 5px;
}

select:disabled {
  opacity: 0.5;
}
</style>
