<template>
  <div class="form-body text-center">
    <div class="form-signin">
      <form>
        <h1>
          <img src="favicon.ico" class="p-1" /><span
            style="vertical-align: middle; padding-left: 0.1em"
            >MPPW<span style="font-size: 0.75em">arehouse</span></span
          >
        </h1>
        <h1 class="h3 mb-3 fw-normal mt-4">Please sign in</h1>

        <div class="form-floating">
          <input
            type="text"
            class="form-control"
            id="floatingInput"
            placeholder="username"
            v-model="username"
          />
          <label for="floatingInput">Username</label>
        </div>
        <div class="form-floating">
          <input
            type="password"
            class="form-control"
            id="floatingPassword"
            placeholder="Password"
            v-model="password"
          />
          <label for="floatingPassword">Password</label>
        </div>

        <!--div class="checkbox mb-3">
          <label>
            <input type="checkbox" value="remember-me" /> Remember me
          </label>
        </div-->

        <button
          class="w-100 btn btn-lg btn-primary"
          type="submit"
          @click="doLogin"
        >
          Sign in
        </button>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      username: null,
      password: null,
    };
  },
  props: {
    fetchOauth2PasswordBearer: Function,
  },
  methods: {
    doLogin(event) {
      // DRAGONS - form submit will *cancel* our pending request,
      // and cause login-retry race conditions, we need to prevent that
      event.preventDefault();
      this.fetchOauth2PasswordBearer({
        method: "POST",
        body: new URLSearchParams({
          username: this.username,
          password: this.password,
        }),
      })
        .then((response) => {
          if (response.status == 200) return response.json();
          return null;
        })
        .then((json) => {
          if (json != null) {
            this.$emit("new-bearer-credentials", {
              user: this.username,
              token: json.access_token,
            });
          }
        });
    },
  },
};
</script>

<style scoped>
.form-body {
  height: 100%;
  display: flex;
  align-items: center;
  padding-top: 40px;
  padding-bottom: 40px;
  margin: 3em;
  background-color: #f5f5f5;
}

.form-signin {
  width: 100%;
  max-width: 330px;
  padding: 15px;
  margin: auto;
}

.form-signin .checkbox {
  font-weight: 400;
}

.form-signin .form-floating:focus-within {
  z-index: 2;
}

.form-signin input[type="email"] {
  margin-bottom: -1px;
  border-bottom-right-radius: 0;
  border-bottom-left-radius: 0;
}

.form-signin input[type="password"] {
  margin-bottom: 10px;
  border-top-left-radius: 0;
  border-top-right-radius: 0;
}
</style>
