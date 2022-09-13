<!--
    Component to render a pivot table, using pivotjs. Can be used for tables, plots, etc
-->
<template v-if="data">
  <div class="pvtUiContainer row">
    <div
      :id="'pivot-table-' + $.uid"
      :class="vertical ? 'pvtUiVertical col' : 'pvtUi col'"
      :style="'width:' + plotWidthPx + 'px;'"
    ></div>
  </div>
</template>

<script>
export default {
  data() {
    return {};
  },
  props: {
    inputData: Array,
    renderer: String,
    aggregator: String,
    vertical: Boolean,
    domain: Array,
    range: Array,
    plotWidthPx: Number,
  },
  methods: {
    buildPivotTable() {
      let config = $("#pivot-table-" + this.$.uid).data("pivotUIOptions") || {
        aggregatorName: this.aggregator,
        rendererName: this.renderer,
        cols: this.domain || [],
        rows: this.range || [],
        // NOTE that vertical layout means we want unused at the *top*
        unusedAttrsVertical: this.vertical ? false : undefined,
        rendererOptions: {
          plotly: {
            width: this.plotWidthPx,
          },
          plotlyConfig: {
            autosizable: true,
            responsive: true,
          },
        },
      };

      config["renderers"] = $.extend(
        $.pivotUtilities.renderers,
        $.pivotUtilities.export_renderers,
        $.pivotUtilities.plotly_renderers
      );

      return $("#pivot-table-" + this.$.uid).pivotUI(
        this.inputData,
        config,
        true
      );
    },
    onDataChange(newInputData) {
      return this.buildPivotTable();
    },
  },
  created() {
    this.$watch("inputData", (newInputData) => this.onDataChange(newInputData));
  },
  mounted() {
    return this.buildPivotTable();
  },
};
</script>
<style scoped>
.pvtUiContainer {
  justify-content: center;
}
.pvtUiVertical {
  font-size: x-small;
}
.pvtUiVertical >>> table {
  display: block;
}
.pvtUiVertical >>> tbody {
  display: block;
}
.pvtUiVertical >>> tr {
  display: block;
}
.pvtUiVertical >>> th {
  display: flex;
}
.pvtUiVertical >>> td {
  display: flex;
}
.pvtUiVertical >>> td.pvtUnused {
  order: 1;
  background-color: white;
  display: block;
  padding: 1em;
  line-height: 2.25em;
}
.pvtUiVertical >>> .pvtUnused li {
  display: inline;
}
.pvtUiVertical >>> td.pvtVals {
  background-color: lightblue;
}
.pvtUiVertical >>> td.pvtVals:before {
  content: "Aggregation:";
  font-weight: bold;
  padding: 0.75em;
}
.pvtUiVertical >>> td.pvtCols:before {
  content: "Domain:";
  font-weight: bold;
  padding: 0.75em;
}
.pvtUiVertical >>> td.pvtRows:before {
  content: "Range:";
  font-weight: bold;
  padding: 0.75em;
}
.pvtUiVertical >>> .pvtRendererArea table {
  display: table;
}
.pvtUiVertical >>> .pvtRendererArea tbody {
  display: table-row-group;
}
.pvtUiVertical >>> .pvtRendererArea tr {
  display: table-row;
}
.pvtUiVertical >>> .pvtRendererArea th {
  display: table-cell;
}
.pvtUiVertical >>> .pvtRendererArea td {
  display: table-cell;
}
</style>
