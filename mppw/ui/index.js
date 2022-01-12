const maxNtpOffsetHost = function(ntpStatus) {
    let maxOffsetHost = null
    for (let host in ntpStatus) {
        if (maxOffsetHost === null || ntpStatus[host][6] > ntpStatus[maxOffsetHost][6])
            maxOffsetHost = host
    }
    return maxOffsetHost
}

const prettyMaxNtpOffset = function(ntpStatus) {
    let maxOffsetHost = maxNtpOffsetHost(ntpStatus)
    return maxOffsetHost + ": " + (Math.trunc(ntpStatus[maxOffsetHost][6] * 1000.0 * 1000.0) / 1000.0) + "ms"
}

const prettyPublishRate = function(published_at_ns) {
    if (published_at_ns.length < 2) return "?Hz"
    let periods_ns = []
    for (let i = 0; i < published_at_ns.length - 1; ++i) {
        if (i > 0 && (published_at_ns[0] - published_at_ns[i]) > 10 * 1000 * 1000 * 1000) break
        periods_ns.push(published_at_ns[i] - published_at_ns[i + 1])
    }

    avg_period_s = (periods_ns.reduce((a, b) => a + b) / periods_ns.length) / (1000.0 * 1000.0 * 1000.0)
    return "" + Math.trunc((1.0 / avg_period_s) * 1000.0) / 1000.0 + "Hz"
}

const prettyPublishPersist = function(numPublished, numPersisted) {
  return "" + numPublished + "/" + numPersisted
}

function HtmlObject(html) {
  this.html = html
}

function ImgObject(src) {
  this.src = src
}

const videoFeedImg = function(webappUrl) {
  return new ImgObject(webappUrl + "/video_jpeg")
}

const uriNodeName = function(nodeName) {
  if (nodeName.startsWith('/')) {
    return nodeName.substring(1)
  }
  return nodeName
}

const isNullOrEmptyStr = function(val) {
  return val == null || val.trim() == ""
}

const toStringy = function(val) {
  return val == null ? "" : val.trim()
}

const throwAlertResponseErr = function(response) {
  err = new Error("" + response.status + ": " + response.statusText)
  alert(err.message)
  throw err
}

const app = Vue.createApp({
    el: '#demo',
    data() {
      return {
        searchQuery: '',
        gridColumns: ['name', 'default_ip', 'max_ntp_offset', 'num_publish_persist', 'publish_rate', 'mongodb_collection', 'camera', 'feed'],
        gridData: [],
        gridSelected: {},
        isFetchingStatus: false,
        isFetchingParameters: false,
        updateParameterName: "",
        updateParameterValue: "",
        isUpdatingParameters: false,
        modalData: ["Goeff"],
        showModal: false,
      }
    },
    created: function () {
        this.fetchStatus()
    },
    methods: {
        fetchStatus(force) {
            
            if (this.isFetchingStatus) return
            this.isFetchingStatus = true

            let preFetch = Promise.resolve()
            if (force == true) {
              preFetch = fetch("api/ros/refresh", {
                            "method": "POST",
                            "headers": {}
                          })
                          .then(response => {
                            if(response.ok) {
                              return {}    
                            } else {
                                throwAlertResponseErr(response)
                            } 
                          })
            }
            
            preFetch.then(() =>
              Promise.all([
                fetch("api/ros/smart_node", {
                  "method": "GET",
                  "headers": {}
                }),
                fetch("api/ros/node", {
                  "method": "GET",
                  "headers": {}
                })]))
            .then(responses => {

                let smartResponse = responses[0]
                let response = responses[1]

                if (!smartResponse.ok)
                  throwAlertResponseErr(smartResponse)

                if (!response.ok)
                  throwAlertResponseErr(response)

                return Promise.all([smartResponse.json(), response.json()]) 
            })
            .then(jsons => {

                let smartJson = jsons[0]
                let json = jsons[1]

                const newGridData = []
                for (let key in smartJson) {
                    let value = smartJson[key]["value"]
                    value["id"] = key
                    value["name"] = key
                    value["max_ntp_offset"] = prettyMaxNtpOffset(value["ntp"])
                    value["num_publish_persist"] = prettyPublishPersist(value["num_published"], value["num_persisted"])
                    value["publish_rate"] = prettyPublishRate(value["published_at_ns"])
                    value["feed"] = videoFeedImg(value["webapp_url"])
                    newGridData.push(value)
                }
                
                for (let key in json) {
                    if (key in smartJson) continue
                    let value = json[key]
                    value["id"] = key
                    value["name"] = key
                    newGridData.push(value)
                }

                this.gridData = newGridData
            })
            .catch(err => {
                console.log(err);
            })
            .finally(() => {
                this.isFetchingStatus = false
            });
        },
        fetchParameters() {
            
          if (this.isFetchingParameters) return
          this.isFetchingParameters = true

          let fetches = []
          for (let nodeName in this.gridSelected) {

            if (!this.gridSelected[nodeName]) continue

            let nodeFetch = 
              fetch("api/ros/node_param/" + uriNodeName(nodeName), {
                "method": "GET",
                "headers": {}
              })
              .then(response => { 
                if(response.ok) {
                    return response.json()
                } else {
                  throwAlertResponseErr(response)
                } 
              })
              .then(json => {
                this.gridSelected[nodeName] = false
                return {nodeName, json}
              })

            fetches.push(nodeFetch)
          }

          Promise.all(fetches)
            .then(responses => {
              combined = {}
              responses.forEach(response => {
                combined[response.nodeName] = response.json
              })
              alert(JSON.stringify(combined))
            })
            .catch(err => {
                console.log(err);
            })
            .finally(() => {
                this.isFetchingParameters = false
            })
        },
        updateParameter() {
            
        if (this.isUpdatingParameters || isNullOrEmptyStr(this.updateParameterName)) return
        this.isUpdatingParameters = true

        let selectedNodeNames = Object.keys(this.gridSelected).filter(nodeName => this.gridSelected[nodeName])

        fetch("api/ros/param/" + toStringy(this.updateParameterName), {
            "method": "POST",
            "headers": {
              "Content-Type": "application/json"
            },
            "body": JSON.stringify({ nodes: selectedNodeNames.map(nodeName => uriNodeName(nodeName)),
                                     value: toStringy(this.updateParameterValue) })
        })
        .then(response => { 
            if(response.ok) {
              selectedNodeNames.forEach(nodeName => { this.gridSelected[nodeName] = false })
            } else {
              throwAlertResponseErr(response)
            } 
        })
        .catch(err => {
            console.log(err);
        })
        .finally(() => {
            this.isUpdatingParameters = false
        });
        },
    }
  })
  
  // register the grid component
  app.component('demo-grid', {
    template: '#grid-template',
    props: {
      rows: Array,
      columns: Array,
      selected: Object,
      filterKey: String
    },
    data() {
      const sortOrders = {};
      this.columns.forEach(function(key) {
        sortOrders[key] = 1;
      });
      return {
        sortKey: '',
        sortOrders
      }
    },
    computed: {
      filteredRows() {
        const sortKey = this.sortKey
        const filterKey = this.filterKey && this.filterKey.toLowerCase()
        const order = this.sortOrders[sortKey] || 1
        let rows = this.rows
        if (filterKey) {
          rows = rows.filter(function(row) {
            return Object.keys(row).some(function(key) {
              return (
                String(row[key])
                  .toLowerCase()
                  .indexOf(filterKey) > -1
              )
            })
          })
        }
        if (sortKey) {
          rows = rows.slice().sort(function(a, b) {
            a = a[sortKey]
            b = b[sortKey]
            return (a === b ? 0 : a > b ? 1 : -1) * order
          })
        }
        return rows
      },
      sortOrders() {
        const columnSortOrders = {}
        
        this.columns.forEach(function(key) {
          columnSortOrders[key] = 1
        })
  
        return columnSortOrders
      }
    },
    methods: {
      prettyKey(str) {
        return (str.charAt(0).toUpperCase() + str.slice(1)).replaceAll("_", " ")
      },
      sortBy(key) {
        this.sortKey = key
        this.sortOrders[key] = this.sortOrders[key] * -1
      },
      isHtmlObject(unknown) {
        try {
          return unknown instanceof HtmlObject
        } catch {
          return false
        }
      },
      isImgObject(unknown) {
        try {
          return unknown instanceof ImgObject
        } catch {
          return false
        }
      },
      showModalTest(nodeName){

        let nodeFetch = fetch("api/ros/node_param/" + uriNodeName(nodeName), {"method": "GET", "headers": {}})
                        .then(response => {
                                  if(response.ok) {
                                    return response.json()
                                  } else {
                                    throwAlertResponseErr(response)
                                  }
                                }
                             )
                        .then(json => {
                            return {nodeName, json}
                          }
                        )

        nodeFetch.then(response => {
                  nodeName = JSON.stringify(response.nodeName)
                  nodeParams = response.json//JSON.stringify(response.json)

                  this.$parent.modalData = [nodeName, nodeParams]

                  //alert(nodeParams)
                  //do the modal stuff here
               }).finally(() =>{

                  //alert(JSON.stringify(nodeFetch))
                  this.$parent.showModal = true
               })


        //alert(id)
        //alert(this.$parent.showModal)
      },
    }
  })
  

app.component("test-modal", {
  template: "#modal-template",
  props:{
    node: Array,
  },
  data:{

  },
  computed: {
    getKeys(){
      console.log(this.node)
      keys = Object.keys(this.node[1])
      console.log(keys)
      return keys
    }
  },
  methods: {
    updateParams(e){
      e.stopPropagation()
      e.preventDefault()
      alert(e)
    }
  }
})

app.mixin({
  methods: {
    isType: function (type, val) {
      if(!isNaN(parseFloat(val)) && isFinite(val)){
        if(Number.isInteger(parseFloat(val))) {
          console.log(val + " is int")
          if(type == "int") return true;
        } else {
          console.log(val + " Is float")
          if(type == "float") return true;
        }
        if(type == "numeric") return true;

        return false;
      } else if(typeof(val) == "string" && type == "string"){
        console.log(val + " Is string")
        return true;
      } else if(typeof(val) == "boolean" && type == "bool"){
          console.log(val+ " is bool") 
          return true;
      }
      return false
    },
  },
}) 

//allows $log("blah") function in HTML
app.config.globalProperties.$log = console.log
app.mount("#demo")

