import datetime
import json
import os
import re
import sys
import xbmc
import xbmcgui 
import xbmcaddon
try:
    import requests
    import simplejson
    import trakt
    from trakt import users
    from bs4 import BeautifulSoup
except:
    if os.name == "nt":
        slash = "\\"
    else:
        slash = "/"
    sys.path.append(os.path.abspath(os.path.dirname(__file__)+slash+"resources"+slash+"lib"))
    import requests
    import simplejson
    import trakt
    from trakt import users
    from bs4 import BeautifulSoup

try:
    from hashlib import sha1
except ImportError:
    from sha import new as sha1


__settings__ = xbmcaddon.Addon()
__language__ = __settings__.getLocalizedString
c_refresh = __settings__.getSetting("32012")
c_runasservice = __settings__.getSetting("32011")
start_time = datetime.datetime.now()
service_interval = int(c_refresh)*360  # seconds
micronap = 500  # milliseconds


def _getstr(id):
    return str(__language__(id))

if len(sys.argv) != 2:
    xbmc.sleep(1000)
    xbmc.log(msg="TAG-GEN: Starting as a service.", level=xbmc.LOGNOTICE)

###################################################################
############################ FUNCTIONS ############################
###################################################################
#test for interwebs
def internet_test(url):
    try:
        response = requests.get(url, timeout=5)
        return True
    except Exception as e:
        pass
    if len(sys.argv) == 2:
        dialog = xbmcgui.Dialog() 
        ok = dialog.ok(_getstr(30000),url + _getstr(30001))
    xbmc.log(msg="TAG-GEN: " + str(url) + " unreachable. Check network and retry.", level=xbmc.LOGERROR)
    sys.exit(1)


# cancels script
def ifcancel():
    if len(sys.argv) == 2:
        if (pDialog.iscanceled()):
            xbmc.log(msg="TAG-GEN: Cancel received from Kodi dialog, exiting.", level=xbmc.LOGNOTICE)
            sys.exit(0)


#def to make a debug log
def debuglog(string):
    if "true" in c_debug:
        xbmc.log(msg=string,level=xbmc.LOGNOTICE)


def notify(input):
    icon = os.path.abspath(os.path.dirname(__file__)) + slash + 'icon.png'
    xbmc.executebuiltin("Notification(Tag Generator," + str(input) + ",5," + icon + ")")


# A function to overwrite EVERY tag found in the database with a blank [] tag.    
def wipealltags():
    counter = 0
    medialist = getxbmcdb()
    for movie in medialist:
        ifcancel()
        json_query = '{"jsonrpc": "2.0", "id": "libMovies", "method": "VideoLibrary.SetMovieDetails", ' \
                     '"params": {"movieid" : replaceid, "tag":[]}}'
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        xbmcid = (json.dumps(movie.get('xbmcid', '')))
        json_query = re.sub('replaceid', xbmcid, json_query)
        jsonobject = simplejson.loads(xbmc.executeJSONRPC(json_query))
        if len(sys.argv) == 2:
            counter = counter + 1
            percent = (100 * int(counter) / int(len(medialist)))
            pDialog.update(percent, " ", _getstr(30002) + str(counter) + "/" + str(len(medialist)) + _getstr(30003))
    return counter


# dump the entire XBMC library to a big fat python list of dicts
def getxbmcdb():
    if "true" in wipeout:
        pDialog.update(0, _getstr(30004), " ", " ")
    elif len(sys.argv) == 2:
        pDialog.update(0, _getstr(30005), " ", " ")
    # json # convert to unicode # create json
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties" : '
                                     '["title","studio","tag","imdbnumber","year"], "sort": {"order": "ascending", '
                                     '"method": "label", "ignorearticle": true}}, "id": "libMovies"}')
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    jsonobject = simplejson.loads(json_query)
    # create media list
    medialist = []
    # if json has key == movies
    if jsonobject['result'].has_key('movies'):
        # for each movie in json
        for item in jsonobject['result']['movies']:
            ifcancel()
            # append new movie to Medialist
            medialist.append({'xbmcid': item.get('movieid', ''), 'imdbid': item.get('imdbnumber', ''), 'name':
            item.get('label', ''), 'tag': item.get('tag', ''), 'year': item.get('year', '')})
    return medialist


# write tags for locally found movies given a Trakt watchlist, local media list and the new tag to write
def write_trakt_tags(traktlist, medialist, newtrakttag):
    if len(sys.argv) == 2:
        pDialog.update(0,_getstr(30006), " ", " ")
    moviecount = 0
    counter = 0
    for traktimdbid in traktlist:
        ifcancel()
        counter = counter + 1
        for movie in medialist:
            xbmcimdbid = (json.dumps(movie.get('imdbid','')))
            xbmcid = (json.dumps(movie.get('xbmcid','')))
            xbmctag = (json.dumps(movie.get('tag','')))
            xbmcname = (json.dumps(movie.get('name','')))
            if (traktimdbid in xbmcimdbid) and (newtrakttag not in xbmctag):
                moviecount = moviecount + 1
                percent = (100 * int(counter) / int(len(traktlist)))
                if len(sys.argv) == 2:
                    pDialog.update(percent, "", "", _getstr(30007) + str(newtrakttag) + _getstr(30008) + str(moviecount)
                                   + _getstr(30010))
                debuglog('TAG-GEN: Writing tag "' + newtrakttag + '" to Trakt movie: ' + xbmcname)
                writetags(xbmcid, newtrakttag, xbmctag[1:-1])
            else:
                percent = (100 * int(counter) / int(len(traktlist)))
                debuglog("TAG-GEN: Not writing tag: " + newtrakttag + " to movie: " + xbmcname + " with existing tag: "
                         + xbmctag)
            if len(sys.argv) == 2:
                pDialog.update(percent, "", _getstr(30009) + str(counter) + "/" + str(len(traktlist)) + _getstr(30010))
    return moviecount

    
# Return imdb ids for movies in a given trakt list. Requires oauth token.
def get_trakt_movies(user_name, list_name, token):
    trakt.core.AUTH_METHOD = trakt.core.OAUTH_AUTH
    trakt.core.OAUTH_TOKEN = token
    trakt.core.CLIENT_ID = trakt_client_id
    trakt.core.CLIENT_SECRET = trakt_client_secret
    target_list = list()
    if list_name.lower() == "watchlist":
        target_list = users.User(user_name).watchlist_movies
    else:
        target_list = users.User(user_name).get_list(list_name).get_items()
    found_ids = list()
    for item in target_list:
        imdb_id = item.ids["ids"]["imdb"]
        if not imdb_id in found_ids:
            found_ids.append(imdb_id)
            debuglog("TAG-GEN: Found Trakt movie " + (str(item)) + " in Trakt List: " + list_name)
    return found_ids


# Write tags via json. Requires the xbmcid, the existing xbmctag and the new tag
def writetags(xbmcid, newtag, xbmctag):
    ifcancel()
    jsonurl = '{"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : replaceid, "tag":replacetag}}'
    jsonurl = re.sub('replaceid', xbmcid, jsonurl)
    if len(xbmctag) > 2:
        jsonurl = re.sub('replacetag', '[' + xbmctag + "," + '"' + newtag + '"]', jsonurl)
    else:
        jsonurl = re.sub('replacetag', '["' + newtag + '"]', jsonurl)
    jsonresponse = simplejson.loads(xbmc.executeJSONRPC(jsonurl))


# Scrapes IMDB given a URL and a scrape count (counter for how many times it has run)
def scrapeimdb(imdburl, scrapecount):
    internet_test("http://www.imdb.com")
    if len(sys.argv) == 2:
        pDialog.update(0,_getstr(30011)," ", " ")
    ifcancel()
    try:
        imdbpage = requests.get(imdburl).text
        imdbuser = re.findall(r'<title>(.+?)</title>', imdbpage)
        if imdbuser[0] == "Your Watchlist - IMDb":
            imdbuser = str(imdbuser[1])
        else:
            imdbuser = str(imdbuser[0])
        imdblist = re.findall(r'"(tt[0-9]{7})"', imdbpage)
        imdblist = sorted(set(imdblist))
        debuglog("TAG-GEN: Found these IMDB tags on " + str(imdbuser) + ": " + str(imdburl) + ": " + str(imdblist))
        return imdblist, imdbuser
    except Exception as e:
        if len(sys.argv) == 2:
            dialog = xbmcgui.Dialog()
            ok = dialog.ok(_getstr(30000), imdburl + _getstr(30012))
        xbmc.log(msg="TAG-GEN: " + imdburl + " contains no IMDB IDs. Check URL and retry.",level=xbmc.LOGERROR)
        debuglog("TAG-GEN: " + str(e))
        sys.exit(1)


# write tags for locally found movies given an imdb watchlist, local media list and the new tag to write
def writeimdbtags(imdblist, medialist, newimdbtag):
    if len(sys.argv) == 2:
        pDialog.update(0, _getstr(30013) + str(imdbuser))
    moviecount = 0
    counter = 0
    for webimdbid in imdblist:
        ifcancel()
        counter = counter + 1
        for movie in medialist:
            xbmcimdbid = (json.dumps(movie.get('imdbid', '')))
            xbmcid = (json.dumps(movie.get('xbmcid', '')))
            xbmctag = (json.dumps(movie.get('tag', '')))
            xbmcname = (json.dumps(movie.get('name', '')))
            if (webimdbid in xbmcimdbid) and (newimdbtag not in xbmctag):
                moviecount = moviecount + 1
                debuglog("TAG-GEN: Writing tag: " + newimdbtag +
                         " to IMDB movie: " + xbmcname +
                         " from " + str(imdbuser))
                percent = (100 * int(counter) / int(len(imdblist)))
                if len(sys.argv) == 2:
                    pDialog.update(percent, "", "", _getstr(30014) + str(newimdbtag) + _getstr(30015) + str(moviecount)
                                   + _getstr(30016))
                writetags(xbmcid, newimdbtag, xbmctag[1:-1])
            else:
                percent = (100 * int(counter) / int(len(imdblist)))
                debuglog("TAG-GEN: Not writing tag: " + newimdbtag +
                         " to movie: " + xbmcname + " with existing tag: " +
                         xbmctag + " from " + str(imdbuser))
            if len(sys.argv) == 2:
                pDialog.update(percent,"",_getstr(30017) + str(counter) + "/" + str(len(imdblist)) + _getstr(30018))
    debuglog(str(imdblist))
    return moviecount


# Scrapes Wikipedia URLs for comedian names given a single url
def scrapewiki():
    internet_test("https://en.wikipedia.org")
    if len(sys.argv) == 2:
        pDialog.update(0, _getstr(30019), " ", " ")
    comiclist = []
    for wikiurl in wikiurllist:
        ifcancel()
        try:
            page = requests.get(wikiurl).text
            results = (re.findall(r'<li><a href="/wiki/.+?" title=".+?">((?!.*List.*|.*rticle.*|.*omedian.*)\b.+?\b.+?)</a></li>', page))
            for comic in results:
                comic = comic.encode("utf-8")
                ifcancel()
                debuglog("TAG-GEN: Found comedian: " + comic + " in Wiki URL: " + wikiurl)
                comiclist.append(comic)
            comiclist = sorted(set(comiclist))
        except Exception as e:
            if len(sys.argv) == 2:
                dialog = xbmcgui.Dialog()
                ok = dialog.ok(_getstr(30000), wikiurl + _getstr(30020))
            xbmc.log(msg="TAG-GEN: " + wikiurl + " contains no comedians. Check URL and retry.", level=xbmc.LOGERROR)
            debuglog("TAG-GEN: " + str(e))
            sys.exit(1)
    return comiclist


# write tags for locally found Stand-up movies given list of comedians, local media list and the new tag to write
def writestanduptags(comiclist, medialist, newwikitag):
    if len(sys.argv) == 2:
        pDialog.update(0,_getstr(30021), " ", " ")
    comicmatches = 0
    counter = 0
    for comic in comiclist:
        ifcancel()
        counter = counter + 1
        for movie in medialist:
            xbmcname = (json.dumps(movie.get('name', '')))
            xbmcid = (json.dumps(movie.get('xbmcid', '')))
            xbmctag = (json.dumps(movie.get('tag', '')))
            if (comic in xbmcname) and (newwikitag not in xbmctag):
                comicmatches = comicmatches + 1
                debuglog("TAG-GEN: Match found for comedian: " + comic + " in feature: " + xbmcname
                         + " from Wikipedia comedians.")
                xbmctag = xbmctag[1:-1]
                percent = (100 * int(counter) / int(len(comiclist)))
                if len(sys.argv) == 2:
                    pDialog.update(percent, "", "", _getstr(30022) + str(newwikitag) + _getstr(30023)
                                   + str(comicmatches) + _getstr(30024))
                    pDialog.update(percent, "", _getstr(30025) + str(counter) + "/"
                                   + str(len(comiclist)) + _getstr(30026))
                    writetags(xbmcid, newwikitag, xbmctag)
            else:
                percent = (100 * int(counter) / int(len(comiclist)))
                debuglog("TAG-GEN: No match found for comedian: " + comic +
                         " in feature: " + xbmcname +
                         " with existing tag: " + xbmctag)
                if len(sys.argv) == 2:
                    pDialog.update(percent, "", _getstr(30025) + str(counter) + "/" + str(len(comiclist))
                                   + _getstr(30026))
    return comicmatches


# input movie wiki url. output imdb movie id
def find_imdb_id(wikiurl):
    wiki_https = "https://www.wikipedia.org"
    page = requests.get(wiki_https + wikiurl)
    page_soup = BeautifulSoup(page.text, "html.parser")
    # capture main body
    page_portion = page_soup.find(class_="mw-parser-output")
    # for each unordered list
    if page_portion is not None:
        for ul in page_portion.find_all("ul"):
            ifcancel()
            # for each list item
            for ul_li in ul.find_all("li"):
                # for each hyperlink
                for ul_li_a in ul_li.find_all("a"):
                    # if link points to imdb website, return imdbid tag
                    imdb_href = ul_li_a.get("href")
                    if imdb_href is not None and "imdb.com" in imdb_href:
                        imdbid = imdb_href[-10:-1]
                        return imdbid
    return ''


# find all ceremony urls
def find_academy_ceremonies(academy_ceremony_url_list, year_set):
    internet_test("https://en.wikipedia.org")
    if len(sys.argv) == 2:
        pDialog.update(0, _getstr(33046), " ", " ")
    year_url_dict = {}
    url_list = []
    year_list = []
    page = requests.get(academy_ceremony_url_list[0])
    page_soup = BeautifulSoup(page.text, "html.parser")
    page_portion = page_soup.find("body")  # find body
    if page_portion is not None:  # if html body is not None
        # find all tables and print class name
        # loop through all tables with class = "wikitable"
        for table in page_portion.find_all("table", "wikitable"):
            ifcancel()
            try:
                # for every table row in table
                for table_tr in table.find_all("tr"):
                    # var to only take year if link was taken in
                    find_date = False
                    is_link_added = False
                    # find year in date of ceremony
                    for table_tr_td in table_tr.find_all("td"):
                        # after link added, add date  to year_list -> from next table cell right
                        if find_date:
                            if table_tr_td.text[-4:].isdigit():
                                year_list.append(table_tr_td.text[-4:])
                                find_date = False
                        # for all links in table row
                        for table_tr_td_a in table_tr_td.find_all("a"):
                            if not is_link_added:
                                # append link to url_list
                                url = table_tr_td_a.get("href")
                                text = table_tr_td_a.text
                                if len(text) > 1 and len(text) < 5 and text[0].isdigit():
                                    url_list.append("https://wikipedia.org" + url)
                                    find_date = True
                                    is_link_added = True
            except Exception as e:
                if len(sys.argv) == 2:
                    pDialog.update(0, _getstr(30000), _getstr(33085))
                    xbmc.log(msg="TAG-GEN: " + wikiurl + " contains no oscar nominees. Check URL and retry.", level=xbmc.LOGERROR)
                debuglog("TAG-GEN: " + str(e))
                sys.exit(1)
        try:
            # create year dict: list of urls for ceremonies
            if len(year_list) == len(url_list):
                # loop. add ceremony urls by year to list in dict
                for n in xrange(len(year_list)):
                    # aquire year
                    year = year_list[n]
                    # add empty list to value to dictionary
                    if year not in year_url_dict:
                        year_url_dict[year] = []
                    # append ceremony url to list
                    year_url_dict[year].append(url_list[n])
            else:
                if len(sys.argv) == 2:
                    xbmcgui.Dialog().ok("Tag Generator", _getstr(33083))
                    debuglog("TAG-GEN: List lengths are different.")
                    sys.exit(1)
            # create new list with only relevant ceremonies
            # loop. for every relevant year add potential ceremony url to url_list_relevant
            url_set_relevant = set()
            for year in year_set:
                ifcancel()
                list_of_relevant_years = []
                # for possibly relevant ceremonies for movies in said year
                for i in xrange(2):
                    new_year = str(int(year) + i)
                    # if new year in year_url_dict then append
                    if new_year in year_url_dict:
                        list_of_relevant_years.append(new_year)
                # add possible ceremonies
                for relevant_year in list_of_relevant_years:
                    for url_ceremony in year_url_dict[relevant_year]:
                        url_set_relevant.add(url_ceremony)
            sorted(url_set_relevant)
        except Exception as e:
            if len(sys.argv) == 2:
                pDialog.update(0, _getstr(30000), _getstr(33084))
                xbmc.log(msg="TAG-GEN: Failed to process ceremonies.", level=xbmc.LOGERROR)
            debuglog("TAG-GEN: " + str(e))
            sys.exit(1)
    return url_set_relevant

# return list of years in xbmc library.
def get_years(medialist):
    # create unique year set
    year_set = set()
    # add all years in xbmcdb to set
    try:
        counter = 0
        percent = 0
        for movie in medialist:
            ifcancel()
            # iterate
            counter = counter + 1
            percent = (100 * counter/len(medialist))
            try:
                if len(sys.argv) == 2:
                    pDialog.update(percent, _getstr(33080), _getstr(33067) + str(counter) + "/" + str(len(medialist)), "")
                # get year, add to set
                xbmc_year = (json.dumps(movie.get('year', '')))
                year_set.add(xbmc_year)
            except Exception as e:
                if len(sys.argv) == 2:
                    pDialog.update(percent, _getstr(33081), _getstr(33067) + str(counter) + "/" + str(len(medialist)), "")
                    debuglog("Failed to log year of film.\nProgress: " + str(counter) + "/" + str(len(medialist)))
                debuglog("TAG-GEN: " + str(e))
                sys.exit(1)
    except Exception as e:
        if len(sys.argv) == 2:
            pDialog.update(_getstr(33082))
            debuglog("TAG-GEN: Failed to log years of medialist")
        debuglog("TAG-GEN: " + str(e))
        sys.exit(1)
    # if set empty
    if len(year_set) <= 0:
        year_set = list(range(1929, datetime.datetime.now().year))
    return year_set


# Scrapes wikipedia for characteristics/awards and returns movies with tag info
def scrapewiki_oscars(source_url_list, medialist):
    # test url
    internet_test("https://www.wikipedia.org")
    # update gui
    if len(sys.argv) == 2:
        pDialog.update(0, _getstr(33046), " ", " ")
        debuglog("TAG-GEN: Scraping Wikipedia for oscar nominees...")
    # aquire list of years in library
    year_set = get_years(medialist)
    # update gui
    if len(sys.argv) == 2:
        pDialog.update(0, _getstr(33057), _getstr(33064) + " " + str(len(year_set)), " ")
        debuglog("TAG-GEN: Acquiring links nominated in relevant academy awards. Number of ceremonies to search: " + str(len(year_set)))
    # get all ceremony urls
    # find set of ceremonies to scape
    url_set_ceremonies = find_academy_ceremonies(source_url_list, year_set)
    # loop through each ceremony url
    counter_url = 0
    percent = 0
    imdb_id_dict = {}
    wiki_url_dict = {}
    for wikiurl in url_set_ceremonies:
        ifcancel()
        try:
            counter_url = counter_url + 1
            percent = (100 * int(counter_url) / int(len(url_set_ceremonies)))
            # BeautifulSoup
            page = requests.get(wikiurl)
            page_soup = BeautifulSoup(page.text, 'html.parser')
            # pull all text from page_soup
            ceremony_name = page_soup.find("h1", "firstHeading").text
            # update gui
            if len(sys.argv) == 2:
                pDialog.update(percent, _getstr(33065) + ": " + str(counter_url) + "/" + str(len(url_set_ceremonies)), wikiurl)
                debuglog("TAG-GEN: Scraping each award ceremony page for awards, nominees and nominee urls. Wiki URL: "
                         + wikiurl + ", progress: " + str(counter_url) + "/" + str(len(url_set_ceremonies)))
            # loop. iterate through each row in table
            page_portion_list = []
            page_portion_list.append(page_soup.find("table", "wikitable"))
            i_list = []
            for page_portion in page_portion_list:
                if page_portion is not None:
                    # find category name and nominees
                    for table_cell in page_portion.find_all('tr'):
                        # first link -> category name
                        table_cell_a = table_cell.find('a')
                        if table_cell_a is not None:
                            category_title = table_cell_a.get('title')
                            # for each list item. cature all movie elements
                            url_list = []
                            for i in table_cell.find_all('i'):
                                # for each catagory nominee element
                                for i_a in i.find_all('a'):
                                    if i_a is not None:
                                        i_a_href = i_a.get('href')
                                        # append url to url_list
                                        if i_a_href not in url_list:
                                            url_list.append(i_a_href)
                            # convert html special characters into unicode
                            key = ceremony_name + " Oscars: " + category_title + " "
                            wiki_url_dict[key] = url_list
        except Exception as e:
            if len(sys.argv) == 2:
                pDialog.update(0, _getstr(30000), wikiurl + _getstr(33049))
                xbmc.log(msg="TAG-GEN: " + wikiurl + " contains no oscar nominees. Check URL and retry.", level=xbmc.LOGERROR)
            debuglog("TAG-GEN: " + str(e))
    if len(sys.argv) == 2:
        pDialog.update(0, _getstr(33069), " ", " ")
        debuglog("TAG-GEN: Creating set of links")
    # create list of all unique urls
    unique_urls = set()
    counter_unique = 0
    percent_unique = 0
    for each_key in wiki_url_dict:
        counter_unique = counter_unique + 1
        percent_unique = (100 * int(counter_unique) / int(len(wiki_url_dict)))
        # loop through each url in each list associated with each_key. add each url
        if len(sys.argv) == 2:
            pDialog.update(percent_unique, str(counter_unique) + "/" + str(len(wiki_url_dict)) + _getstr(33070))
        for each_url in wiki_url_dict[each_key]:
            unique_urls.add(each_url)
    if len(sys.argv) == 2:
        pDialog.update(0, _getstr(33071), "", "")
        debuglog("TAG-GEN: Unique URL set created")
    # create dictionary from unique_urls set. to be referenced when creating a larger dict proportional to wiki_url_dict
    percent = 0
    counter = 0
    unique_url_imdb_pair = {}
    for each_url in unique_urls:
        counter = counter + 1
        percent = (100 * int(counter) / int(len(unique_urls)))
        if len(sys.argv) == 2:
            pDialog.update(percent, _getstr(33072), _getstr(33074) + each_url, " ")
        # extract imdb id from url and add to dictionary
        imdb_id = find_imdb_id(each_url)
        if len(imdb_id) > 3:
            unique_url_imdb_pair[each_url] = imdb_id
    if len(sys.argv) == 2:
        pDialog.update(percent, _getstr(33075), " ", " ")
        debuglog("TAG-GEN: Creating IMDb set")
    # loop through each key in wiki_url_dict and replace url list with imdb id list
    unique_imdbs = set()
    percent = 0
    counter = 0
    for each_key in wiki_url_dict:
        counter = counter + 1
        percent = (100 * int(counter) / int(len(unique_urls)))
        if len(sys.argv) == 2:
            pDialog.update(percent, _getstr(33075), " ", " ")
        # loop through each url in wiki_url_dict[each tag] (list). append to corresponding list in imdb_id_dict
        imdb_id_dict[each_key] = []
        for each_url in wiki_url_dict[each_key]:
            if each_url in unique_url_imdb_pair:
                imdb_id = unique_url_imdb_pair[each_url]
                imdb_id_dict[each_key].append(imdb_id)
                # add to unique imdbs set
                unique_imdbs.add(imdb_id)
    # return
    return imdb_id_dict, unique_imdbs


# write tags for locally found Stand-up movies given list of comedians, local media list and the new tag to write
def write_tags_from_dict(dict_of_tag_and_imdbids, unique_imdbs, medialist, newwikitag):
    # update gui
    if len(sys.argv) == 2:
        # ok = xbmcgui.Dialog().ok("Tag Generator", "starting to write")
        pDialog.update(0,_getstr(33050), " ", " ")
    try:
        # vars
        matches = 0
        moviematches = 0
        counter = 0
        imdbid_matches = []
        # cancel script?
        ifcancel()
        # for each movie in library
        for movie in medialist:
            # iterate counter
            moviematch = 0
            counter = counter + 1
            percent = (100 * int(counter) / int(len(medialist)))
            if len(sys.argv) == 2:
                pDialog.update(percent, _getstr(33076), " ", " ")
            # name, id, imdb id, tag
            xbmcname = (json.dumps(movie.get('name', '')))
            xbmcid = (json.dumps(movie.get('xbmcid', '')))
            xbmc_imdbid = (json.dumps(movie.get('imdbid', '')))
            xbmctag = (json.dumps(movie.get('tag', '')))
            # convert to string
            xbmc_imdbid_str = re.sub('[^a-z0-9\.]', '', xbmc_imdbid)
            xbmctag_str = ''.join(xbmctag)
            # if len of imdbid is 9
            if len(xbmc_imdbid_str) == 9:
                # if imdbid is in unique imdb set then loop through tags
                if xbmc_imdbid_str in unique_imdbs:
                    # for tag in dict_of_tag_and_imdbids
                    for tag in dict_of_tag_and_imdbids:
                        # cancel script?
                        ifcancel()
                        # if nonempty tag
                        if len(tag) > 3:
                            # for each imdbid in list of imdbids for current tag
                            counter_id = 0
                            list_of_imdbids = dict_of_tag_and_imdbids[tag]
                            for imdbid in list_of_imdbids:
                                # if movie name and tag match local to imdb
                                if (imdbid == xbmc_imdbid_str) and (tag not in xbmctag):
                                    # iterate oscarmatches & log & xbmc tag & percentage completed
                                    matches = matches + 1
                                    if moviematch == 0:
                                        moviematch += 1
                                    if imdbid not in imdbid_matches:
                                        imdbid_matches.append(imdbid)
                                        moviematches += 1
                                    if len(sys.argv) == 2:
                                        pDialog.update(percent, "", _getstr(33077), str(counter) + "/" + str(len(medialist)))
                                        debuglog("TAG-GEN: Match found for oscar nominee: " + imdbid + " in feature: " + xbmcname)
                                    # if imdbid matches to first in list_of_imdbids then it was the winner of this catagory
                                    if imdbid == list_of_imdbids[0]:
                                        tag = tag + " Winner "
                                    # write tag
                                    writetags(xbmcid, newwikitag, xbmctag)
                                # else. imdbid is not a match (most common case)
                                else:
                                    # update percentage & log
                                    percent = (100 * int(counter) / int(len(medialist)))
                                    debuglog(_getstr(33059) + _getstr(33060) + xbmcname + _getstr(33061) + xbmctag)
                                    # update gui
                                    if len(sys.argv) == 2:
                                        pDialog.update(percent,"",_getstr(33077), str(counter) + "/" + str(len(medialist)))
    except Exception as e:
        ok = xbmcgui.Dialog().ok("Tag Generator", _getstr(33086))
        debuglog("TAG-GEN: " + str(e))
        sys.exit(1)
    return moviematches

###################################################################
########################## END FUNCTIONS ##########################
###################################################################

# These are the URLs that we will be searching for comedians
wikiurllist=["https://en.wikipedia.org/wiki/List_of_British_stand-up_comedians",
"https://en.wikipedia.org/wiki/List_of_stand-up_comedians",
"https://en.wikipedia.org/wiki/List_of_Australian_stand-up_comedians",
"https://en.wikipedia.org/wiki/List_of_Canadian_stand-up_comedians",
"https://en.wikipedia.org/wiki/List_of_United_States_stand-up_comedians"]

# These are the URLs that will be used to search for oscar movie awards
wiki_oscar_url = ["https://en.wikipedia.org/wiki/List_of_Academy_Awards_ceremonies"]

monitor = xbmc.Monitor()
while not monitor.abortRequested():
    if (c_runasservice != "true") and len(sys.argv) != 2:
        xbmc.log(msg="TAG-GEN: Manual run not requested and runasservice not selected, exiting.", level=xbmc.LOGERROR)
        sys.exit(1)
    xbmc.log(msg="TAG-GEN: Starting tag generation.", level=xbmc.LOGNOTICE)
    URLID=32050
    TAGID=32080
    oscarcount = 0
    comiccount = 0
    moviecount = 0
    c_imdburl = __settings__.getSetting(str(URLID))
    c_imdbtag = __settings__.getSetting(str(TAGID))
    c_standup = __settings__.getSetting("32015")
    c_standuptag = __settings__.getSetting("32016")
    c_plusurl = __settings__.getSetting("32013")
    c_minusurl = __settings__.getSetting("32014")
    c_urlcount =  __settings__.getSetting("32099")
    c_useimdb =  __settings__.getSetting("32020")
    c_usetrakt = __settings__.getSetting("32023")
    c_oscars = __settings__.getSetting("35015")
    c_oscartag = __settings__.getSetting("35016")
    trakt_list_start = 32120
    trakt_tag_start = 32140
    trakt_user_start = 32160
    c_trakt_list = __settings__.getSetting(str(trakt_list_start))
    c_trakt_tag = __settings__.getSetting(str(trakt_tag_start))
    c_trakt_user = __settings__.getSetting(str(trakt_user_start))
    trakt.core.APPLICATION_ID = '12265'
    trakt_client_id = '8bc9b1371d9594b451c863bea2c95aa96ac5e5bf9ecee274daa23c0790386afe'
    trakt_client_secret = '6087cbfb47b8f0cdc1c0fc491ec52524c9d23bf37a8480a8c2827ea91312cbad'
    c_trakt_token = __settings__.getSetting("32031")
    c_trakt_list_count = __settings__.getSetting("32098")
    c_debug = __settings__.getSetting("32030")
    c_notify = __settings__.getSetting("32019")
    manual = "false"
    wipeout = "false"


# Initialise IMDB URL list, add extra to list if specified by settings.xml. 
# Also make a list out of the user-defined tags
    listurlcount = int(c_urlcount)
    imdburllist = []
    imdbtaglist = []
    while listurlcount > -1:
        imdburllist.append(c_imdburl)
        imdbtaglist.append(c_imdbtag)
        URLID = URLID+1
        TAGID = TAGID+1
        c_imdburl = __settings__.getSetting(str(URLID))
        c_imdbtag = __settings__.getSetting(str(TAGID))
        listurlcount = listurlcount -1

# init trakt lists and tags        
    trakt_list_count = int(c_trakt_list_count)
    trakt_lists = list()
    trakt_tags = list()
    trakt_users = list()
    while trakt_list_count > -1:
        trakt_lists.append(c_trakt_list)
        trakt_tags.append(c_trakt_tag)
        trakt_users.append(c_trakt_user)
        trakt_list_start+=1
        trakt_tag_start+=1
        c_trakt_list = __settings__.getSetting(str(trakt_list_start))
        c_trakt_tag = __settings__.getSetting(str(trakt_tag_start))
        c_trakt_user = __settings__.getSetting(str(trakt_user_start))
        trakt_list_count -= 1
        
#command line arguments for manual/tag delete executions
    if len(sys.argv) == 2:
        if sys.argv[1] == "manual":
            manual = "true"
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30027))
        elif sys.argv[1] == "wipeout":
            wipeout = "true"
            if xbmcgui.Dialog().yesno("Tag Generator", _getstr(30028)):
                if xbmcgui.Dialog().yesno("Tag Generator", _getstr(30029)):
                    pDialog = xbmcgui.DialogProgress()
                    pDialog.create("Tag Generator", _getstr(30030))
                    wipedcount = wipealltags()
                    xbmc.log(msg="TAG-GEN: Finished wiping tags.", level=xbmc.LOGNOTICE)
                    sys.exit(0)
                else:
                    xbmc.log(msg="TAG-GEN: Manual tag deletion arg received, but not confirmed so exiting.",
                             level=xbmc.LOGNOTICE)
                    sys.exit(0)
            else:
                xbmc.log(msg="TAG-GEN: Manual tag deletion arg received, but not confirmed so exiting.",
                         level=xbmc.LOGNOTICE)
                sys.exit(0)
        elif sys.argv[1] == "standup":
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30027))
            xbmc.log(msg="TAG-GEN: Starting stand-up tag writing.", level=xbmc.LOGNOTICE)
            medialist = getxbmcdb()
            newwikitag = c_standuptag
            comedians = scrapewiki()
            comiccount = writestanduptags(comedians, medialist, newwikitag)
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Tag Generator", _getstr(30031) + str(comiccount) + _getstr(30033))
            xbmc.log(msg="TAG-GEN: Manual Stand-Up arg received, exiting after execution.", level=xbmc.LOGNOTICE)
            sys.exit(0)
        elif sys.argv[1] == "imdb":
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30027))
            xbmc.log(msg="TAG-GEN: Starting IMDB tag writing.",level=xbmc.LOGNOTICE)
            medialist = getxbmcdb()
            scrapecount = 0
            for imdburl in imdburllist:
                newimdbtag = imdbtaglist[scrapecount]
                imdblist, imdbuser = scrapeimdb(imdburl, scrapecount)
                moviecount += writeimdbtags(imdblist, medialist, newimdbtag)
                scrapecount = scrapecount + 1
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Tag Generator", _getstr(30031)+str(moviecount)+_getstr(30003))
            xbmc.log(msg="TAG-GEN: Manual IMDB arg received, exiting after execution.", level=xbmc.LOGNOTICE)
            sys.exit(0)
        elif sys.argv[1] == "trakt_init":
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Tag Generator", _getstr(30923))
            dialog = xbmcgui.Dialog()
            d = dialog.input(_getstr(30924))
            if d:
                try:
                    trakt_token = trakt.init(pin=d, client_id=trakt_client_id, client_secret=trakt_client_secret)
                    __settings__.setSetting("32031", trakt_token)
                    sys.exit(0)
                except Exception as e:
                    dialog = xbmcgui.Dialog()
                    ok = dialog.ok("Tag Generator", _getstr(30925))
                    xbmc.log(msg="Unable to retrieve Trakt oauth token." + str(e), level=xbmc.LOGERROR)
                    sys.exit(0)
            else:
                xbmc.log(msg="TAG-GEN: Manual Trakt Init arg received, exiting after execution.", level=xbmc.LOGNOTICE)
                sys.exit(0)
        elif sys.argv[1] == "trakt":
            if len(c_trakt_token) != 64:
                dialog = xbmcgui.Dialog()
                ok = dialog.ok("Tag Generator", _getstr(30925))
                xbmc.log(msg="TAG-GEN: Unable to retrieve Trakt oauth token.", level=xbmc.LOGERROR)
                sys.exit(1)
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30027))
            xbmc.log(msg="TAG-GEN: Starting Trakt writing.", level=xbmc.LOGNOTICE)
            medialist = getxbmcdb()
            i = 0
            for this_trakt_list in trakt_lists:
                this_trakt_tag = trakt_tags[i]
                this_trakt_user = trakt_users[i]
                try:
                    trakt_movies = get_trakt_movies(this_trakt_user, this_trakt_list, c_trakt_token)
                    moviecount += write_trakt_tags(trakt_movies, medialist, this_trakt_tag)
                except:
                    xbmc.log(msg="TAG-GEN: Could not retrieve movies from Trakt API.", level=xbmc.LOGERROR)
                i += 1
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Tag Generator", _getstr(30031) + str(moviecount) + _getstr(30003))
            xbmc.log(msg="TAG-GEN: Manual arg received, exiting after single execution.", level=xbmc.LOGNOTICE)
            sys.exit(0)
        elif sys.argv[1] == "oscars":
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30027))
            xbmc.log(msg="TAG-GEN: Starting oscar tag writing.", level=xbmc.LOGNOTICE)
            medialist = getxbmcdb()
            newwikitag_oscars = c_oscartag
            (oscar_nominees, unique_imdbs) = scrapewiki_oscars(wiki_oscar_url, medialist)
            nominee_count = write_tags_from_dict(oscar_nominees, unique_imdbs, medialist, newwikitag_oscars)
            ok = dialog.ok("Tag Generator", _getstr(30031) + str(nominee_count) + _getstr(33056))
            xbmc.log(msg="TAG-GEN: Manual arg received, exiting after single execution.", level=xbmc.LOGNOTICE)
            sys.exit(0)
        else:
            xbmc.log(msg="TAG-GEN: No valid arguments supplied.", level=xbmc.LOGERROR)
            sys.exit(1)

            
#### Read the local XBMC DB ####
    medialist = getxbmcdb()

#### IMDB tag writing ####
    if ("true" in c_useimdb) and ("false" in wipeout):
        if c_notify == "true":
            notify(_getstr(30036))
        xbmc.log(msg="TAG-GEN: Starting IMDB tag writing.", level=xbmc.LOGNOTICE)
        scrapecount = 0
        moviecount = 0
        for imdburl in imdburllist:
            newimdbtag = imdbtaglist[scrapecount]
            imdblist, imdbuser = scrapeimdb(imdburl, scrapecount)
            moviecount = moviecount + writeimdbtags(imdblist, medialist, newimdbtag)
            scrapecount = scrapecount + 1
    else:
        xbmc.log(msg="TAG-GEN: Skipping IMDB tag writing.", level=xbmc.LOGNOTICE)
        moviecount = 0

#### Trakt movies tag writing ####
    if ("true" in c_usetrakt) and ("false" in wipeout) and (len(c_trakt_token) == 64):
        if c_notify == "true":
            notify(_getstr(30037))
        xbmc.log(msg="TAG-GEN: Starting Trakt tag writing.", level=xbmc.LOGNOTICE)
        i = 0
        for this_trakt_list in trakt_lists:
            this_trakt_tag = trakt_tags[i]
            this_trakt_user = trakt_users[i]
            try:
                trakt_movies = get_trakt_movies(this_trakt_user, this_trakt_list, c_trakt_token)
                moviecount += write_trakt_tags(trakt_movies, medialist, this_trakt_tag)
            except:
                xbmc.log(msg="TAG-GEN: Could not retrieve movies from Trakt API.", level=xbmc.LOGERROR)
            i += 1
    else:
        xbmc.log(msg="TAG-GEN: Skipping Trakt tag writing.", level=xbmc.LOGNOTICE)

    #### Stand-up Comedy tag writing ####
    if ("true" in c_standup) and ("false" in wipeout):
        if c_notify == "true":
            notify(_getstr(30038))
        newwikitag = c_standuptag
        xbmc.log(msg="TAG-GEN: Starting stand-up tag writing.", level=xbmc.LOGNOTICE)
        comedians = scrapewiki()
        comiccount = writestanduptags(comedians, medialist, newwikitag)
    else:
        xbmc.log(msg="TAG-GEN: Skipping stand-up tag writing.", level=xbmc.LOGNOTICE)

    #### Oscar tag writing ####
    if ("true" in c_oscars) and ("false" in wipeout):
        if c_notify == "true":
            notify(_getstr(30039))
        medialist = getxbmcdb()
        newwikitag_oscars = c_oscartag
        xbmc.log("TAG-GEN: Starting oscar tag writing.", level=xbmc.LOGNOTICE)
        (oscars, unique_imdbs) = scrapewiki_oscars(wiki_oscar_url, medialist)
        oscarcount = write_tags_from_dict(oscars, unique_imdbs, medialist, newwikitag_oscars)
    else:
        xbmc.log(msg="TAG-GEN: Skipping oscar tag writing.", level=xbmc.LOGNOTICE)

    if "true" in manual:
        dialog = xbmcgui.Dialog()
        ok = dialog.ok("Tag Generator", _getstr(30031) + str(moviecount) + _getstr(30032) + str(comiccount)
                       + _getstr(30033) + str(oscarcount) + _getstr(30040))
        xbmc.log(msg="TAG-GEN: Manual arg received, exiting after single execution.", level=xbmc.LOGNOTICE)
        sys.exit(0)
   
    elif "true" in wipeout:
        dialog = xbmcgui.Dialog()
        ok = dialog.ok("Tag Generator", _getstr(30034) + str(wipedcount) + _getstr(30035))
        xbmc.log(msg="TAG-GEN: Wipeout arg received, exiting after single execution.", level=xbmc.LOGNOTICE)
        sys.exit(0)
   
    else:
        xbmc.log(msg="TAG-GEN: Sleeping for " + str(c_refresh) + " hours", level=xbmc.LOGNOTICE)
        while not monitor.abortRequested():
            if (datetime.datetime.now() - start_time).total_seconds() < service_interval:
                xbmc.sleep(micronap)
            else:
                start_time = datetime.datetime.now()
                break
