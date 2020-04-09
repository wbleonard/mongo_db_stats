// Compare Data Sizes
// listDatabases reports storageSize + indexSize
// the dataSize is uncompressed

var totalStorageSize = 0;
var totalIndexSize = 0;
var totalStorageIndexSize = 0;
var totalDataSize = 0;

db.getSiblingDB('admin').runCommand({ "listDatabases": 1 }).databases.forEach(
    function(database) { 
        // Get sizes
        storageSize = db.getSiblingDB(database.name).stats().storageSize;
        indexSize = db.getSiblingDB(database.name).stats().indexSize;
        storageIndexSize = storageSize + indexSize;
        dataSize = db.getSiblingDB(database.name).stats().dataSize;
        compression = ((1 - storageSize/dataSize)*100).toFixed(2);
        
        // Convert to MB
        storageSizeMB = (storageSize/1024/1024).toFixed(3);
        indexSizeMB = (indexSize/1024/1024).toFixed(3);
        storageIndexSizeMB = ((storageSize+indexSize)/1024/1024).toFixed(3);
        dataSizeMB = (dataSize/1024/1024).toFixed(3);

        // Print
        print(database.name)
        print(`  ${storageSizeMB} MB - storageSize`);
        print(`  ${indexSizeMB} MB - indexSize`);
        print(`  ${storageIndexSizeMB} MB - storageSize + indexSize`);
        print(`  ${dataSizeMB} MB - dataSize (uncompressed storageSize - excludes indexes)`);
        print(`  ${storageIndexSize} bytes - storageSize + indexSize (compressed - should match value as reported by listDatabases)`);
        print(`  ${database.sizeOnDisk} bytes - sizeOnDisk from listDatabases (compressed)`);
        print(`  ${compression}% compression (dataSize -> storageSize)`);
        print();

        totalStorageSize += storageSize;
        totalIndexSize += indexSize;        
        totalStorageIndexSize += storageIndexSize;
        totalDataSize += dataSize;
});

var totalCompression = ((1 - totalStorageSize/totalDataSize)*100).toFixed(2);

print ('=== Cluster Totals ===');
print('\n--- DB Storage ---');
print(`${(totalStorageSize/1024/1024/1024).toFixed(3)} GB - Total storageSize`);
print(`${(totalIndexSize/1024/1024/1024).toFixed(3)} GB - Total indexSize`);
print(`${(totalStorageIndexSize/1024/1024/1024).toFixed(3)} GB - Total storageSize + indexSize`);
print(`${(totalDataSize/1024/1024/1024).toFixed(3)} GB - Total dataSize (uncompressed storageSize - excludes indexes)`);
print(`${totalCompression}% compression (total dataSize -> total storageSize)`);
print('\n--- Reconcilation ---');
print(`${totalStorageIndexSize} bytes - Total storageSize + indexSize (compressed - should match value reported by listDatabases)`);
print(`${db.getSiblingDB('admin').runCommand({ "listDatabases": 1 }).totalSize} bytes - from db.adminCommand( { listDatabases: 1 } )`);
var fsUsedSizeGB = (db.getSiblingDB('admin').runCommand({ "dbStats": 1 }).fsUsedSize/1024/1024/1024).toFixed(3)
var fsTotalSizeGB = (db.getSiblingDB('admin').runCommand({ "dbStats": 1 }).fsTotalSize/1024/1024/1024).toFixed(3)
var percentFsUsed = (fsUsedSizeGB/fsTotalSizeGB*100).toFixed(2);
print('\n-- Disk Space Used ---');
print(`${fsUsedSizeGB} GB - Total File System Used`);
print(`${fsTotalSizeGB} GB - Total File System Size`);
print(`${percentFsUsed}% File System Used `);







