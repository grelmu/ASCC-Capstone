<template>
  <div>
    <h2>Configure Settings</h2>

    <o-tabs type="boxed" class="mt-3">
      <o-tab-item>
        <template #header>
          <o-icon icon="bookshelf"></o-icon>
          <span>Projects</span>
        </template>

        <config-projects-tab></config-projects-tab>
      </o-tab-item>
      <o-tab-item>
        <template #header>
          <o-icon icon="account-multiple"></o-icon>
          <span>Users</span>
        </template>

        <config-users-tab></config-users-tab>
      </o-tab-item>
    </o-tabs>
  </div>
</template>

<script>
export default {
  components: {
    "config-projects-tab": RemoteVue.asyncComponent(
      "vues/config-projects-tab.vue"
    ),
    "config-users-tab": RemoteVue.asyncComponent("vues/config-users-tab.vue"),
  },
  data() {
    return {};
  },
  methods: {},
  created() {
    if (!this.$root.isAdminUser()) {
      this.$router.push("/");
      return;
    }
  },
};
</script>

<style></style>
