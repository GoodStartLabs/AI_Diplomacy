# ==============================================================================
# Copyright (C) 2019 - Philip Paquette
#
#  This program is free software: you can redistribute it and/or modify it under
#  the terms of the GNU Affero General Public License as published by the Free
#  Software Foundation, either version 3 of the License, or (at your option) any
#  later version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#  FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
#  details.
#
#  You should have received a copy of the GNU Affero General Public License along
#  with this program.  If not, see <https://www.gnu.org/licenses/>.
# ==============================================================================
""" Convoy paths
    - Contains utilities to generate all the possible convoy paths for a given map
"""
import collections
import hashlib
import glob
import pickle
import multiprocessing
import os
from queue import Queue
import threading
import tqdm
from diplomacy.engine.map import Map
from diplomacy import settings

# Using `os.path.expanduser()` to find home directory in a more cross-platform way.
HOME_DIRECTORY = os.path.expanduser('~')
if HOME_DIRECTORY == '~':
    raise RuntimeError('Cannot find home directory. Unable to save cache')

# Constants
__VERSION__ = '20180913_0915'
COAST_TYPES = ('COAST', 'PORT')
WATER_TYPES = ('WATER', 'PORT')
MAX_CONVOY_LENGTH = 13                      # Convoys over this length are not supported, too reduce generation time

CACHE_FILE_NAME = 'convoy_paths_cache.pkl'
INTERNAL_CACHE_PATH = os.path.join(settings.PACKAGE_DIR, 'maps', CACHE_FILE_NAME)
EXTERNAL_CACHE_PATH = os.path.join(HOME_DIRECTORY, '.cache', 'diplomacy', CACHE_FILE_NAME)

def _display_progress_bar(queue, max_loop_iters):
    """ Displays a progress bar

        :param queue: Multiprocessing queue to display the progress bar
        :param max_loop_iters: The expected maximum number of iterations
    """
    progress_bar = tqdm.tqdm(total=max_loop_iters)
    for item in iter(queue.get, None):              # type: int
        for _ in range(item):
            progress_bar.update()
    progress_bar.close()

def _get_convoy_paths(map_object, start_location, max_convoy_length, queue):
    """ Returns a list of possible convoy destinations with the required units to get there
        Does a breadth first search from the starting location

        :param map_object: The instantiated map
        :param start_location: The start location of the unit (e.g. 'LON')
        :param max_convoy_length: The maximum convoy length permitted
        :param queue: Multiprocessing queue to display the progress bar
        :return: A list of ({req. fleets}, {reachable destinations})
        :type map_object: diplomacy.Map
    """
    to_check = Queue()          # Items in queue have format ({fleets location}, last fleet location)
    dest_paths = {}             # Dict with dest as key and a list of all paths from start_location to dest as value

    # To measure progress
    last_completed_path_length = 0
    nb_water_locs = len([loc.upper() for loc in map_object.locs if map_object.area_type(loc) in WATER_TYPES])

    # We need to start on a coast / port
    if map_object.area_type(start_location) not in COAST_TYPES or '/' in start_location:
        queue.put(nb_water_locs)
        return []

    # Queuing all adjacent water locations from start
    for loc in [loc.upper() for loc in map_object.abut_list(start_location, incl_no_coast=True)]:
        if map_object.area_type(loc) in WATER_TYPES:
            to_check.put(({loc}, loc))

    # Checking all subsequent adjacencies until no more adjacencies are possible
    while not to_check.empty():
        fleets_loc, last_loc = to_check.get()
        new_completed_path_length = len(fleets_loc) - 1

        # Marking path length as completed
        if new_completed_path_length > last_completed_path_length:
            queue.put(new_completed_path_length - last_completed_path_length)
            last_completed_path_length = new_completed_path_length

        # Checking adjacencies
        for loc in [loc.upper() for loc in map_object.abut_list(last_loc, incl_no_coast=True)]:

            # If we find adjacent coasts, we mark them as a possible result
            if map_object.area_type(loc) in COAST_TYPES and '/' not in loc and loc != start_location:
                dest_paths.setdefault(loc, [])

                # If we already have a working path that is a subset of the current fleets, we can skip
                # Otherwise, we add the new path as a valid path to dest
                for path in dest_paths[loc]:
                    if path.issubset(fleets_loc):
                        break
                else:
                    dest_paths[loc] += [fleets_loc]

            # If we find adjacent water/port, we add them to the queue
            elif map_object.area_type(loc) in WATER_TYPES \
                    and loc not in fleets_loc \
                    and len(fleets_loc) < max_convoy_length:
                to_check.put((fleets_loc | {loc}, loc))

    # Merging destinations with similar paths
    similar_paths = {}
    for dest, paths in dest_paths.items():
        for path in paths:
            tuple_path = tuple(sorted(path))
            similar_paths.setdefault(tuple_path, set([]))
            similar_paths[tuple_path] |= {dest}

    # Converting to list
    results = []
    for fleets, dests in similar_paths.items():
        results += [(start_location, set(fleets), dests)]

    # Marking as done
    if nb_water_locs > last_completed_path_length:
        queue.put(nb_water_locs - last_completed_path_length)

    # Returning
    return results

def _build_convoy_paths_cache(map_object, max_convoy_length):
    """ Builds the convoy paths cache for a map

        :param map_object: The instantiated map object
        :param max_convoy_length: The maximum convoy length permitted
        :return: A dictionary where the key is the number of fleets in the path and
                 the value is a list of convoy paths (start loc, {fleets}, {dest}) of that length for the map
        :type map_object: diplomacy.Map
    """
    print('Generating convoy paths for "{}"'.format(map_object.name))
    print('This is an operation that is required the first time a map is loaded. It might take several minutes...\n')
    coasts = [loc.upper() for loc in map_object.locs if map_object.area_type(loc) in COAST_TYPES and '/' not in loc]
    water_locs = [loc.upper() for loc in map_object.locs if map_object.area_type(loc) in WATER_TYPES]

    # Starts the progress bar loop
    manager = multiprocessing.Manager()
    queue = manager.Queue()
    progress_bar = threading.Thread(target=_display_progress_bar, args=(queue, len(coasts) * len(water_locs)))
    progress_bar.start()

    # Getting all paths for each coasts in parallel (except if the map is large, to avoid high memory usage)
    nb_cores = multiprocessing.cpu_count() if (len(water_locs) <= 30 or max_convoy_length <= MAX_CONVOY_LENGTH) else 1
    pool = multiprocessing.Pool(nb_cores)
    tasks = [(map_object, coast, max_convoy_length, queue) for coast in coasts]
    results = pool.starmap(_get_convoy_paths, tasks)
    pool.close()
    results = [item for sublist in results for item in sublist]
    queue.put(None)
    progress_bar.join()

    # Splitting into buckets
    buckets = collections.OrderedDict({i: [] for i in range(1, len(map_object.locs) + 1)})
    for start, fleets, dests in results:
        buckets[len(fleets)] += [(start, fleets, dests)]

    # Returning
    print('Found {} convoy paths for {}\n'.format(len(results), map_object.name))
    return buckets

def get_file_md5(file_path):
    """ Calculates a file MD5 hash

        :param file_path: The file path
        :return: The computed md5 hash
    """
    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as file:
        for chunk in iter(lambda: file.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def add_to_cache(map_name, max_convoy_length=MAX_CONVOY_LENGTH):
    """ Lazy generates convoys paths for a map and adds it to the disk cache

        :param map_name: The name of the map
        :param max_convoy_length: The maximum convoy length permitted
        :return: The convoy_paths for that map
    """
    convoy_paths = {'__version__': __VERSION__}             # Uses hash as key
    external_convoy_paths = {'__version__': __VERSION__}    # Uses hash as key

    # Loading from internal cache first
    if os.path.exists(INTERNAL_CACHE_PATH):
        try:
            cache_data = pickle.load(open(INTERNAL_CACHE_PATH, 'rb'))
            if cache_data.get('__version__', '') == __VERSION__:
                convoy_paths.update(cache_data)
        except (pickle.UnpicklingError, EOFError):
            pass

    # Loading external cache
    if os.path.exists(EXTERNAL_CACHE_PATH):
        try:
            cache_data = pickle.load(open(EXTERNAL_CACHE_PATH, 'rb'))
            if cache_data.get('__version__', '') != __VERSION__:
                print('Upgrading cache from "%s" to "%s"' % (cache_data.get('__version__', '<N/A>'), __VERSION__))
            else:
                convoy_paths.update(cache_data)
                external_convoy_paths.update(cache_data)
        except (pickle.UnpicklingError, EOFError):
            pass

    # Getting map MD5 hash
    if os.path.exists(map_name):
        map_path = map_name
    else:
        map_path = os.path.join(settings.PACKAGE_DIR, 'maps', map_name + '.map')
    if not os.path.exists(map_path):
        return None
    map_hash = get_file_md5(map_path)

    # Generating and adding to alternate cache paths
    if map_hash not in convoy_paths:
        map_object = Map(map_name, use_cache=False)
        convoy_paths[map_hash] = _build_convoy_paths_cache(map_object, max_convoy_length)
        external_convoy_paths[map_hash] = convoy_paths[map_hash]
        os.makedirs(os.path.dirname(EXTERNAL_CACHE_PATH), exist_ok=True)
        pickle.dump(external_convoy_paths, open(EXTERNAL_CACHE_PATH, 'wb'))

    # Returning
    return convoy_paths[map_hash]

def get_convoy_paths_cache():
    """ Returns the current cache from disk """
    disk_convoy_paths = {}                  # Uses hash as key
    cache_convoy_paths = {}                 # Use map name as key

    # Loading from internal cache first
    if os.path.exists(INTERNAL_CACHE_PATH):
        try:
            cache_data = pickle.load(open(INTERNAL_CACHE_PATH, 'rb'))
            if cache_data.get('__version__', '') == __VERSION__:
                disk_convoy_paths.update(cache_data)
        except (pickle.UnpicklingError, EOFError):
            pass

    # Loading external cache
    if os.path.exists(EXTERNAL_CACHE_PATH):
        try:
            cache_data = pickle.load(open(EXTERNAL_CACHE_PATH, 'rb'))
            if cache_data.get('__version__', '') == __VERSION__:
                disk_convoy_paths.update(cache_data)
        except (pickle.UnpicklingError, EOFError):
            pass

    # Getting map name and file paths
    files_path = glob.glob(settings.PACKAGE_DIR + '/maps/*.map')
    for file_path in files_path:
        map_name = file_path.replace(settings.PACKAGE_DIR + '/maps/', '').replace('.map', '')
        map_hash = get_file_md5(file_path)
        if map_hash in disk_convoy_paths:
            cache_convoy_paths[map_name] = disk_convoy_paths[map_hash]
            cache_convoy_paths[file_path] = disk_convoy_paths[map_hash]

    # Returning
    return cache_convoy_paths

def rebuild_all_maps():
    """ Rebuilds all the maps in the external cache """
    if os.path.exists(EXTERNAL_CACHE_PATH):
        os.remove(EXTERNAL_CACHE_PATH)

    files_path = glob.glob(settings.PACKAGE_DIR + '/maps/*.map')
    for file_path in files_path:
        map_name = file_path.replace(settings.PACKAGE_DIR + '/maps/', '').replace('.map', '')
        map_hash = get_file_md5(file_path)
        print('-' * 80)
        print('Adding {} (Hash: {}) to cache\n'.format(file_path, map_hash))
        add_to_cache(map_name)
