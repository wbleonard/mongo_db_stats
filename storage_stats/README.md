# MongoDB Storage Statistics

It's often important to understand the storage usage statistic of your MongoDB cluster. This is easy to determine if your cluster is managed by [Ops Manager](https://www.mongodb.com/products/ops-manager) or [Cloud Manager](https://www.mongodb.com/cloud/cloud-manager), or even better if you're using [Atlas](https://www.mongodb.com/cloud/atlas).

However, if you're just running the Community Edition, you've left to using commands such as [dbStats](https://docs.mongodb.com/manual/reference/command/dbStats/) to get this kind of information. 

This [storage-stats.js](storage-stats.js) will show the storage statistics for each database in the cluster. For example:

```
sample_mflix
  27.430 MB - storageSize
  14.297 MB - indexSize
  41.727 MB - storageSize + indexSize
  49.895 MB - dataSize (uncompressed storageSize - excludes indexes)
  43753472 bytes - storageSize + indexSize (compressed - should match value as reported by listDatabases)
  43753472 bytes - sizeOnDisk from listDatabases (compressed)
  45.03% compression (dataSize -> storageSize)
```
as well as the overall total storage statistics:

```
=== Cluster Totals ===

--- DB Storage ---
0.568 GB - Total storageSize
0.077 GB - Total indexSize
0.645 GB - Total storageSize + indexSize
1.595 GB - Total dataSize (uncompressed storageSize - excludes indexes)
64.41% compression (total dataSize -> total storageSize)

--- Reconcilation ---
692060160 bytes - Total storageSize + indexSize (compressed - should match value reported by listDatabases)
692060160 bytes - from db.adminCommand( { listDatabases: 1 } )

-- Disk Space Used ---
7.162 GB - Total File System Used
99.951 GB - Total File System Size
7.17% File System Used
```

To run it from the shell, just > `load('storage-stats.js')`

Another great resource of interest are these [DB Storage Tools](https://github.com/tap1r/mongodb-scripts/blob/master/DB%20Storage%20tools.md).