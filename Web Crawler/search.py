# CS122 W'15
# Course search engine
#
# Alex Qian-Wang (alexqw)
# Owen Cummings (ocummings)

import re
import util
import bs4
import Queue

def build_course_search_engine(N):
    '''
    Build a search engine for courses from the 122 shadow copy of the catalog.

    Inputs:
      N - the maximum of pages to crawl number

    outputs:

      function that takes a search string and returns the titles and
      URLs of courses that match the search string
    '''

    starting_url = "http://www.classes.cs.uchicago.edu/archive/2015/winter/12200-1/new.collegecatalog.uchicago.edu/index.html"
    limiting_domain = "cs.uchicago.edu"
    return build_search_engine(starting_url, limiting_domain, N)


def build_cs_course_search():
    '''
    Function useful for testing indexing on a single page.
    '''
    starting_url = "http://www.classes.cs.uchicago.edu/archive/2015/winter/12200-1/new.collegecatalog.uchicago.edu/thecollege/computerscience/index.html"
    limiting_domain = "cs.uchicago.edu"
    return build_search_engine(starting_url, limiting_domain, 1)



def build_search_engine(starting_url, limiting_domain, max_num_pages_to_visit):
    urls = Queue.Queue()
    visited = []
    index = {}
    def search(word):
        rv = []
        matches = []
        words = re.findall("[a-zA-Z]\w*", word)
        if len(words) == 0:
            return []
        for url in index.keys():
            for title in index[url].keys():
                for word in words:
                    word = word.lower()
                    if word in title or word in index[url][title]:
                        matches.append((title, url))
        for pair in matches:
            if matches.count(pair) == len(words):
                if pair not in rv:
                    rv.append(pair)
        return rv
    if util.is_url_ok_to_follow(starting_url, limiting_domain):
        urls.put(starting_url)
        while not urls.empty() and len(visited) < max_num_pages_to_visit:
            top_queue = urls.get()
            if top_queue not in visited and util.is_url_ok_to_follow(top_queue, limiting_domain):
                request = util.get_request(top_queue)
                if request == None:
                    visited.append(top_queue)
                    continue
                new_page = util.get_request_url(request)
                if new_page != top_queue:
                    if new_page not in visited:
                        visited.append(new_page)
                        top_queue = new_page
                data = bs4.BeautifulSoup(util.read_request(request))
                visited.append(top_queue)
                index = indexer(index, top_queue, data)
                for link in data.find_all('a'):
                    href = link.get('href')
                    if href == None:
                        continue
                    href = util.remove_fragment(href)
                    if not util.is_absolute_url(href):
                        url = util.convert_if_relative_url(top_queue, href)
                    urls.put(url)
    else:
        return None
    return search


def indexer(url_dict, page, data):
    course_blocks = data.find_all('div', class_= 'courseblock main')
    if len(course_blocks) == 0:
        return url_dict
    course_titles = []
    course_descs = []
    for block in course_blocks:
        for tag in util.find_sequence(block):
            if util.is_subsequence(tag):
                for line in block.find_all(tag, class_='courseblocktitle'):
                    course_titles.append(line.get_text().lower())
                for line in block.find_all(tag, class_='courseblockdesc'):
                    course_descs.append(line.get_text().lower())
        for line in block.find_all('p', class_='courseblocktitle'):
            course_titles.append(line.get_text().lower())
        for line in block.find_all('p', class_='courseblockdesc'):
            course_descs.append(line.get_text().lower())
    if len(course_titles) == 0 or len(course_descs) == 0:
        return url_dict
    url_dict[page] = {}
    pairs = zip(course_titles, course_descs)
    for pair in pairs:
        url_dict[page][pair[0]] = pair[1]
    return url_dict
