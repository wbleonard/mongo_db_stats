import params
import json
import datetime
import time
import pprint
import pymongo
from pymongo import MongoClient

print("\nMongoDB Database Stats\n")

# Establish connections to Atlas
target_client = MongoClient(params.target_conn_string)

# Get target cluster name
admin_db = target_client ['admin']
target_cluster_name = admin_db.command({'replSetGetStatus' :1})["set"]

result_client = MongoClient(params.results_conn_string)
result_db = result_client[params.results_database]

timestamp = datetime.datetime.now()

# Set up PrettyPrinter
pp = pprint.PrettyPrinter(depth=6)

# A placehold for the result
result = {}

def analyze_db_cache():

    print("Analyzing Database Cache Use for Cluster '" + target_cluster_name + "'...\n")

    dbNames = target_client.list_database_names()

    for dbName in dbNames:

        result['cluster_name'] = target_cluster_name
        result['db'] = dbName
        result['db_cache_bytes'] = 0
        result['collections'] = []
        result['timestamp'] = timestamp

        db = target_client[dbName]
        dbCacheBytes = 0

        collsCursor = db.list_collections()

        for coll in collsCursor:

            if coll["type"] == "collection":

                collName = coll['name']

                stats = db.command("collstats", collName)

                collStats = {}

                collStats['collection_name'] = collName
                collStats['cache_bytes'] = stats["wiredTiger"]["cache"]['bytes currently in the cache']

                dbCacheBytes = dbCacheBytes + collStats['cache_bytes']
                result['collections'].append(collStats)

            # Endif
        # end collsCursor for

        result['db_cache_bytes'] = dbCacheBytes
        result_db.cache_stats.insert_one(result.copy())

    # end dbNames for
  # end analyze_db_cache()

# analyze the cache results
def print_db_cache_row(database, cache):
        print(" %-25s %10s" % (database, cache))


def print_db_cache_results():
    db_cache = result_db.cache_stats.find({'timestamp':timestamp, 'db_cache_bytes':{'$gt':1024*1024}}, {'_id':0, 'db':1, 'db_cache_bytes':1}).sort('db_cache_bytes',-1)

    print_db_cache_row("Database", "Cache Used (MB)")
    print_db_cache_row("--------", "---------------")

    for db in db_cache:
        
        # size up to MB
        cache = round(db['db_cache_bytes']/1024/1024, 3)

        print_db_cache_row(db['db'], cache)
    # end for

    # Calculate the total
    match_stage = {'$match': {'timestamp': timestamp}}
    group_stage = {'$group': {'_id': '$timestamp', 'total': { '$sum': '$db_cache_bytes'  } } }   
    db_total_cache = result_db.cache_stats.aggregate([match_stage, group_stage])

    print_db_cache_row("--------", "---------------")

    for total in db_total_cache:
        print_db_cache_row("Total", round(total['total']/1024/1024, 3) )

def analyze_db_collections():
    print("Analyzing Database Collection Stats for Cluster '" + target_cluster_name + "'...\n")

    dbNames = target_client.list_database_names()

    for dbName in dbNames:

        result['cluster_name'] = target_cluster_name
        result['db'] = dbName
        result['collections'] = []
        result['timestamp'] = timestamp

        db = target_client[dbName]
        dbStorageSize = 0
        dbIndexSize = 0

        collsCursor = db.list_collections()

        for coll in collsCursor:

            if coll["type"] == "collection":

                collName = coll['name']

                stats = db.command("collstats", collName)

                collStats = {}

                try:
                    collStats['collection_name'] = collName
                    collStats['numberOfDocuments'] = stats["count"]
                    collStats['averageDocumentSize'] = stats["avgObjSize"]
                    collStats['storageSize'] = stats["storageSize"]
                    collStats['freeStorageSize'] = stats["freeStorageSize"]
                    collStats['numberOfIndexes'] = stats["nindexes"]
                    collStats['totalIndexSize'] = stats["totalIndexSize"]

                    dbStorageSize = dbStorageSize + collStats['storageSize']
                    dbIndexSize = dbIndexSize + collStats['totalIndexSize']
                    result['collections'].append(collStats)
                except KeyError:
                    continue

            # Endif
        # end collsCursor for

        result['db_storage_size'] = dbStorageSize
        result['db_index_size'] = dbIndexSize
        result_db.collection_stats.insert_one(result.copy())

    # end dbNames for
  # end analyze_db_collections()


# Roughly based on hottest collections solution from Compass
# https://github.com/mongodb-js/compass-serverstats/blob/master/src/stores/top-store.js#L86
def analyze_db_cpu():

    print("\nCalculating Hottest DBs for Cluster '" + target_cluster_name + "'...\n")

    admin_db = target_client['admin']

    totals = admin_db.command("top")['totals']
  
    poll_interval_secs = 1
    t1s = {}

    # Collect current load values for a collections..
    for collName in totals:

        if collName == 'note':
            continue

        t1s[collName] = {'loadPercentR' : totals[collName]['readLock']['time'],  
            'loadPercentW' : totals[collName]['writeLock']['time'], 
            'loadPercent' : totals[collName]['total']['time']}

    # end current values for

    # Sleep for 1 second and the grab another snapshot
    time.sleep(poll_interval_secs)
    totals2 = admin_db.command("top")['totals']
    tdiff = {}

    # Collect new load values for all collections and store the diffs...
    for collName in totals2:

        if collName == 'note':
            continue

        total_delta = totals2[collName]['total']['time'] - totals[collName]['total']['time']
        read_delta =  totals2[collName]['readLock']['time'] - totals[collName]['readLock']['time']  
        write_delta = totals2[collName]['writeLock']['time'] - totals[collName]['writeLock']['time']

        # Only track collections w/ values...
        if total_delta: 
            tdiff[collName] = {'read_time_diff' : read_delta,  
                'write_time_diff' : write_delta, 
                'total_time_diff' : total_delta}

    # end diff collection for

    t_roll_up = {}
    prev_db_name = ""

    # roll-up collection values
    for coll_name in tdiff:

        names = coll_name.split('.')
        db_name = names[0]

        if db_name == prev_db_name:
            t_roll_up[db_name]['total_time_diff'] = t_roll_up[db_name]['total_time_diff'] + tdiff[coll_name]['total_time_diff']
            t_roll_up[db_name]['read_time_diff'] = t_roll_up[db_name]['read_time_diff'] + tdiff[coll_name]['read_time_diff']
            t_roll_up[db_name]['write_time_diff'] = t_roll_up[db_name]['write_time_diff'] + tdiff[coll_name]['write_time_diff']

        else:
            t_roll_up[db_name] = tdiff[coll_name]      

        prev_db_name = db_name

    # Convert diff roll-up values to percentages

    db_percent = {}
    cadence = 1000000 * poll_interval_secs # Can safely assume we're polling 1x/sec TODO
    num_cores = admin_db.command('hostInfo')['system']['numCores']

    for db_name in t_roll_up:

        total_time_diff = t_roll_up[db_name]['total_time_diff']
        loadPercent = round((total_time_diff * 100) / (cadence * num_cores), 2)
        readPercent = t_roll_up[db_name]['read_time_diff'] / total_time_diff * 100
        writePercent = t_roll_up[db_name]['write_time_diff'] / total_time_diff * 100

        db_percent[db_name] = {'loadPercent' : loadPercent, 
            'readPercent' : round(readPercent * loadPercent/100, 2),
            'writePercent': round(writePercent * loadPercent/100, 2) }

    # end roll_up for
       
    # Persist to MongoDB

    # A placehold for the result
    result = {}

    for db_name in db_percent:
        result['cluster_name'] = target_cluster_name
        result['db'] = db_name
        result['db_load_percent'] = db_percent[db_name]['loadPercent']
        result['db_read_percent'] = db_percent[db_name]['readPercent']
        result['db_write_percent'] = db_percent[db_name]['writePercent']
        result['timestamp'] = timestamp

        result_db.hottest_dbs.insert_one(result.copy())

# analyze the hottest db results
def print_hot_db_row(database, total, read, write):
        print(" %-25s %10s %10s %10s" % (database, total, read, write) )

def print_hot_db_results():
    hot_dbs = result_db.hottest_dbs.find({'timestamp':timestamp, 'db_load_percent':{'$gt':0}}, {'_id':0}).sort('db_load_percent',-1)

    print_hot_db_row("Database", "CPU", "CPU Read", "CPU Write")
    print_hot_db_row("--------", "---------", "---------", "---------")

    for db in hot_dbs:

        print_hot_db_row( db['db'], str(db['db_load_percent']) + '%', str(db['db_read_percent']) + '%', str(db['db_write_percent']) + '%' )        
    
    # end for

    # Calculate the totals
    match_stage = {'$match': {'timestamp': timestamp}}
    group_stage = {'$group': {'_id': '$timestamp', 'total': { '$sum': '$db_load_percent'  }, 'read_total': { '$sum': '$db_read_percent'  }, 'write_total': { '$sum': '$db_write_percent'  } } }   
    db_total_cpu = result_db.hottest_dbs.aggregate([match_stage, group_stage])

    print_hot_db_row("--------", "---------", "---------", "---------")

    for total in db_total_cpu:
        total_cpu = str( round(total['total'], 2) ) + '%'
        read_total = str(round(total['read_total'], 2) ) + '%'
        write_total = str( round(total['write_total'], 2) ) + '%'
        print_hot_db_row("Total", total_cpu, read_total , write_total )

analyze_db_collections()
analyze_db_cache()
print_db_cache_results()
analyze_db_cpu()
print_hot_db_results()

print("\nAnalysis Complete")
