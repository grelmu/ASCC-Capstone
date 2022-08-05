<template >
  <div ref="scatterPlotRef">
    <div :id="'threejs-container-' + $.uid" class="threejs-container" @click="toggleFullscreen()"></div>
    <o-button class="three-exit-btn" inverted 
      @click="(e) => { toggleFullscreen(); }">
      <o-icon :icon="'close'"></o-icon>
    </o-button>
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
      fullScreen: false
    };
  },
  props: {
    opId: String,
    artifactId: String,
    importData: Array,
  },
  methods: {
    toggleFullscreen(){
      this.fullScreen = !this.fullScreen;
      this.fullScreen ? 
        this.$el.parentElement.classList.add('three-full-screen'):
        this.$el.parentElement.classList.remove('three-full-screen');

      let box = this.$el.parentElement.getBoundingClientRect();

      this.camera.aspect = box.width / box.height;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize( box.width, box.height );
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
    init_1() {
        this.container = document.getElementById( 'threejs-container-' + this.$.uid);

        let box = this.$el.parentElement.parentElement.getBoundingClientRect();

				this.camera = new THREE.PerspectiveCamera( 27, box.width / box.height, 5, 3500 );
				this.camera.position.z = 750;

				this.scene = new THREE.Scene();
				this.scene.background = new THREE.Color( 0x050505 );
				// this.scene.fog = new THREE.Fog( 0x050505, 2000, 3500 );

				const geometry = new THREE.BufferGeometry();

				const positions = [];
				const colors = [];

				const color = new THREE.Color();

        let max = [1,1,1,1];
        let min = [1,1,1,1];
				for ( let i = 0; i < this.importData.length; i ++ ) {

					// positions
					const x = this.importData[i].ctx.x;
					const y = this.importData[i].ctx.y;
					const z = this.importData[i].ctx.z;

          [x, y, z].forEach( (value, i) => {
            if (value < min[i]) min[i] = value;
            if (value > max[i]) max[i] = value;
            if (value > max[3]) max[3] = value;
          });

					positions.push(x, y, z);

					// colors
          const colorRatio = (i / this.importData.length);
					color.setRGB( colorRatio * 0.75 + 0.25  , 1 , 1 );
					colors.push( color.r, color.g, color.b );

				}

        let ratio = 500 / max[3];

        let adjustedPositions = positions.map(position => { return position * ratio});

				geometry.setAttribute( 'position', new THREE.Float32BufferAttribute( adjustedPositions, 3 ) );
				geometry.setAttribute( 'color', new THREE.Float32BufferAttribute( colors, 3 ) );

				geometry.computeBoundingSphere();

				const material = new THREE.PointsMaterial( { size: 15, vertexColors: true } );

				this.points = new THREE.Points( geometry, material );
				this.scene.add( this.points );

				this.renderer = new THREE.WebGLRenderer();
				this.renderer.setPixelRatio( window.devicePixelRatio );
				this.renderer.setSize( box.width, box.height );

				this.container.appendChild( this.renderer.domElement );
    },
    animate_1(){
      requestAnimationFrame( this.animate_1 );
      this.render_1();
      // stats.update();
    },
    render_1(){
      const time = Date.now() * 0.001;

      this.points.rotation.x = time * (0.25 / 10.0);
      this.points.rotation.y = time * (0.25 / 10.0);
      this.points.rotation.z = time * 0.25;
      this.points.geometry.center();

      this.renderer.render( this.scene, this.camera );
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

				this.container = document.getElementById(  'threejs-container-' + this.$.uid );
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

  
</style>