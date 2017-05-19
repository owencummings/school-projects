from math import radians, cos, sin, asin, sqrt
import sqlite3
import json
import re
import os

# Alex Qian-Wang and Owen Cummings (alexqw and ocummings)

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

# Use these filenames to open the database and the json file
DATABASE_FILENAME = os.path.join(DATA_DIR, 'courses.db')
CATALOG_FILENAME = os.path.join(DATA_DIR, 'catalog_index.json')

def find_courses(args_from_ui):
    info = args_from_ui
    if info == {}:
        return ([], [])
    courses_from_search = set()
    select_string, select_list = find_variables(info)
    sections_from_query = list(set(make_query(select_string, info)))
    if sections_from_query == []:
        return ([], [])
    if info.has_key('terms'):
        courses_from_search = search(info['terms'])
        query_dict = make_query_dict(sections_from_query)
        final_rv = look_in_dict(courses_from_search, query_dict, select_list)
        return final_rv
    return (select_list, sections_from_query)

def search(term):
    f = open(CATALOG_FILENAME, 'r')
    index = json.load(f)
    all_sets = []
    words = re.findall("[a-zA-Z]\w*", term)
    if len(words) == 0:
        return []
    for word in words:
        word = word.lower()
        search_set = set()
        for key in index.keys():
            if word == key:
                for course in index[key]:
                    course_tuple = tuple(course)
                    search_set.add(course_tuple)
        all_sets.append(search_set)
    courses_from_search = set.intersection(*all_sets)
    return courses_from_search

def make_query_dict(sections_from_query):
    if len(sections_from_query) == 0:
        return {}
    query_dict = {}
    i = 0
    for section in sections_from_query:
        dept = section[0]
        num = section[1]
        dept_and_num = (dept, num)
        if query_dict.has_key(dept_and_num):
            duplicate_key = (dept + str(i), num)
            if not query_dict.has_key(duplicate_key):
                query_dict[duplicate_key] = section
        else:
            query_dict[dept_and_num] = section
        i = i + 1
    return query_dict

def look_in_dict(courses_from_search, query_dict, select_list):
    if query_dict == {}:
        return ([], [])
    section_list = []
    for course in courses_from_search:
        for key in query_dict.keys():
            dept = key[0]
            num = key[1]
            if course == key or course == (dept[:-1], num) or course == (dept[:-2], num) or course == (dept[:-3], num) or course == (dept[:-4], num):
                if query_dict[key] not in section_list:
                    section_list.append(query_dict[key])
    if section_list == []:
        return ([], [])
    final_rv = (select_list, section_list)
    return final_rv

def find_variables(info):
    s = 'a.dept, a.course_num'
    l = ['dept', 'course_num']
    if info.has_key('section_num') or info.has_key('day') or info.has_key('time_start') or info.has_key('walking_time') or info.has_key('building') or info.has_key('enroll_lower') or info.has_key('enroll_upper'):
        s = s + ', b.section_num, b.day, b.time_start, b.time_end'
        l.append('section_num')
        l.append('day')
        l.append('time_start')
        l.append('time_end')
    if info.has_key('walking_time') or info.has_key('building'):
        s = s + ', b.building, compute_time_between(c.lon, c.lat, d.lon, d.lat)'
        l.append('building')
        l.append('walking_time')
    if info.has_key('enroll_lower') or info.has_key('enroll_upper'):
        s = s + ', b.enroll'
        l.append('enrollment')
    if info.has_key('terms') or info.has_key('dept'):
        s = s + ', a.title'
        l.append('title')
    return s, l

def make_query(select_variables, info):
    db = sqlite3.connect(DATABASE_FILENAME)
    db.create_function("compute_time_between", 4, compute_time_between)
    c = db.cursor()
    s0 = '''SELECT ''' + select_variables
    s1 = ''' FROM course AS a JOIN section AS b ON a.course_id = b.course_id JOIN gps AS c ON b.building = c.building INNER JOIN gps AS d WHERE '''
    s2 = ''''''
    where_arguments = []
    i = 0
    keys_list = info.keys()
    if len(keys_list) == 1 and keys_list[0] == 'terms':
        s = '''SELECT a.dept, a.course_num, a.title FROM course AS a JOIN section AS b ON a.course_id = b.course_id'''
        r = c.execute(s, where_arguments).fetchall()
        return r
    for key in keys_list:
        if key == 'dept':
            s2 = s2 + 'dept = ?'
            where_arguments.append(info['dept'])
        elif key == 'day':
            day_string = '('
            j = 0
            for day in info['day']:
                day_string = day_string + 'day = ?'
                where_arguments.append(info['day'][j])
                if j < len(info[key]) - 1:
                    day_string = day_string + ' OR '
                j = j + 1
            day_string = day_string + ')'
            s2 = s2 + day_string
        elif key == 'time_start':
            s2 = s2 + 'time_start >= ?'
            where_arguments.append(info['time_start'])
        elif key == 'time_end':
            s2 = s2 + 'time_end <= ?'
            where_arguments.append(info['time_end'])
        elif key == 'walking_time':
            s2 = s2 + 'd.building = ? AND compute_time_between(c.lon, c.lat, d.lon, d.lat) <= ?'
            where_arguments.append(info['building'])
            where_arguments.append(info['walking_time'])
        elif key == 'enroll_lower':
            s2 = s2 + 'enroll >= ?'
            where_arguments.append(info['enroll_lower'])
        elif key == 'enroll_upper':
            s2 = s2 + 'enroll <= ? AND enroll > -1'
            where_arguments.append(info['enroll_upper'])
        else:
            i = i + 1
            continue
        if i < len(keys_list) - 1:
            s2 = s2 + ' AND '
        i = i + 1
    s = s0 + s1 + s2
    r = c.execute(s, where_arguments).fetchall()
    return r

########### auxiliary functions #################
########### do not change this code #############

def compute_time_between(lon1, lat1, lon2, lat2):
    '''
    Converts the output of the haversine formula to walking time in minutes
    '''
    meters = haversine(lon1, lat1, lon2, lat2)

    #adjusted downwards to account for manhattan distance
    walk_speed_m_per_sec = 1.1
    mins = meters / (walk_speed_m_per_sec * 60)

    return mins


def haversine(lon1, lat1, lon2, lat2):
    '''
    Calculate the circle distance between two points
    on the earth (specified in decimal degrees)
    '''
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    # 6367 km is the radius of the Earth
    km = 6367 * c
    m = km * 1000
    return m 
