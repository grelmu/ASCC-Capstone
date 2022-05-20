<template>
  <section v-if="metadata">
    <h1 @click="nameEdit = true" v-if="!nameEdit">{{ edit["name"] || "(no name)" }}</h1>
    <o-input
      type="text"
      v-if="nameEdit"
      v-model="edit['name']"
      v-on:change="checkChanges('name')"
      style="font-size: 1.5em"
    ></o-input>

    <div class="row">
      <div class="col-auto">
        <o-field label="Status">
          <o-select
            placeholder="Select a status"
            v-model="edit['status']"
            v-on:change="checkChanges('status')"
          >
            <option value="draft">draft</option>
            <option value="published">published</option>
          </o-select>
        </o-field>
      </div>
      <div class="col-10">
        <o-field label="Description">
          <o-input
            type="text"
            v-model="edit['description']"
            v-on:change="checkChanges('description')"
          ></o-input>
        </o-field>
      </div>
    </div>

    <div class="row">
      <div class="col">
        <o-field label="Start Date & Time">
          <o-input
            v-model="edit['start_at']"
            icon="clock"
            type="datetime-local"
            v-on:change="checkChanges('start_at')"
          ></o-input>
        </o-field>
      </div>
      <div class="col">
        <o-field label="End Date & Time">
          <o-input
            v-model="edit['end_at']"
            icon="clock"
            type="datetime-local"
            v-on:change="checkChanges('end_at')"
          ></o-input>
        </o-field>
      </div>
    </div>

    <div class="row">
      <div class="col-4">
        <o-field label="System Name">
          <o-input
            type="text"
            v-model="edit['system_name']"
            icon="washing-machine"
            placeholder="Add name"
            v-on:change="checkChanges('system_name')"
            style="height: 2.5em"
          ></o-input>
        </o-field>
      </div>
      <div class="col-8">
        <o-field label="Operator Names">
          <o-inputitems
            v-model="edit['human_operator_names']"
            icon="account-hard-hat"
            placeholder="Add system operators or technicians"
            v-on:add="checkChanges('human_operator_names')"
            v-on:remove="checkChanges('human_operator_names')"
          ></o-inputitems>
        </o-field>
      </div>
    </div>

    <div class="row">
      <div class="col-auto" style="flex: auto">
        <o-field label="Tags">
          <o-inputitems
            v-model="edit['tags']"
            icon="tag"
            placeholder="Add tags"
            v-on:add="checkChanges('tags')"
            v-on:remove="checkChanges('tags')"
          ></o-inputitems>
        </o-field>
      </div>
      <div class="col-auto" v-show="submitButton">
        <o-field>
          <o-button @click="onMetadataSubmit()" class="mt-4"
            >Save Changes</o-button
          >
        </o-field>
      </div>
    </div>
  </section>
</template>

<script>
export default {
  data() {
    return {
      nameEdit: false,
      edit: null,
      changes: [],
      submitButton: false,
    };
  },
  props: {
    metadata: null,
  },
  methods: {
    checkChanges(id) {
      if (this.edit[id] != this.metadata[id]) {
        this.changes.push({
          op: "replace",
          path: id,
          value: this.edit[id],
        });
      }
      this.submitButton = true;
    },
    onMetadataSubmit() {
      return this.$root
        .apiPatchOperation(this.metadata["id"], this.changes)
        .then(() => {
          this.submitButton = false;
          this.nameEdit = false;
          this.changes = [];
        });
    },
  },
  created() {
    this.edit = Object.assign({}, this.metadata);
    return true;
  },
};
</script>

<style scoped></style>
