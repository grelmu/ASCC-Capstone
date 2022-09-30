// Copyright 2021 Observable, Inc.
// Released under the ISC license.
// https://observablehq.com/@d3/force-directed-graph
function ForceGraph(
  {
    nodes, // an iterable of node objects (typically [{id}, …])
    links, // an iterable of link objects (typically [{source, target}, …])
  },
  {
    nodeId = (d) => d.id, // given d in nodes, returns a unique identifier (string)
    nodeGroup, // given d in nodes, returns an (ordinal) value for color
    nodeGroups, // an array of ordinal values representing the node groups
    nodeTitle, // given d in nodes, a title string
    nodeText,
    nodeHref,
    nodeHighlight,
    nodeFill = "currentColor", // node stroke fill (if not using a group color encoding)
    nodeStroke = "#fff", // node stroke color
    nodeStrokeWidth = 1.5, // node stroke width, in pixels
    nodeStrokeOpacity = 1, // node stroke opacity
    nodeRadius = 5, // node radius, in pixels
    nodeStrength,
    nodeHighlightColor = "red",
    linkSource = ({ source }) => source, // given d in links, returns a node identifier string
    linkTarget = ({ target }) => target, // given d in links, returns a node identifier string
    linkStroke = "#999", // link stroke color
    linkStrokeOpacity = 0.6, // link stroke opacity
    linkStrokeWidth = 1.5, // given d in links, returns a stroke width in pixels
    linkStrokeLinecap = "round", // link stroke linecap
    linkStrength,
    colors = d3.schemeTableau10, // an array of color strings, for the node groups
    icons = null,
    width = 640, // outer width, in pixels
    height = 400, // outer height, in pixels
    invalidation, // when this promise resolves, stop the simulation
  } = {}
) {
  // Compute values.
  const N = d3.map(nodes, nodeId).map(intern);
  const LS = d3.map(links, linkSource).map(intern);
  const LT = d3.map(links, linkTarget).map(intern);
  if (nodeTitle === undefined) nodeTitle = (_, i) => N[i];
  const T = nodeTitle == null ? null : d3.map(nodes, nodeTitle);
  const T2 = nodeText == null ? null : d3.map(nodes, nodeText);
  const A = nodeHref == null ? null : d3.map(nodes, nodeHref);
  const H = (nodeHighlight = null ? null : d3.map(nodes, nodeHighlight));
  const G = nodeGroup == null ? null : d3.map(nodes, nodeGroup).map(intern);
  const W =
    typeof linkStrokeWidth !== "function"
      ? null
      : d3.map(links, linkStrokeWidth);
  const L = typeof linkStroke !== "function" ? null : d3.map(links, linkStroke);

  // Replace the input nodes and links with mutable objects for the simulation.
  nodes = d3.map(nodes, (_, i) => ({ id: N[i] }));
  links = d3.map(links, (_, i) => ({ source: LS[i], target: LT[i] }));

  // Compute default domains.
  if (G && nodeGroups === undefined) nodeGroups = d3.sort(G);

  // Construct the scales.
  const color = nodeGroup == null ? null : d3.scaleOrdinal(nodeGroups, colors);

  // Construct the forces.
  const forceNode = d3.forceManyBody();
  const forceLink = d3
    .forceLink(links)
    .distance(() => nodeRadius * 4)
    .id(({ index: i }) => N[i]);
  if (nodeStrength !== undefined) forceNode.strength(nodeStrength);
  if (linkStrength !== undefined) forceLink.strength(linkStrength);

  // Add some forces to push DAG nodes in the right arrangement
  const forceForward = () => {
    for (let link of links) {
      let dy = link.source.y - link.target.y;
      if (dy < nodeRadius * 3) {
        let d = nodeRadius * 3 - dy;
        link.source.vy += d * 0.1;
        link.target.vy -= d * 0.1;
      }
    }
  };

  // Force from right to left
  const forceRight = () => {
    for (let link of links) {
      let dx = link.source.x - link.target.x;
      if (dx > nodeRadius * 2) {
        let d = nodeRadius * 3 + dx;
        link.source.vx -= d * 0.1;
        link.target.vx += d * 0.1;
      }
    }
  };

  const simulation = d3
    .forceSimulation(nodes)
    .force("link", forceLink)
    .force("charge", forceNode)
    // .force("dag", forceForward)
    .force("dag", forceRight)
    .force("center", d3.forceCenter())
    .force("collide", d3.forceCollide([nodeRadius * 2]))
    .on("tick", ticked);

  const svg = d3
    .create("svg")
    .attr("width", "100%")
    .attr("viewBox", [-width / 2, -height / 2, width, height])
    .attr("style", "max-width: 100%; height: auto; height intrinsic;");

  svg
    .append("defs")
    .append("marker")
    .attr("id", "arrowhead")
    .attr("viewBox", "-0 -5 10 10")
    .attr("refX", 0)
    .attr("refY", 0)
    .attr("orient", "auto")
    .attr("markerWidth", nodeRadius / 10.0)
    .attr("markerHeight", nodeRadius / 10.0)
    .attr("xoverflow", "visible")
    .append("svg:path")
    .attr("d", "M 0,-5 L 10 ,0 L 0,5")
    .attr("fill", "#999")
    .style("stroke", "none");

  const link = svg
    .append("g")
    .attr("stroke", typeof linkStroke !== "function" ? linkStroke : null)
    .attr("stroke-opacity", linkStrokeOpacity)
    .attr(
      "stroke-width",
      typeof linkStrokeWidth !== "function" ? linkStrokeWidth : null
    )
    .attr("stroke-linecap", linkStrokeLinecap)
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("marker-end", "url(#arrowhead)");

  const node = svg.append("g").selectAll("circle").data(nodes).join("g");

  let expansionRatio = 3;
  // Resize node content when any part of the node is hovered over
  node.on("mouseover", function() {
    let c = this.querySelector('circle');
    c.style.transitionDuration = '.2s';
    c.style.zIndex = '1000'; 
    // Increase the radius of the circle
    c.r.baseVal.value = c.r.baseVal.value * expansionRatio;
  });
  node.on("mouseout", function() {
    let c = this.querySelector('circle');
    c.style.transitionDuration = 'initial';
    c.style.zIndex = 'initial';
    c.r.baseVal.value = c.r.baseVal.value / expansionRatio; 
  });

  const nodeCircles = node
    .append("circle")
    .attr("stroke", nodeStroke)
    .attr("stroke-opacity", nodeStrokeOpacity)
    .attr("stroke-width", nodeStrokeWidth)
    .attr("r", nodeRadius)
    .call(drag(simulation));

  const nodeTextEls = node
    .append("text")
    .append("tspan")
    .attr("font-size", nodeRadius / 3 + "px")
    .attr("stroke-width", 0)
    .style("fill", "black")
    .style("font-weight", "bold")
    .style("text-anchor", "middle")
    .text(({ index: i }) => T[i]);

  const nodeTextEls2 = node
    .append("a")
    .attr("href", ({ index: i }) => A[i])
    .append("text")
    .append("tspan")
    .attr("font-size", nodeRadius / 3 + "px")
    .style("fill", "black")
    .style("text-anchor", "middle")
    .style("text-decoration", "none")
    .text(({ index: i }) => T2[i]);

  const nodeIcon = node
    .append("text")
    .attr("font-family", "Material Design Icons")
    .attr("font-size", nodeRadius + "px")
    .style("fill", "black")
    .style("text-anchor", "middle")
    .text(({ index: i }) => icons[G[i]]);

  if (W) link.attr("stroke-width", ({ index: i }) => W[i]);
  if (L) link.attr("stroke", ({ index: i }) => L[i]);
  if (G)
    nodeCircles.attr("fill", ({ index: i }) =>
      H[i] ? nodeHighlightColor : color(G[i])
    );
  if (T) {
    nodeCircles.append("title").text(({ index: i }) => T[i]);
  }

  if (invalidation != null) invalidation.then(() => simulation.stop());

  function intern(value) {
    return value !== null && typeof value === "object"
      ? value.valueOf()
      : value;
  }

  function ticked() {
    const math = window["math"];

    link.each((d, i, n) => {
      const sourcePoint = math.matrix([d.source.x, d.source.y]);
      const targetPoint = math.matrix([d.target.x, d.target.y]);
      let linkVector = math.subtract(targetPoint, sourcePoint);
      let linkMag = math.norm(linkVector);

      if (linkMag == 0) {
        d3.select(n[i])
          .attr("x1", d.target.x)
          .attr("y1", d.target.y)
          .attr("x2", d.target.x)
          .attr("y2", d.target.y);
      } else {
        linkVector = math.divide(linkVector, linkMag);

        const fromPoint = math.add(
          sourcePoint,
          math.multiply(linkVector, nodeRadius + 3.0 * (nodeRadius / 10.0))
        );
        const toPoint = math.subtract(
          targetPoint,
          math.multiply(linkVector, nodeRadius + 5.0 * (nodeRadius / 10.0))
        );

        d3.select(n[i])
          .attr("x1", math.subset(fromPoint, math.index(0)))
          .attr("y1", math.subset(fromPoint, math.index(1)))
          .attr("x2", math.subset(toPoint, math.index(0)))
          .attr("y2", math.subset(toPoint, math.index(1)));
      }
    });

    nodeCircles.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
    nodeTextEls.attr("x", (d) => d.x).attr("y", (d) => d.y + nodeRadius / 2.0);
    nodeTextEls2.attr("x", (d) => d.x).attr("y", (d) => d.y + nodeRadius);
    nodeIcon.attr("x", (d) => d.x).attr("y", (d) => d.y);
  }

  function drag(simulation) {
    function dragstarted(event) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    return d3
      .drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended);
  }

  return Object.assign(svg.node(), { scales: { color } });
}

export default ForceGraph;
