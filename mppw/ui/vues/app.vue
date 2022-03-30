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
        <a class="navbar-brand col-md-3 col-lg-2 me-0 px-3" href="#"
          >MPPWarehouse</a
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
          class="form-control form-control-dark w-100"
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
            class="col-md-3 col-lg-2 d-md-block bg-light sidebar collapse"
          >
            <div class="position-sticky pt-3">
              <ul class="nav flex-column">
                <li class="nav-item">
                  <router-link to="/" class="nav-link">
                    Browse Operations
                  </router-link>
                </li>
                <li class="nav-item">
                  <router-link to="/about" class="nav-link">
                    About
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

          <main class="col-md-9 ms-sm-auto col-lg-10 px-md-4 mt-4">
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
  { path: "/about", component: RemoteVue.lazyComponent("vues/about-page.vue") },
  {
    path: "/operations/:id",
    component: RemoteVue.lazyComponent("vues/operations-page.vue"),
  },
];

const initRoutes = function (app) {
  router.getRoutes().forEach((route) => (route.props.app = app));
};

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
    apiUrl(input) {
      return location.origin + "/api/" + input;
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
}

@media (max-width: 767.98px) {
  .sidebar {
    top: 5rem;
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
  padding-top: 0.75rem;
  padding-bottom: 0.75rem;
  font-size: 1rem;
  background-color: rgba(0, 0, 0, 0.25);
  box-shadow: inset -1px 0 0 rgba(0, 0, 0, 0.25);
}

.navbar .navbar-toggler {
  top: 0.25rem;
  right: 1rem;
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
</style>
