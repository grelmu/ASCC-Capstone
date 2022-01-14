<template>
  <span class="example">Login {{ msg }} {{(app != null)}}</span>
  <button @click="doLogin()">Login</button>
</template>

<script>
  export default {
    data () {
      return {
        msg: 'component!'
      }
    },
    props: {
      app: Object
    },
    methods: {
      doLogin() {
        this.app.api_user = "Me"
      }
    },
  }
</script>

<style scoped>
  .example {
    color: purple;
  }
</style>