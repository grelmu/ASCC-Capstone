// Based on example from: https://codepen.io/brinkbot/pen/oNZJXqK?editors=1010
// Other helpful resources: https://observablehq.com/@erikbrinkman/d3-dag-topological

/*
TODO:
- [ ] Add arrows on links
- [*] Fix off-by-one error that drops last node from graph
- [*] Add discrete coloration to nodes
- [*] Dynamically assign icons
*/

/**
 * 
 * @param {Array} graphData An array of objects in the form:
 *   [{
 *     "id": "<NODE ID>",
 *     "parentIds": ["<NODE ID>", "<NODE ID>", ...]
 *   }]
 * @param {Object} network Object containing "links" and "nodes" properties
 * @param {Object} param2 Object containing google font icons and nodegroup
 * @returns An array with the SVG width and height
 */
function Dag(graphData, network, {
  nodeGroup=null, // Given d in nodes, returns an (ordinal) value for color
  icons=null,
  nodeHighlight = null,
  nodeHighlightColor = "red", // TODO: use this on final node?
}) {
  let dag = null;

  function intern(value) {
    return value !== null && typeof value === "object"
      ? value.valueOf()
      : value;
  }

  function getAndTruncateNodeText(targetNode, property, cutoff=Infinity) {
      if (targetNode[property].length > cutoff) {
        return "..." + targetNode[property].slice(targetNode[property]
          .length - cutoff, targetNode[property].length)
      } else {
        return targetNode[property];
      }
  }

  // For coloration of nodes:
  const G = nodeGroup == null ? null : d3.map(network.nodes, nodeGroup).map(intern);
  let nodeGroups;
  let colors = d3.schemeTableau10;
  // Construct the color scales.
  if (G && nodeGroups === undefined) nodeGroups = d3.sort(G);
  const color = nodeGroup == null ? null : d3.scaleOrdinal(nodeGroups, colors);

  // Restructure dag data so it can be displayed
  dag = graphData.length > 0 ? d3.dagStratify()(graphData) : null;
  if (dag == null) return [0, 0];

  const nodeRadius = 70; // Adjusting this seems to only impact the inner text size?
  const layout = d3
    .sugiyama() 
    .decross(d3.decrossOpt()) // minimize number of crossings
    .nodeSize((node) => [(node ? 3.6 : 0.25) * nodeRadius, 3 * nodeRadius]); 

  // Flip x and y to horizontal
  let flipDagHorizontal = (dag) => {
    const { width, height } = layout(dag);
    for (const node of dag) {
      [node.x, node.y] = [node.y, node.x];
    }
    for (const { points } of dag.ilinks()) {
      for (const point of points) {
        [point.x, point.y] = [point.y, point.x];
      }
    }
    return { width: height, height: width };
  };
  const {width, height} = flipDagHorizontal(dag);

  // Render SVG
  const svgSelection = d3.select("svg");
  svgSelection.style("height", "70vh");
  svgSelection.style("width", "100%");
  svgSelection.attr("viewBox", [0, 0, width, height].join(" "));
  const defs = svgSelection.append("defs"); // For gradients

  const colorMap = new Map();
  network.nodes.forEach((node, i) => {
    // TODO: used "1-" below to switch all orange nodes to blue nodes. Need to
    // verify that this yields correct operation coloration
    colorMap.set(node.id, color(1-G[i]));
  })

  // Create edges
  const line = d3
    .line()
    .curve(d3.curveCatmullRom)
    .x((d) => d.x)
    .y((d) => d.y);

  // Plot edges
  svgSelection
    .append("g")
    .selectAll("path")
    .data(dag.links())
    .enter()
    .append("path")
    .attr("d", ({ points }) => line(points))
    .attr("fill", "none")
    .attr("stroke-width", 3)
    .attr("stroke", ({ source, target }) => {
      // encodeURIComponents for spaces, hope id doesn't have a `--` in it
      const gradId = encodeURIComponent(`${source.data.id}--${target.data.id}`);
      const grad = defs
        .append("linearGradient")
        .attr("id", gradId)
        .attr("gradientUnits", "userSpaceOnUse")
        .attr("x1", source.x)
        .attr("x2", target.x)
        .attr("y1", source.y)
        .attr("y2", target.y);
      grad
        .append("stop")
        .attr("offset", "0%")
        .attr("stop-color", colorMap.get(source.data.id));
      grad
        .append("stop")
        .attr("offset", "100%")
        .attr("stop-color", colorMap.get(target.data.id));
      return `url(#${gradId})`;
    });

  // Select nodes
  const nodes = svgSelection
    .append("g")
    .selectAll("g")
    .data(dag.descendants())
    .enter()
    .append("g")
    .attr("transform", ({ x, y }) => `translate(${x}, ${y})`);

  // Plot node circles
  const nodeCircles = nodes
    .append("circle")
    .attr("r", nodeRadius)
    .attr("fill", (n) => colorMap.get(n.data.id));
  
  // Adds icon to circle
  nodes
    .append("text")
    .attr("font-family", "Material Design Icons")
    .attr("font-size", nodeRadius/2 + "px")
    .attr("dy", "-20px")
    .style("fill", "white")
    .style("text-anchor", "middle")
    .text((d, i) => icons[G[i]]);
  
  // Add text to circle
  nodes
    .append("text")
    .text((d) => getAndTruncateNodeText(d.data, "id", 9))
    .text(
      (d) => network.nodes.filter(n => n.id == d.data.id).map(match => {
        return getAndTruncateNodeText(match, "title", 15)})
    )
    .attr("font-weight", "bold")
    .attr("font-family", "sans-serif")
    .attr("text-anchor", "middle")
    .attr("alignment-baseline", "middle")
    .attr("fill", "white")
    .style("transition-duration", ".3s")
    .on("mouseover", (d) => d3.select(d.target).attr("fill", "black"))
    .on("mouseout", (d) => d3.select(d.target).attr("fill", "white"))
    .append("title")
    .text((d) => network.nodes.filter(n => n.id == d.data.id).map(match => {
        return getAndTruncateNodeText(match, "title")}))

  // Add link to part in circle
  nodes
    .append("text")
    .attr("dy", "20px")
    .append("a")
    .attr("href", (d) => network.nodes.filter(n => n.id == d.data.id).map(match => {
      return match.href
    }))
    .text(
      (d) => network.nodes.filter(n => n.id == d.data.id).map(match => {
        return getAndTruncateNodeText(match, "text", 10)}))
    .attr("font-weight", "bold")
    .attr("font-family", "sans-serif")
    .attr("text-anchor", "middle")
    .attr("alignment-baseline", "middle")
    .attr("fill", "white")
    .style("transition-duration", ".3s")
    .on("mouseover", (d) => d3.select(d.target).attr("fill", "black"))
    .on("mouseout", (d) => d3.select(d.target).attr("fill", "white"))
    .append("title")
    .text((d) => network.nodes.filter(n => n.id == d.data.id).map(match => {
          return match.text;}))
  
  return [width, height];
} 

export default Dag;
