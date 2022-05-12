<template>
  <section v-if="metadata">
    <h1>{{metadata['name']}}</h1>
    <o-field label="Tags">
        <o-inputitems v-model="edit['tags']" icon="tag" placeholder="Add tag"  v-on:add="checkChanges('tags')" v-on:remove="checkChanges('tags')" ></o-inputitems>
    </o-field>
    <o-field label="Status">
      <o-select placeholder="Select a status" v-model="edit['status']" v-on:change="checkChanges('status')">
        <option value="draft">draft</option>
        <option value="published">published</option>
      </o-select>
    </o-field>
    <o-field label="Description">
      <o-input maxlength="500" type="textarea" v-model="edit['description']"  v-on:change="checkChanges('description')" ></o-input>
    </o-field>
    <o-field label="System Name">
      <o-input type="text" v-model="edit['system_name']"  v-on:change="checkChanges('system_name')" ></o-input>
    </o-field>
    <o-field label="Operator Names">
      <o-inputitems v-model="edit['human_operator_names']" icon="person" placeholder="Add an operator"  v-on:add="checkChanges('human_operator_names')" v-on:remove="checkChanges('human_operator_names')" ></o-inputitems>
    </o-field>
    <o-field label="Start Date & Time">
      <o-input v-model="edit['start_at']" icon="clock" type="datetime-local"  v-on:change="checkChanges('start_at')" ></o-input>
    </o-field>
    <o-field label="End Date & Time">
      <o-input v-model="edit['end_at']" icon="clock" type="datetime-local"  v-on:change="checkChanges('end_at')" ></o-input>
    </o-field>
    <o-field>
    <o-button v-show="submitButton" @click="onMetadataSubmit()">Submit</o-button>
    </o-field>
  </section>
</template>

<script>
export default {
  data() {
    return {
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
      if(this.edit[id] != this.metadata[id]){
        this.changes.push({
          op: "replace",
          path: id,
          value: this.edit[id],
        });
      }
      this.submitButton = true;
    },
    onMetadataSubmit(){
      this.submitButton = false;
      this.changes = [];
      return this.$root.apiPatchOperation(this.metadata['id'],this.changes);
    },
  },
  created() {
    this.edit= Object.assign({},this.metadata);
    return true;
  },
};
</script>

<style scoped>
.text-area {
  width: 100%;
  position: relative;
  padding: 0.75rem;
}
</style>