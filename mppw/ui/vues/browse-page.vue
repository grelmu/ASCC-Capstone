<template>
  <span class="example">Browse {{ msg }} {{app}}</span>
  <button @click="doLogout()">Logout</button>
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
      doLogout() {
        this.app.api_user = null
      }
    },
  }
</script>

<style scoped>
  .example {
    color: purple;
  }
</style>