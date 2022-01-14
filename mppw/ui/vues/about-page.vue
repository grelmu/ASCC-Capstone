<template>
  <span class="example">About {{ msg }}</span>
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
  }
</script>

<style scoped>
  .example {
    color: red;
  }
</style>