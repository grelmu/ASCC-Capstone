
const throwAlertResponseErr = function(response, msg) {
  err = new Error((msg ? msg + ": ": "") + response.status + " " + response.statusText)
  alert(err.message)
  throw err
}

const app = Vue.createApp({
  data() {
    return {
      ready: false,
      api_access_token: localStorage.getItem("mppw_api_access_token"),
      api_user: null,
    }
  },
  methods: {

    apiFetch(input, init) {
      input = "../api/" + input
      init.headers = init.headers || {}
      init.headers["Authorization"] = "Bearer " + this.api_access_token
      return fetch(input, init)
    },
    fetchCurrentApiUser() {
      return this.apiFetch("security/users/me", {
        "method": "GET"
      }).then(response => {
        if (response.status == 200) return response.json()
        if (response.status == 401) return null
        throwAlertResponseErr(response, "Unknown response when checking user status")
      })
    }
  },
  created() {

    this.fetchCurrentApiUser()
      .then(user => {
        this.api_user = user
      })
      .catch(err => {
        console.error(err)
        this.api_access_token = null
        this.api_user = null
      })
      .finally(() => {
        this.ready = true
      })
  },
})

app.mount("#app")
