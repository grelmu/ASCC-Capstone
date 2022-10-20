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
          <o-datetimepicker
            v-model="edit['start_at']"
            v-on:update:modelValue="checkChanges('start_at')"
            icon="clock"
            placeholder="Click to select..."
            :timepicker="{ enableSeconds : true }"
          ></o-datetimepicker>
        </o-field>
      </div>
      <div class="col">
        <o-field label="End Date & Time">
          <o-datetimepicker
            v-model="edit['end_at']"
            v-on:update:modelValue="checkChanges('end_at')"
            icon="clock"
            placeholder="Click to select..."
            :timepicker="{ enableSeconds : true }"
          ></o-datetimepicker>
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
    parseLocalAsUTC(val) {
      return new Date(val.substring(0, 19) + "Z");
    },
    dumpUTCAsLocal(dt) {
      return dt.toISOString().substring(0, 19);
    },
    checkChanges(id) {

      let addChange = this.edit[id] != this.metadata[id];
      let addChangeValue = this.edit[id];
      if (["start_at", "end_at"].includes(id)) {
        addChange = (this.edit[id] != this.parseLocalAsUTC(this.metadata[id]));
        addChangeValue = this.dumpUTCAsLocal(this.edit[id]);
      }

      if (addChange) {
        this.changes.push({
          op: "replace",
          path: id,
          value: addChangeValue,
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
    for (let dtf of ["start_at", "end_at"]) {
      if (!(dtf in this.edit)) continue;
      this.edit[dtf] = this.parseLocalAsUTC(this.edit[dtf]);
    }
    return true;
  },
};
</script>

<style scoped></style>
