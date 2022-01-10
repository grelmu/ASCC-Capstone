
conn = null
status = null

for (var i = 0; i < 1000 && status == null; ++i) {

    try {

        conn = Mongo("localhost:27017")
        db = conn.getDB("admin")

        username = _getEnv('MONGO_INITDB_ROOT_USERNAME');
        password = _getEnv('MONGO_INITDB_ROOT_PASSWORD');
        if (username) {
            print("  Authenticating to determine rs status...")
            db.getSiblingDB("admin").auth(username, password);
        }

        status = rs.status();
        print(JSON.stringify(status));
    }
    catch (ex) {
        print(ex);
        print("  Waiting for successful rs status...");
        sleep(1000);
    }
}

if (status.codeName == "NotYetInitialized") {
    config = JSON.parse(_getEnv('MONGO_INITRS_CONFIG'))
    print(JSON.stringify(rs.initiate(config)));
}
