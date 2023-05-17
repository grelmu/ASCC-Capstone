# Material Process-Property Warehouse (MPPW)

The MPPW is a web-based data platform intended to be used for planning, organization, storage, and analysis of manufacturing processes and material science experiments. Processes and experiments are stored as highly configurable "digital threads" of simulation and physical results, allowing material property or other experimental results to be linked back to build process data.

In addition, a digital thread is a powerful planning abstraction for manufacturing, allowing manufacturing operations and experiments to be fully defined before real-world actions begin.

At the highest level, the MPPW consists of three loosely-coupled components:

- An API, backed by a (MongoDB) database and hosted via a web server (nginx), providing manufacturing data services.

- A UI, backed by the API, providing data exploration and data entry interfaces.

- An analysis sandbox, backed by a scripting platform (JupyterHub) and integrated with the API, packaging researcher data analysis scripts as well as user-driven automation scripts.

More information around the software design is in the [architecture section](./architecture.md).

# For software and data integrators

* The [deployment section](./deploy.md) describes how to setup and deploy the MPPW stack.
* The [sensor data integration section](./data_integration/sensor_data.md) shows how to ingest data from manufacturing or other processes into the warehouse.

# For project administrators

* The [tutorial section](./tutorial/create_a_project.md) has an overview of how to set up a new project in the MPPW and define data collection operation and artifact schemas.

# For scientists and researchers

* The [data entry](./data_integration/data_entry.md) section introduces data collection via file and other web UIs. 

TODO: Add more focused links here

