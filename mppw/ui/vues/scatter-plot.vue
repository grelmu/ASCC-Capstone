<template >
  <div ref="scatterPlotRef">
    <!-- TODO: Add info button with camera controls shown. Possible system specific. -->
    <div :id="'threejs-container-' + $.uid" class="threejs-container"></div>
    <div class="icon-row-upper" :class="{ hide: !showSelectors }" >
      <div class="control-row">
        <o-tooltip label="What path the x,y,z coordinates are located at" multiline position="bottom" :delay="500">
          <select v-model="pointSelector">
            <option 
              v-for="option in findPointSelectorPaths(importData[0])"
              :key="option"
            >{{ option }}</option>
          </select>
        </o-tooltip>

        <o-tooltip label="What determines whether or not to include a point." multiline position="bottom" :delay="500">
          <select :disabled="pointSelector == ''" v-model="displayValue">
            <option value="">No filter value</option>
            <option 
              v-for="option in getDisplayValueOptions()"
              :key="option"
            >{{ option }}</option>
          </select>
        </o-tooltip>

        <o-tooltip label="What variable determines how the data is sorted and used in the slider." multiline position="bottom" :delay="500">
          <select :disabled="pointSelector == ''" v-model="sliderSelector">
            <option value="">No slider value</option>
          <option 
              v-for="option in getSliderSelectorOptions()"
              :key="option"
            >{{ option }}</option>
          </select>
        </o-tooltip>

        <o-tooltip label="Show/Hide selectors" position="right" :delay="500">
          <o-icon :icon="showSelectors ? 'menu-left' : 'menu-right'" @click="showSelectors = !showSelectors"></o-icon>
        </o-tooltip>
      </div>

      <div class="control-row">
        <div class="hotkey-legend">
          <h3>Hotkeys</h3>
          <p><span>b</span>+<span>left click</span>: Place new <u><b>b</b></u>ounding points</p>
          <p><span>1</span> or <span>2</span>: Toggle mesh visibility</p>
          <p><span>c</span>: Toggle mesh <u><b>c</b></u>ontrols</p>
          <p><span>m</span>: Toggle mesh control <u><b>m</b></u>ode &lpar;scale/translate&rpar;</p>
        </div>
      </div>
    
      </div>
      <div class="info-icon">
        <o-icon :icon="'information-outline'" @click="showSelectors = !showSelectors"></o-icon>
    </div>
    <div class="icon-row">
      <div class="time-slider hide">
        <o-slider
          :disabled="sliderSelector == ''"
          v-model="sliderRange"
          @dragend="updateVisualization()"
          :min=0
          :max="importData.length-1"
          :step="1"
          :custom-formatter="sliderFormat">
        </o-slider>
      </div>
      <!-- TODO: Add tooltips for these icons -->
      <!-- TODO: Move dropdowns into something like the time slider toggle -->
      <o-icon :icon="showTimeSlider ? 'menu-down' : 'menu-up'" @click="toggleTimeSlider()"></o-icon>
      <o-icon :icon="fullScreen ? 'fullscreen-exit' : 'fullscreen'" @click="toggleFullscreen()"></o-icon>
      <o-icon :icon="rotate ? 'lock-reset' : 'rotate-3d'" @click="toggleRotation()"></o-icon>
      <o-icon :icon="'backup-restore'" @click="resetCamera"></o-icon>
    </div>
  </div>
</template>

<script>
export default {
  components: {
    "scatter-plot": RemoteVue.asyncComponent(
      "vues/scatter-plot.vue"
    ),
  },
  data() {
    return {
      filteredData: [],
      scatterPlot: null,
      fullScreen: false,
      showTimeSlider: false,
      showSelectors: false,
      sliderRange: [0,1],
      maxStep: 1,
      rotate: false,
      position: [0,0,0],
      pointSelector: '',
      pointSelectorPaths: [],
      displayValue: '',
      displayValuePaths: [],
      sliderSelector: '',
      sliderSelectorPaths: [],
      windowPosition: {x: 0, y: 0},
      tooltip: null,
      new_bounds: [],
      showTransformControl: false,
    };
  },
  props: {
    opId: String,
    artifactId: String,
    importData: Array,
  },
  watch: { 
      	displayValue: function(){ this.updateVisualization() },
        pointSelector: function(){ this.updateVisualization() },
        sliderSelector: function(){ this.updateVisualization() },
      },
  methods: {
    updateVisualization(e){
      if (!this.scene) return true;
      // console.log("Updating Visualization...");
      this.scene.remove( this.points);
      this.points = this.buildPoints();
      this.scene.add( this.points );
    },
    toggleFullscreen(){
      this.fullScreen = !this.fullScreen;
      this.fullScreen ? 
        this.$el.parentElement.classList.add('three-full-screen'):
        this.$el.parentElement.classList.remove('three-full-screen');

      let box = this.$el.parentElement.getBoundingClientRect();

      this.camera.aspect = box.width / box.height;
      this.camera.updateProjectionMatrix();
      this.controls.update();

      this.transformControls.update();       

      this.renderer.setSize( box.width, box.height );
    },
    toggleRotation(){
      this.rotate = !this.rotate;
      if (!this.rotate) {
        // this.points.rotation.x = 0;
        // this.points.rotation.y = 0;
        // this.points.rotation.z = 0;
      }
    },
    toggleTimeSlider(){
      this.showTimeSlider = !this.showTimeSlider;
      this.showTimeSlider ?
        this.$el.querySelector('.time-slider').classList.remove('hide') :
        this.$el.querySelector('.time-slider').classList.add('hide');
    },
    sliderFormat(val){
      if (this.sliderSelector) {
        let formattedVal = this.sliderSelector.split('.').reduce(function(p,prop) { return p[prop] }, this.importData[val]);
        if (new Date(formattedVal) !== "Invalid Date" && !isNaN(new Date(formattedVal))){
          return new Date(formattedVal).toLocaleString({ weekday: 'short', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' });
        } else {
          return formattedVal;
          }
      } else {
        return "Please select a slider value"
      }
    },
    resetCamera(){
      this.rotate = false;
      this.points.rotation.x = 0;
      this.points.rotation.y = 0;
      this.points.rotation.z = 0;
      this.camera.position.x = this.position.x;
      this.camera.position.y = this.position.y;
      this.camera.position.z = this.position.z;
      this.controls.reset();
    },
    refreshPlot() {
      this.scatterPlot = null;
      const scene = new THREE.Scene();
    },
    createScatterPlot(){
      this.init_1();
      this.animate_1();
    },
    init_1() {
      this.container = this.$el.querySelector( '.threejs-container' );
      let box = this.$el.parentElement.parentElement.getBoundingClientRect();

      this.camera = new THREE.PerspectiveCamera( 27, box.width / box.height, 5, 3500 );
      this.camera.position.z = 750;
      this.position = this.camera.position;

      this.scene = new THREE.Scene();
      this.scene.background = new THREE.Color( 0x050505 );

      this.points = this.buildPoints();
      this.scene.add( this.points );

      this.renderer = new THREE.WebGLRenderer();
      this.renderer.setPixelRatio( window.devicePixelRatio );
      this.renderer.setSize( box.width, box.height );
      this.controls = new OrbitControls( this.camera, this.renderer.domElement );

      // TODO: any way to do this dynamically instead of hardcoding all 3?
      this.transformControls = new TransformControls( this.camera, this.renderer.domElement );
      this.associateTranContWithMesh(this.newBoundsCube, this.transformControls);

      this.pointer = new THREE.Vector2();
      this.raycaster = new THREE.Raycaster();

      this.container.appendChild( this.renderer.domElement );
      document.addEventListener( 'pointermove', this.onPointerMove );
    },
    buildPoints(){
      this.filteredData = [];
      if (this.sliderSelector){
        // TODO: Place camera relative to entire set of points instead of subset of points determined by the sliders
        this.importData.sort((a, b) => {
            let a_value = this.sliderSelector.split('.').reduce(function(p,prop) { return p[prop] }, a);
            let b_value = this.sliderSelector.split('.').reduce(function(p,prop) { return p[prop] }, b);
            return (a_value < b_value) ? -1 : ((a_value > b_value) ? 1 : 0);
          });
        this.filteredData = this.importData.slice(this.sliderRange[0],this.sliderRange[1]);
      } else {
        this.filteredData = [...this.importData];
      }
      
      const box = this.$el.parentElement.parentElement.getBoundingClientRect();
      const geometry = new THREE.BufferGeometry();
      const color = new THREE.Color();

      const positions = [];
      const colors = [];
      let max = [null, null, null, null];
      let min = [null, null, null, null];


      let newfiltereddata = [];
      for ( let i = 0; i < this.filteredData.length; i ++ ) {
        var currentPoint = this.pointSelector.split('.').reduce(function(p,prop) { return p[prop] }, this.filteredData[i]);
        var displayBool = this.displayValue.split('.').reduce(function(p,prop) { return p[prop] }, this.filteredData[i]);

        if ((!this.displayValue || displayBool) && this.pointSelector){
          if (Array.isArray(currentPoint) && currentPoint.length >= 3){
            currentPoint = {
              "x": currentPoint[0],
              "y": currentPoint[1],
              "z": currentPoint[2]
            }
          }

          positions.push(currentPoint.x, currentPoint.y, currentPoint.z);
          newfiltereddata.push(this.filteredData[i]);

          // Update the bounds if this point is outside them.
          [currentPoint.x, currentPoint.y, currentPoint.z].forEach( (value, i) => {
            if ((value < min[i]) || min[i] === null) min[i] = value;
            if ((value > max[i]) || max[i] === null) max[i] = value;
          });

          const colorRatio = (i / this.filteredData.length);
          color.setRGB( colorRatio , colorRatio , 1 );
          colors.push( color.r, color.g, color.b );
        }
      };

      this.filteredData = newfiltereddata;

      let span = max[0] - min[0];
      if (max[1]-min[1] > span) span = max[1] - min[1];
      if (max[2]-min[2] > span) span = max[2] - min[2];

      this.sizeRatio = 1/span;
      this.min = min;

      let adjustedPositions = positions.map((position, i) => { return ((position - min[i%3]) * (1 / span)) * 500});

      geometry.setAttribute( 'position', new THREE.Float32BufferAttribute( adjustedPositions, 3 ) );
      geometry.setAttribute( 'color', new THREE.Float32BufferAttribute( colors, 3 ) );

      geometry.computeBoundingSphere();

      const material = new THREE.PointsMaterial( { size: 5, vertexColors: true } );

      var points = new THREE.Points( geometry, material );
      points.geometry.center();

      // handle new bounding box functionality
      let width  = (max[0] - min[0]) * this.sizeRatio * 500;
      let height = (max[1] - min[1]) * this.sizeRatio * 500;
      let depth  = (max[2] - min[2]) * this.sizeRatio * 500;

      this.dimensions = [width, height, depth];
      
      let padding = 25;
      let scale = 1.25;

      const bounds_geometry = new THREE.BoxGeometry( width + padding , height+padding, depth+padding );
      this.original_dimensions = [width + padding , height+padding, depth+padding];
      const bounds_material = new THREE.MeshBasicMaterial( { color: 0x00ff00 ,opacity: 0.5, transparent: true, wireframe: true, side: THREE.DoubleSide } );
      this.bounds_cube = new THREE.Mesh( bounds_geometry, bounds_material );
      this.bounds_cube.scale.set(scale, scale, scale);
      this.bounds_points = new THREE.Group();
      this.scene.add( this.bounds_points );

      const new_bounds_material = new THREE.MeshBasicMaterial( { color: 0xff00ff ,opacity: 0.5, transparent: true, wireframe: true } );
      this.newBoundsCube = new THREE.Mesh (bounds_geometry, new_bounds_material);

      return points;
    },
    animate_1(){
      requestAnimationFrame( this.animate_1 );
      this.render_1();
    },
    render_1(){
      if (this.rotate){
        var SPEED = 0.01;
        this.points.rotation.x -= SPEED * 2;
        this.points.rotation.y -= SPEED;
        this.points.rotation.z -= SPEED * 3;
      }

      this.points.geometry.center();

      this.handleRaycasting();
        
      this.renderer.render(this.scene, this.camera);
      this.controls.update();
    },
    handleRaycasting(){
      // update the picking ray with the camera and pointer position
      this.raycaster.setFromCamera( this.pointer, this.camera );

      // calculate objects intersecting the picking ray
      const intersects = this.raycaster.intersectObject(this.points);
      if (intersects.length > 0 ){
        // console.log(intersects[0]);
        let colors = intersects[0].object.geometry.attributes.color;
        if (this.currentIndex && this.currentColors){
          colors.array[this.currentIndex + 0] = this.currentColors[0]
          colors.array[this.currentIndex + 1] = this.currentColors[1]
          colors.array[this.currentIndex + 2] = this.currentColors[2]
        } 
        this.currentIndex = intersects[0].index;
        this.currentColors = colors.array.slice(this.currentIndex, this.currentIndex+2);

        colors.array[this.currentIndex*3 + 0] = 1;
        colors.array[this.currentIndex*3 + 1] = 0;
        colors.array[this.currentIndex*3 + 2] = 0;

        // this.updateToolTip(intersects[0]);
        this.updateToolTip(this.filteredData[this.currentIndex]?.ctx);
        // console.log(this.filteredData[this.currentIndex]);
        // console.log(this.getAdjustedPoint(this.filteredData[this.currentIndex].p));

        // sadly this is a floatarray and does not have the splice function
        // this.currentColors = colors.array.splice((this.currentIndex * 3), 3, ...[1,0,0]);
        colors.needsUpdate= true;
      } else {
        this.tooltip.style.display = 'none';
      }
    },
    getAdjustedPoint(point){
      return point.map((val,i) =>{
        return (val - this.min[i]) * this.sizeRatio * 500
      });
    },
    onPointerMove( event ) {
      let canvasBounds = this.renderer.getContext().canvas.getBoundingClientRect();
      this.pointer.x = ( ( event.clientX - canvasBounds.left ) / ( canvasBounds.right - canvasBounds.left ) ) * 2 - 1;
      this.pointer.y = - ( ( event.clientY - canvasBounds.top ) / ( canvasBounds.bottom - canvasBounds.top) ) * 2 + 1;
      this.windowPosition = {
        x: event.clientX,
        y: event.clientY
      };

    },
    onWindowResize() {

      this.camera.aspect = window.innerWidth / window.innerHeight;
      this.camera.updateProjectionMatrix();

      this.renderer.setSize( window.innerWidth, window.innerHeight );

    },
    findPointSelectorPaths(obj, path=''){
      let successfulArray = [];
      Object.getOwnPropertyNames(obj).forEach(key => {
        if(typeof obj[key] == "object"){
          successfulArray.push(path + key);
          if (!this.pointSelector) this.pointSelector = path + key;
          successfulArray = successfulArray.concat(this.findPointSelectorPaths(obj[key], path + key + '.' ));
        }
      });
      return successfulArray;
    },
    getDisplayValueOptions(){
      if (this.pointSelector == '') return [];

      let obj = this.pointSelector.split('.').reduce(function(p,prop) { return p[prop] }, this.importData[0]);
      let arr = this.findDisplayValuePaths(obj, this.pointSelector + '.');
      if (!arr.includes(this.displayValue)) this.displayValue = '';
      return arr;
    },
    findDisplayValuePaths(obj, path=''){
      let successfulArray = [];

      Object.getOwnPropertyNames(obj).forEach(key => {
        if(typeof obj[key] == "boolean")
          successfulArray.push(path + key);
        if(typeof obj[key] == "object")
          successfulArray = successfulArray.concat(this.findDisplayValuePaths(obj[key], path + key + '.' ));
      });

      return successfulArray;
    },
    getSliderSelectorOptions(){
      if (this.pointSelector == '') return [];
      let obj = this.pointSelector.split('.').reduce(function(p,prop) { return p[prop] }, this.importData[0]);
      let arr = this.findSliderSelectorPaths(obj, this.pointSelector + '.');
      if (!arr.includes(this.sliderSelector)) this.sliderSelector = '';
      return arr;
    },
    findSliderSelectorPaths(obj,path='',comparator){
      let successfulArray = [];

      Object.getOwnPropertyNames(obj).forEach(key => {
        if(['number', 'string', 'bigint'].includes(typeof obj[key]))
          successfulArray.push(path + key);
        if(typeof obj[key] == "object")
          successfulArray = successfulArray.concat(this.findSliderSelectorPaths(obj[key], path + key + '.'));
      });

      return successfulArray;

    },
    createToolTipElement(){
      this.tooltip = document.createElement('div');
      this.tooltip.id = 'three-js-tooltip';
      this.tooltip.innerText = 'test Tooltip';

      let options = {
        position: 'fixed',
        'z-index': 1000,
        'background-color': '#2c2c2c',
        color: '#FFF',
        padding: '10px',
        'overflow-wrap': 'break-word',
        'max-width': '500px',
        'border-radius': '4px',
        display: 'none' 
      };
      Object.assign(this.tooltip.style,options);

      document.body.appendChild(this.tooltip);
    },
    updateToolTip(data){
      let options = {
        left: `${this.windowPosition.x - 520}px`,
        top: `${this.windowPosition.y}px`,
        display: 'block' 
      };
      Object.assign(this.tooltip.style,options);

      // let html = this.prettyPrintJSON(data);
      this.tooltip.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;

    },
    placePoint(vector, size, color){
      const geometry = new THREE.SphereGeometry(size);
      const material = new THREE.MeshBasicMaterial({
        color: color
      });

      const sphere = new THREE.Mesh(geometry, material);
      sphere.position.set(vector.x, vector.y, vector.z);
      this.bounds_points.add(sphere);
      this.new_bounds.push(vector);

      if (this.new_bounds.length == 2) {
        this.createBoundsCube();
        this.new_bounds.length = 0;
        this.bounds_points.children.length = 0;
      }
    },
    /**
     * associate a transformController with a given mesh
     * Args:
     *   mesh - a shape we want to add transform controls to
     *   tc   - a transformControls object
     */
    associateTranContWithMesh(mesh, tc){
        tc.setSpace('local');
        tc.attach(mesh);
        tc.enabled = false;
        tc.visible = false;
        tc.showX = this.showTransformControl;
        tc.showY = this.showTransformControl;
        tc.showZ = this.showTransformControl;

        tc.addEventListener('change', () => this.renderer.render(this.scene, this.camera));
        tc.addEventListener('mouseDown', function () {
            this.controls.enabled = false;
        }.bind(this));
        tc.addEventListener('mouseUp', function () {
            this.controls.enabled = true;
            this.translateBounds(mesh);
        }.bind(this));
    },
    createBoundsCube(){
      //check if we are missing a dimension
        let width = Math.abs(this.new_bounds[0].x - this.new_bounds[1].x);
        let height = Math.abs(this.new_bounds[0].y - this.new_bounds[1].y);
        let depth = Math.abs(this.new_bounds[0].z - this.new_bounds[1].z);
        let center = {
          x: (this.new_bounds[1].x + this.new_bounds[0].x) / 2,
          y: (this.new_bounds[0].y + this.new_bounds[1].y) / 2,
          z: (this.new_bounds[0].z + this.new_bounds[1].z) / 2
        }
        
        if (width <= 0.01){
          width = this.original_dimensions[0];
          center.x = 0;
        }
        if (height <= 0.01){
          height = this.original_dimensions[1];
          center.y = 0;
        }
        if (depth <= 0.01){
          depth = this.original_dimensions[2];
          center.z = 0;
        }

        let new_geometry = new THREE.BoxGeometry(width,height,depth);
        this.newBoundsCube.geometry.dispose();
        this.newBoundsCube.geometry = new_geometry;
        this.newBoundsCube.scale.set(1, 1, 1);

        this.newBoundsCube.position.set(center.x, center.y, center.z);
        this.newBoundsCube.updateMatrixWorld();

        this.translateBounds(this.newBoundsCube);
    },
    translateBounds(theCube){
      // how many decimal places to round to
      let precision = 2;
      // Get current center in relation to world space
      let currentPosition = theCube.position;
      //get current dimensions (has width,height,depth values)
      let currentdimensions = theCube.geometry.parameters;
      //get current scale
      let currentscale = theCube.scale;

      //get current min/max values
      let min = [ 0 - ( currentdimensions.width / 2 ), 
                  0 - ( currentdimensions.height / 2 ), 
                  0 - ( currentdimensions.depth / 2 ) ];
      // console.log('current min is: ', min);

      min = [
        currentPosition.x - ( currentdimensions.width * currentscale.x / 2 ), 
        currentPosition.y - ( currentdimensions.height * currentscale.y / 2 ), 
        currentPosition.z - ( currentdimensions.depth * currentscale.z / 2 )
      ];
      // console.log('Adjusting for local space, current min is: ', min);

      min = [ min[0] + (this.dimensions[0] / 2),
              min[1] + (this.dimensions[1] / 2),
              min[2] + (this.dimensions[2] / 2)
              ];
      // console.log('Adjusting for world space, current min is: ', min);

      min = [ min[0] / this.sizeRatio / 500,
              min[1] / this.sizeRatio / 500,
              min[2] / this.sizeRatio / 500
            ];
      // console.log('Adjusting for scaling, current min is: ', min);

      min = [ min[0] + this.min[0],
              min[1] + this.min[1],
              min[2] + this.min[2],
            ];
      // console.log('Accounting for min bounds: ', min);

      let max = [ ((currentPosition.x + ( currentdimensions.width * currentscale.x / 2 ) + ( this.dimensions[0] / 2 )) / this.sizeRatio / 500) + this.min[0], 
                  ((currentPosition.y + ( currentdimensions.height * currentscale.y / 2 ) + ( this.dimensions[1] / 2 )) / this.sizeRatio / 500) + this.min[1], 
                  ((currentPosition.z + ( currentdimensions.depth * currentscale.z / 2 ) + ( this.dimensions[2] / 2 )) / this.sizeRatio / 500) + this.min[2]
            ];
      // console.log('test max: ', max);

      //round 
      let newString = `[[${min[0].toFixed(precision)},${min[1].toFixed(precision)},${min[2].toFixed(precision)}],[${max[0].toFixed(precision)},${max[1].toFixed(precision)},${max[2].toFixed(precision)}]]`;

      this.$emit('newBounds', newString);

    },
  },
  created() {
    this.spheresIndex = 0;
    this.toggle = 0;
    
    this.pointSelectorPaths = this.findPointSelectorPaths(this.importData[0]);
    this.displayValuePaths = this.getDisplayValueOptions();
    this.sliderSelectorPaths = this.getSliderSelectorOptions();
    this.tooltip = document.getElementById('three-js-tooltip');
    if (!this.tooltip) this.createToolTipElement();
    
    return this.refreshPlot();
  },
  mounted() {
    function toggleCubeVisibility(scene, cube, tc=null) {
      if (scene.children.includes(cube)) {
        scene.remove(cube);
        if (tc != null) {scene.remove(tc); tc.enabled = false};
      } else {
        scene.add(cube);
        if (tc != null) {scene.add(tc); tc.enabled = true;};
      }
    }

    this.maxStep = this.importData.length-1
    this.sliderRange = [0, this.maxStep];
    this.createScatterPlot();

    let body = document.querySelector('body');

    window.addEventListener('keydown', (e) => {
      // Prevent keypress actions from firing when we're
      // entering text in an <input> or somthing like that.
      if (document.activeElement != body) {return}

      if (e.code == "Digit1" && this.bounds_cube) {
        toggleCubeVisibility(this.scene, this.bounds_cube);}

      if (e.code == "KeyB" && this.bounds_cube && this.bounds_points) {
        this.keyFlag = true;
      }

      if (e.code == "Digit2" && this.newBoundsCube){
        debugger;
        toggleCubeVisibility(this.scene, this.newBoundsCube, this.transformControls);
      }

      // Toggle scale mode on transform controls
      if (e.code == "KeyM") {
        if (this.transformControls.mode == 'scale') {
          this.transformControls.setMode('translate');
        } else {
          this.transformControls.setMode('scale');
        }
      }
      if (e.code == "KeyC") {
        this.showTransformControl = !this.showTransformControl;
        this.transformControls.enabled = this.showTransformControl;
        this.transformControls.visible = this.showTransformControl;
        this.transformControls.showX = this.showTransformControl;
        this.transformControls.showY = this.showTransformControl;
        this.transformControls.showZ = this.showTransformControl;
      }
    });

    window.addEventListener('keyup', (e) => {
      if (document.activeElement != body) {return}
      if (e.code == "KeyB" && this.bounds_cube && this.bounds_points) {
        this.keyFlag = false;
      }
    });

    window.addEventListener('mousedown', (e) => {
      if (document.activeElement != body) {return}
      if(this.keyFlag == true && this.raycaster){
        const bounds_intersects = this.raycaster.intersectObject(this.bounds_cube);

        // the children should be the points, the bounding box mesh, spheres added.
          this.placePoint(bounds_intersects[0].point, 2.5, '#00ff00');

      }
    });

  }
};
</script>

<style scoped>
  .threejs-container {
    /* width: 500px;
    height: 500px; */
  }

  .three-parent-container { 
    height: 100%;
  }

  .three-parent-container div {
    /* height: 100%; */
  }


  .three-exit-btn {
    display: none;
    position: fixed;
    top: 65px;
    left: 20px;
  }

  .three-show.three-full-screen .three-exit-btn{
    display: flex;
  }

  .three-parent-container .icon-row{
    position: absolute;
    display: flex;
    width: 100%;
    bottom: 0;
    right: 0;
    height: 34px;
    padding: 5px;
  }

  .three-parent-container .icon-row-upper{
    align-items: center;
    /* display: inline-flex; */
    display: flex;
    flex-direction: column;
    position: absolute;
    top: 0;
    margin-left: 10px;
    transition: margin-left .5s ease;
    
  }
  .icon-row-upper .control-row {
    display: flex;
    flex-direction: row;
    align-content: center;
    align-items: center;
    justify-content: flex-start;
    width: calc(100% - 10px);
  }
  .icon-row-upper .hotkey-legend {
    background: #ffffffb2;
    backdrop-filter: blur(5px);
    border-radius: 5px;
    color: #2c2c2c;
    width: calc(100% - 28px);
    padding-left: 7px;
  }
  .hotkey-legend ul {list-style-type: none;}
  .hotkey-legend p {
    margin: 7px 0px 0px 0px;
  }
  .hotkey-legend p:last-of-type {margin-bottom: 7px;}
  .hotkey-legend span {
    font-family: monospace;
    padding: 3px;
    border-radius: 3px;
    background-color: #2c2c2c;
    color: white;
  }
  .three-parent-container .icon-row-upper.hide{
    margin-left: -315px;
  }

  .icon-row-upper select {
    width: 100px;
    margin-right: 5px;
    text-overflow: ellipsis;
    overflow: hidden;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
}


/* Slider Stlying */
.top-ui {
  position: absolute;
  width: 100%;
  top: 0;
  height: 24px;
  padding: 0 20px;
  display: flex;
}
.time-slider {
  padding: 0 15px;
  display: flex;
  align-items: center;
  width: calc(100% - 30px);
  height: 100%;
  position: relative;
  top: 0;
  -moz-transition: top .5s ease;
  -webkit-transition: top .5s ease;
  -o-transition: top .5s ease;
  transition: top .5s ease;
}
.time-slider.hide { 
  top: 26px;
  -moz-transition: top .5s ease;
  -webkit-transition: top .5s ease;
  -o-transition: top .5s ease;
  transition: top .5s ease;
}
  .three-parent-container .o-icon {
    color: white;
    width: auto;
    height: 100%;
    margin-left: 5px;
    pointer-events: all;
    cursor: pointer;
  }

  .info-icon {
    position: absolute;
    top: 0;
    right: 0;
    margin-right: 5px;
  }

  .info-tooltip{
    max-width: 170px;
  }

  #tooltip {
    position: fixed;
    left: 0;
    top: 0;
    min-width: 100px;
    text-align: center;
    padding: 5px 12px;
    font-family: monospace;
    background: #a0c020;
    display: none;
    opacity: 0;
    border: 1px solid black;
    box-shadow: 2px 2px 3px rgba(0, 0, 0, 0.5);
    transition: opacity 0.25s linear;
    border-radius: 3px;
  }

  
</style>