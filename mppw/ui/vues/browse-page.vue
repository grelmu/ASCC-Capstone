<template>
  <div>
    <h1 class="example">Browse {{ msg }}</h1>

    <p>
      Lorem ipsum stuff.
    </p>
  </div>
</template>

<script>
  export default {
    data () {
      return {
        msg: 'component!'
      }
    },
    methods: {
    },
  }
</script>

<style scoped>
  .example {
    color: purple;
  }
</style>