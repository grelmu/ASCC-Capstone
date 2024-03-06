
db = db.getSiblingDB("admin")

username = _getEnv('MONGO_INITDB_ROOT_USERNAME');
password = _getEnv('MONGO_INITDB_ROOT_PASSWORD');
if (username) {
    print("  Authenticating to determine rs status...")
    db.getSiblingDB("admin").auth(username, password);
}

// FAILS if not initialized with rs options, as in the initdb phase
status = rs.status();
print(JSON.stringify(status));

if (status.codeName == "NotYetInitialized") {
    config = JSON.parse(_getEnv('MONGO_INITRS_CONFIG'))
    print(JSON.stringify(rs.initiate(config)));
}
else if (status.members == undefined) {
    msg = "Replication state not stable - wait for full startup.";
    print(msg);
    throw new Error(msg);
}