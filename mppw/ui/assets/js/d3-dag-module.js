// Based on example from: https://codepen.io/brinkbot/pen/oNZJXqK?editors=1010
// Other helpful resources: https://observablehq.com/@erikbrinkman/d3-dag-topological

/*
TODO:
- [ ] Add discrete coloration to nodes
- [ ] Dynamically assign icons
- [ ] Fix off-by-one error that drops last node from graph
- [*] Add hyperlinks inside nodes
- [*] Add icons inside nodes
- [*] Add tooltips to nodes
- [*] Add properly sized text inside nodes 
- [*] Get actual data 
- [*] Change to Zherebko layout
*/

function Dag(graphData, network, {icons=null}) {
  console.log("Graph data: ", graphData);
  console.log("Network: ", network);
  const dag = d3.dagStratify()(graphData);
  const nodeRadius = 70; // adjusting this seems to only impact the inner text size?
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

  const steps = dag.size();
  const interp = d3.interpolateRainbow; // TODO: change coloration
  const colorMap = new Map();
  dag.descendants().forEach((node, i) => {
    colorMap.set(node.data.id, interp(i / steps));
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
  nodes
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
    .text(() => icons[0]); 
  
  // Add text to circle
  nodes
    .append("text")
    // Only show the final 9 characters + an ellipses
    .text((d) => "..." + d.data.id.slice(
      d.data.id.length - 9, d.data.id.length
    ))
    .attr("font-weight", "bold")
    .attr("font-family", "sans-serif")
    .attr("text-anchor", "middle")
    .attr("alignment-baseline", "middle")
    .attr("fill", "white")
    .style("transition-duration", ".3s")
    .on("mouseover", (d) => d3.select(d.target).attr("fill", "black"))
    .on("mouseout", (d) => d3.select(d.target).attr("fill", "white"))
    .append("title")
    .text((d) => d.data.id)

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
        if (match.text.length > 9) {
          return "..." + match.text.slice(match.text.length - 9, match.text.length)
        } else {
          return match.text;
        }
      })
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
    .text((d) => d.data.text)
  
  console.log("ICONS: ", icons);
  return [width, height];
} 

export default Dag;
