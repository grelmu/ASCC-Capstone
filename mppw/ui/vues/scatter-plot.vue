<template >
  <div ref="scatterPlotRef">
    <div :id="'threejs-container-' + $.uid" class="threejs-container"></div>
    <o-button class="three-exit-btn" inverted 
      @click="(e) => { toggleFullscreen(); }">
      <o-icon :icon="'close'"></o-icon>
    </o-button>
    <div class="icon-row">
      <o-icon :icon="fullScreen ? 'fullscreen-exit' : 'fullscreen'" @click="toggleFullscreen()"></o-icon>
      <o-icon :icon="rotate ? 'lock-reset' : 'rotate-3d'" @click="toggleRotation()"></o-icon>
      <o-icon :icon="'backup-restore'" @click="resetCamera"></o-icon>
      <o-icon :icon="'sync'"></o-icon>
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
      scatterPlot: null,
      fullScreen: false,
      rotate: false,
      position: [0,0,0]
    };
  },
  props: {
    opId: String,
    artifactId: String,
    importData: Array,
    displayValue: String,
    pointSelector: String
  },
  watch: { 
      	displayValue: function(){ this.updateVisualization() },
        pointSelector: function(){ this.updateVisualization() },
      },
  methods: {
    updateVisualization(e){
      console.log("Updating Visualization...");
      this.scene.remove( this.points);
      const material = new THREE.PointsMaterial( { size: 15, vertexColors: true } );
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
      // return this.$root.apiFetchArtifact(this.artifactId).then((artifact) => {
      //   this.artifact = artifact;
      // });
    },
    createScatterPlot(){
      this.init_1();
      this.animate_1();
    },
    createRayCasterPlot(){
      this.init_2();
      this.animate_2();
    },
    buildPoints(){
      const box = this.$el.parentElement.parentElement.getBoundingClientRect();
      const geometry = new THREE.BufferGeometry();
      const color = new THREE.Color();

      const positions = [];
      const colors = [];
      let max = [null, null, null, null];
      let min = [null, null, null, null];
      for ( let i = 0; i < this.importData.length; i ++ ) {
        var currentPoint = this.pointSelector.split('.').reduce(function(p,prop) { return p[prop] }, this.importData[i]);
        var displayBool = this.displayValue.split('.').reduce(function(p,prop) { return p[prop] }, this.importData[i]);

        if ((!this.displayValue || displayBool) && this.pointSelector){
          positions.push(currentPoint.x, currentPoint.y, currentPoint.z);
          [currentPoint.x, currentPoint.y, currentPoint.z].forEach( (value, i) => {
            if ((value < min[i]) || min[i] === null) min[i] = value;
            if ((value > max[i]) || max[i] === null) max[i] = value;
          });

          const colorRatio = (i / this.importData.length);
          color.setRGB( colorRatio , colorRatio , 1 );
          colors.push( color.r, color.g, color.b );
        }
      };

      let span = max[0] - min[0];
      if (max[1]-min[1] > span) span = max[1] - min[1];
      if (max[2]-min[2] > span) span = max[1] - min[1];

      let adjustedPositions = positions.map((position, i) => { return ((position - min[i%3]) * (1 / span)) * 500});
      console.log(adjustedPositions);

      geometry.setAttribute( 'position', new THREE.Float32BufferAttribute( adjustedPositions, 3 ) );
      geometry.setAttribute( 'color', new THREE.Float32BufferAttribute( colors, 3 ) );

      geometry.computeBoundingSphere();

      const material = new THREE.PointsMaterial( { size: 15, vertexColors: true } );

      var points = new THREE.Points( geometry, material );
      points.geometry.center();

      return points;
    },

    init_1() {
      this.container = this.$el.querySelector( '.threejs-container' );
      let box = this.$el.parentElement.parentElement.getBoundingClientRect();

      this.camera = new THREE.PerspectiveCamera( 27, box.width / box.height, 5, 3500 );
      this.camera.position.z = 750;
      this.position = this.camera.position;
      console.log(this.camera);
      console.log(this.camera.position);

      this.scene = new THREE.Scene();
      this.scene.background = new THREE.Color( 0x050505 );
      // this.scene.fog = new THREE.Fog( 0x050505, 2000, 3500 );


// ///NOTE WE CAN FAKE THE TIME SLIDER
// // slider actually sets the end index [0:i] and on select we show that the time value is for it [array[i]]

// // let user pick what field to use to color code the results
// // let user pick what field to say if we display or not

      this.points = this.buildPoints();
      this.scene.add( this.points );

      this.renderer = new THREE.WebGLRenderer();
      this.renderer.setPixelRatio( window.devicePixelRatio );
      this.renderer.setSize( box.width, box.height );
      this.controls = new OrbitControls( this.camera, this.renderer.domElement );

      this.container.appendChild( this.renderer.domElement );
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
      this.renderer.render(this.scene, this.camera);
      this.controls.update();
    },
    render_1_old(){
      const time = Date.now() * 0.001;
      

      if (this.rotate){
        // r[2] is the var to use for colors
        this.points.rotation.x = time * 0.8; // time * 0.25;
        this.points.rotation.y = time * 0.75;
        this.points.rotation.z = time * 0.5;
      }
      this.points.geometry.center();
      this.renderer.render( this.scene, this.camera );
      this.controls.update();
    },
    generatePointCloudGeometry( color, width, length ) {

      const geometry = new THREE.BufferGeometry();
      const numPoints = width * length;

      const positions = new Float32Array( numPoints * 3 );
      const colors = new Float32Array( numPoints * 3 );

      let k = 0;

      for ( let i = 0; i < width; i ++ ) {

        for ( let j = 0; j < length; j ++ ) {

          const u = i / width;
          const v = j / length;
          const x = u - 0.5;
          const y = ( Math.cos( u * Math.PI * 4 ) + Math.sin( v * Math.PI * 8 ) ) / 20;
          const z = v - 0.5;

          positions[ 3 * k ] = x;
          positions[ 3 * k + 1 ] = y;
          positions[ 3 * k + 2 ] = z;

          const intensity = ( y + 0.1 ) * 5;
          colors[ 3 * k ] = color.r * intensity;
          colors[ 3 * k + 1 ] = color.g * intensity;
          colors[ 3 * k + 2 ] = color.b * intensity;

          k ++;

        }

      }

      geometry.setAttribute( 'position', new THREE.BufferAttribute( positions, 3 ) );
      geometry.setAttribute( 'color', new THREE.BufferAttribute( colors, 3 ) );
      geometry.computeBoundingBox();

      return geometry;

    },
    generatePointcloud( color, width, length ) {

      const geometry = this.generatePointCloudGeometry( color, width, length );
      console.table(geometry);
      const material = new THREE.PointsMaterial( { size: this.pointSize, vertexColors: true } );

      return new THREE.Points( geometry, material );
      // can we set point size(yes), transparency(?), and point color (yes)

    },
    generateIndexedPointcloud( color, width, length ) {

      const geometry = this.generatePointCloudGeometry( color, width, length );
      const numPoints = width * length;
      const indices = new Uint16Array( numPoints );

      let k = 0;

      for ( let i = 0; i < width; i ++ ) {

        for ( let j = 0; j < length; j ++ ) {

          indices[ k ] = k;
          k ++;

        }

      }

      geometry.setIndex( new THREE.BufferAttribute( indices, 1 ) );

      const material = new THREE.PointsMaterial( { size: this.pointSize, vertexColors: true } );

      return new THREE.Points( geometry, material );

    },
    generateIndexedWithOffsetPointcloud( color, width, length ) {

      const geometry = this.generatePointCloudGeometry( color, width, length );
      const numPoints = width * length;
      const indices = new Uint16Array( numPoints );

      let k = 0;

      for ( let i = 0; i < width; i ++ ) {

        for ( let j = 0; j < length; j ++ ) {

          indices[ k ] = k;
          k ++;

        }

      }

      geometry.setIndex( new THREE.BufferAttribute( indices, 1 ) );
      geometry.addGroup( 0, indices.length );

      const material = new THREE.PointsMaterial( { size: this.pointSize, vertexColors: true } );

      return new THREE.Points( geometry, material );

    },
    init_2() {

				this.container = this.$el.querySelector( '.threejs-container' );
        this.threshold = 0.1;
        this.pointSize = 0.05;
        this.width = 80;
        this.length = 160;
        this.rotateY = new THREE.Matrix4().makeRotationY( 0.005 );		
        this.intersection = null;
        this.spheresIndex = 0;
        this.toggle = 0;
        this.pointer = new THREE.Vector2();
			  this.spheres = [];

				this.scene = new THREE.Scene();

				this.clock = new THREE.Clock();

				this.camera = new THREE.PerspectiveCamera( 45, window.innerWidth / window.innerHeight, 1, 10000 );
				this.camera.position.set( 10, 10, 10 );
				this.camera.lookAt( this.scene.position );
				this.camera.updateMatrix();

				//

				const pcBuffer = this.generatePointcloud( new THREE.Color( 1, 0, 0 ), this.width, this.length );
        console.table(pcBuffer);
				pcBuffer.scale.set( 5, 10, 10 );
				pcBuffer.position.set( - 5, 0, 0 );
				this.scene.add( pcBuffer );

				const pcIndexed = this.generateIndexedPointcloud( new THREE.Color( 0, 1, 0 ), this.width, this.length );
				pcIndexed.scale.set( 5, 10, 10 );
				pcIndexed.position.set( 0, 0, 0 );
				this.scene.add( pcIndexed );

				const pcIndexedOffset = this.generateIndexedWithOffsetPointcloud( new THREE.Color( 0, 1, 1 ), this.width, this.length );
				pcIndexedOffset.scale.set( 5, 10, 10 );
				pcIndexedOffset.position.set( 5, 0, 0 );
				this.scene.add( pcIndexedOffset );

				this.pointclouds = [ pcBuffer, pcIndexed, pcIndexedOffset ];

				//

				const sphereGeometry = new THREE.SphereGeometry( 0.1, 32, 32 );
				const sphereMaterial = new THREE.MeshBasicMaterial( { color: 0xff0000 } );

        // trailing mouse line
				for ( let i = 0; i < 40; i ++ ) {

					const sphere = new THREE.Mesh( sphereGeometry, sphereMaterial );
					this.scene.add( sphere );
					this.spheres.push( sphere );

				}

				//

				this.renderer = new THREE.WebGLRenderer( { antialias: true } );
				this.renderer.setPixelRatio( window.devicePixelRatio );
				this.renderer.setSize( window.innerWidth, window.innerHeight );
				this.container.appendChild( this.renderer.domElement );

				//

				this.raycaster = new THREE.Raycaster();
				this.raycaster.params.Points.threshold = this.threshold;

				//

				// stats = new Stats();
				// container.appendChild( stats.dom );

				//

				window.addEventListener( 'resize', this.onWindowResize );
				document.addEventListener( 'pointermove', this.onPointerMove );

			},
    onPointerMove( event ) {

      this.pointer.x = ( event.clientX / window.innerWidth ) * 2 - 1;
      this.pointer.y = - ( (event.clientY - 48 ) / window.innerHeight ) * 2 + 1;

    },

    onWindowResize() {

      this.camera.aspect = window.innerWidth / window.innerHeight;
      this.camera.updateProjectionMatrix();

      this.renderer.setSize( window.innerWidth, window.innerHeight );

    },

    animate_2() {

      requestAnimationFrame( this.animate_2 );

      this.render_2();
      // stats.update();

    },

    render_2() {

      this.camera.applyMatrix4( this.rotateY );
      this.camera.updateMatrixWorld();

      this.raycaster.setFromCamera( this.pointer, this.camera );

      const intersections = this.raycaster.intersectObjects( this.pointclouds, false );
      this.intersection = ( intersections.length ) > 0 ? intersections[ 0 ] : null;

      if ( this.toggle > 0.02 && this.intersection !== null ) {

        this.spheres[ this.spheresIndex ].position.copy( this.intersection.point );
        this.spheres[ this.spheresIndex ].scale.set( 1, 1, 1 );
        this.spheresIndex = ( this.spheresIndex + 1 ) % this.spheres.length;

        this.toggle = 0;

      }

      for ( let i = 0; i < this.spheres.length; i ++ ) {

        const sphere = this.spheres[ i ];
        sphere.scale.multiplyScalar( 0.98 );
        sphere.scale.clampScalar( 0.01, 1 );

      }

      this.toggle += this.clock.getDelta();

      this.renderer.render( this.scene, this.camera );

    }
  },
  created() {
    this.spheresIndex = 0;
    this.toggle = 0;
    console.log(this.importData)
    return this.refreshPlot();
  },
  mounted() {
    this.createScatterPlot();
    // this.createRayCasterPlot();
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
    height: 100%;
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

  #three-parent-container .icon-row{
    position: absolute;
    bottom: 0;
    right: 0;
    height: 24px;
    margin: 5px;
  }

  #three-parent-container .icon-row .o-icon {
    color: white;
    width: auto;
    height: 100%;
    margin-left: 5px;
    pointer-events: all;
    cursor: pointer;
  }

  
</style>