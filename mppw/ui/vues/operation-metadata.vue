<template>
  <section v-if="metadata">
    <h1>{{metadata['name']}}</h1>
    <o-field label="Tags">
        <o-inputitems v-model="metadata['tags']" icon="tag" placeholder="Add tag"  v-on:add="edit=true" v-on:remove="edit=true" ></o-inputitems>
    </o-field>
    <o-field label="Status">
      <o-select placeholder="Select a status" v-model="metadata['status']" v-on:change="edit=true">
        <option value="draft">draft</option>
        <option value="published">published</option>
      </o-select>
    </o-field>
    <o-field label="Description">
      <o-input maxlength="500" type="textarea" v-model="metadata['description']"  v-on:change="edit=true" ></o-input>
    </o-field>
    <o-field label="System Name">
      <o-input type="text" v-model="metadata['system_name']"  v-on:change="edit=true" ></o-input>
    </o-field>
    <o-field label="Operator Names">
      <o-inputitems v-model="metadata['human_operator_names']" icon="person" placeholder="Add an operator"  v-on:add="edit=true" v-on:remove="edit=true" ></o-inputitems>
    </o-field>
    <o-field label="Start Date & Time">
      <o-input v-model="metadata['start_at']" icon="clock" type="datetime-local"  v-on:change="edit=true" ></o-input>
    </o-field>
    <o-field label="End Date & Time">
      <o-input v-model="metadata['end_at']" icon="clock" type="datetime-local"  v-on:change="edit=true" ></o-input>
    </o-field>
    <o-field>
    <o-button v-show="edit" @click="submit()">Submit</o-button>
    </o-field>
  </section>
</template>

<script>
export default {
  data() {
    return {
      edit: null,
    };
  },
  props: {
    metadata: null,
  },
  methods: {
    apiPutOp(opId,op) {
      return this.$root
        .apiFetch("operations/" + opId + "/", {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(op),
        })
        .then((response) => {
          if (response.status == 422) return response.json();
          this.$root.throwApiResponseError(
            response,
            "Unknown response when saving operation"
          );
        });
    },

    submit(){
      this.edit = false;
      return this.apiPutOp(this.metadata['id'],this.metadata);
    },
    
    status(message) {
      this.metadata['status'] = message;
      this.edit = true;
      return null;
    },

  },
  created() {
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