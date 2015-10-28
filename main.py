import re, urllib2, urllib, httplib, sys, os, time
import xbmc 
import xbmcgui 
import xbmcaddon
import simplejson
import json

try:
    from hashlib import sha1
except ImportError:
    from sha import new as sha1

if len(sys.argv) != 2:
    xbmc.sleep(1000)
    xbmc.log(msg="TAG-GEN: Starting as a service.",level=xbmc.LOGNOTICE)
__settings__ = xbmcaddon.Addon()
c_refresh = __settings__.getSetting("32012")
c_runasservice = __settings__.getSetting("32011")
sleeptime = int(c_refresh)*3600000
micronap = 60000

###################################################################
############################ FUNCTIONS ############################
###################################################################
#test for interwebs
def internet_test(url):
    try:
        response=urllib2.urlopen(url,timeout=1)
        return True
    except urllib2.URLError as err: pass
    if len(sys.argv) == 2:
        dialog = xbmcgui.Dialog()
        ok = dialog.ok("Error",url + " unreachable. Check network and retry.")
    xbmc.log(msg= "TAG-GEN: " + url + " unreachable. Check network and retry.",level=xbmc.LOGNOTICE)
    sys.exit(url + " unreachable. Check network and retry.")

#stops the music
def stopmusic():
    playlist = xbmc.PlayList( xbmc.PLAYLIST_MUSIC )
    playlist.clear()
    xbmc.Player().stop()

# cancels script and stops the music
def ifcancel():
    if len(sys.argv) == 2:
        if (pDialog.iscanceled()):
            if "true" in c_bgmusic:
                stopmusic()
            xbmc.log(msg= "TAG-GEN: Cancel received from XBMC dialog, exiting.",level=xbmc.LOGNOTICE)
            sys.exit("Operation cancelled.")

#starts the music
def playmusic():
    path=__settings__.getAddonInfo('path')
    file = path + "/music.mp3"
    playlist = xbmc.PlayList( xbmc.PLAYLIST_MUSIC )
    playlist.clear()
    playlist.add(file)
    playlist.add(file)
    playlist.add(file)
    playlist.add(file)
    playlist.add(file)
    xbmc.Player().play( playlist)

#def to make a debug log
def debuglog(string):
    if "true" in c_debug:
        xbmc.log(msg=string,level=xbmc.LOGNOTICE)

#make lists sorted and unique
def unique(it):
    return dict(map(None,it,[])).keys()
def sorted(it):
    alist = [item for item in it]
    alist.sort()
    return alist

# A function to overwrite EVERY tag found in the database with a blank [] tag.    
def wipealltags():
    counter = 0
    Medialist = getxbmcdb()
    for movie in Medialist:
        ifcancel()
        json_query = '{"jsonrpc": "2.0", "id": "libMovies", "method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : replaceid, "tag":[]}}'
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        xbmcid = (json.dumps(movie.get('xbmcid','')))
        json_query = re.sub('replaceid', xbmcid, json_query)
        jsonobject=simplejson.loads(xbmc.executeJSONRPC(json_query))
        if len(sys.argv) == 2:
            counter = counter + 1
            percent = (100 * int(counter) / int(len(Medialist)))
            pDialog.update (percent," ","Writing blank tags for " + str(counter) + "/" + str(len(Medialist)) + " movies")
    return counter

# dump the entire XBMC library to a big fat python list of dicts
def getxbmcdb():
    if "true" in wipeout:
        pDialog.update (0,"Alrighty then..."," "," ")
    elif len(sys.argv) == 2:
        pDialog.update (0,"Reading your XBMC DB..."," "," ")
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies","params": {"properties" : ["tag","imdbnumber"], "sort": { "order": "ascending", "method": "label", "ignorearticle": true } }, "id": "libMovies"}')
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    jsonobject = simplejson.loads(json_query)
    Medialist = []
    if jsonobject['result'].has_key('movies'):
        for item in jsonobject['result']['movies']:
            ifcancel()
            Medialist.append({'xbmcid': item.get('movieid',''),'imdbid': item.get('imdbnumber',''),'name': item.get('label',''),'tag': item.get('tag','')})
    return Medialist

#def to fetch the names of the custom trakt lists
def gettraktlists(traktuser, traktpass):
    if len(sys.argv) == 2:
        pDialog.update (0,"Checking for custom Trakt lists..."," "," ")
    listurl = "https://api.trakt.tv/user/lists.json/b6135e0f7510a44021fac8c03c36c81a17be35d9/" + traktuser
    debuglog("TAG-GEN: Fetching custom Trakt Movie lists from " + listurl)
    list_args = {'username': traktuser, 'password': traktpass}
    listdata = urllib.urlencode(list_args)
    listrequest = urllib2.Request(listurl, listdata)
    listresponse = urllib2.urlopen(listrequest)
    listhtml = listresponse.read()
    listjson = simplejson.loads(listhtml)
    traktlistinfo = []
    if len(listjson) > 0:
        for item in listjson:
            ifcancel()
            traktlistinfo.append({'listname': item.get('name',''),'listslug': item.get('slug','')})
            debuglog("Found list " + (json.dumps(item.get('name',''))) + " with slug " + (json.dumps(item.get('slug',''))))
    return traktlistinfo

#def to return the contents of a custom Trakt list
def readtraktlists(traktuser, traktpass, slug):
    if len(sys.argv) == 2:
        pDialog.update (0,"Reading custom Trakt list: " + slug," "," ")
    ifcancel()
    listurl = "https://api.trakt.tv/user/list.json/b6135e0f7510a44021fac8c03c36c81a17be35d9/" + traktuser + "/" + slug[1:-1]
    debuglog("TAG-GEN: Reading custom Trakt Movie list: " + listurl)
    list_args = {'username': traktuser, 'password': traktpass}
    listdata = urllib.urlencode(list_args)
    listrequest = urllib2.Request(listurl, listdata)
    listresponse = urllib2.urlopen(listrequest)
    listhtml = listresponse.read()
    listjson = simplejson.loads(listhtml)
    traktlist = []
    for item in listjson['items']:
        ifcancel()
        traktlist.append({'imdbid': item['movie'].get('imdb_id',''),'name': item['movie'].get('title','')})
        debuglog("TAG-GEN: Found Trakt movie " + (json.dumps(item['movie'].get('title',''))) + " in " + listurl)
    return traktlist

#def to fetch Trakt movies from primary Movie watchlist
def gettrakt(traktuser, traktpass):
    if len(sys.argv) == 2:
        pDialog.update (0,"Reading your Trakt movie watchlist..."," "," ")
    movieurl = "https://api.trakt.tv/user/watchlist/movies.json/b6135e0f7510a44021fac8c03c36c81a17be35d9/" + traktuser
    movie_args = {'username': traktuser, 'password': traktpass}
    moviedata = urllib.urlencode(movie_args)
    movierequest = urllib2.Request(movieurl, moviedata)
    movieresponse = urllib2.urlopen(movierequest)
    moviehtml = movieresponse.read()
    moviejson = simplejson.loads(moviehtml)
    traktlist = []
    for item in moviejson:
        ifcancel()
        traktlist.append({'imdbid': item.get('imdb_id',''),'name': item.get('title','')})
        debuglog("TAG-GEN: Found Trakt movie " + (json.dumps(item.get('title',''))) + " in primary watchlist: " + movieurl)
    return traktlist

# write tags for locally found movies given a Trakt watchlist, local media list and the new tag to write
def writetrakttags(traktlist, Medialist, newtrakttag):
    if len(sys.argv) == 2:
        pDialog.update (0,"Scanning for local matches to Trakt movie watchlists."," "," ")
    moviecount = 0
    counter = 0
    for traktitem in traktlist:
        ifcancel()
        traktimdbid = (json.dumps(traktitem.get('imdbid','')))
        counter = counter + 1
        for movie in Medialist:
            xbmcimdbid = (json.dumps(movie.get('imdbid','')))
            xbmcid = (json.dumps(movie.get('xbmcid','')))
            xbmctag = (json.dumps(movie.get('tag','')))
            xbmcname = (json.dumps(movie.get('name','')))
            if (traktimdbid in xbmcimdbid) and (newtrakttag not in xbmctag):
                moviecount = moviecount + 1
                percent = (100 * int(counter) / int(len(traktlist)))
                if len(sys.argv) == 2:
                    pDialog.update (percent,"","","Writing tag '" + str(newtrakttag) + "' to " + str(moviecount) + " movies.")
                debuglog("TAG-GEN: Writing tag: " + newtrakttag + " to Trakt movie: " + xbmcname)
                writetags(xbmcid, newtrakttag, xbmctag[1:-1])
            else:
                percent = (100 * int(counter) / int(len(traktlist)))
                debuglog("TAG-GEN: Not writing tag: " + newtrakttag + " to movie: " + xbmcname + " with existing tag: " + xbmctag)
            if len(sys.argv) == 2:
                pDialog.update (percent,"","Evaluated " + str(counter) + "/" + str(len(traktlist)) + " movies")
    return moviecount

# def to write tags via json. Requires the xbmcid, the existing xbmctag and the new tag
def writetags(xbmcid, newtag, xbmctag):
    ifcancel()
    jsonurl='{"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : replaceid, "tag":replacetag}}'
    jsonurl=re.sub('replaceid', xbmcid, jsonurl)
    if len(xbmctag) > 2:
        jsonurl=re.sub('replacetag', '[' + xbmctag + "," + '"' + newtag + '"]', jsonurl)
    else:
        jsonurl=re.sub('replacetag', '["' + newtag + '"]', jsonurl)
    jsonresponse=simplejson.loads(xbmc.executeJSONRPC(jsonurl))

# Scrapes IMDB given a URL and a scrape count (counter for how many times it has run)
def scrapeimdb(imdburl, scrapecount):
    if len(sys.argv) == 2:
        pDialog.update (0,"Scraping IMDB for IDs..."," ", " ")
    ifcancel()
    listid=imdburl.split('/')[4]
    opener = urllib2.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    infile = opener.open(imdburl)
    imdbpage=infile.read()
    infile.close()
    global imdbuser
    imdbuser = re.findall(r'<title>IMDb: (.+?)&#x27;s Watchlist</title>', imdbpage)
    imdblist = re.findall(r'<a href="/title/(tt[0-9]{7})/">.+?</a>', imdbpage)
    imdblist = sorted(unique(imdblist))
    debuglog("TAG-GEN: Found these IMDB tags on " + str(imdbuser) + "'s watchlist: " + str(imdburl) + ": " + str(imdblist))
    return imdblist

# Scrapes IMDB given a URL and a scrape count (counter for how many times it has run)
def scrapeimdbrss(imdburl, scrapecount):
    internet_test("http://rss.imdb.com")
    if len(sys.argv) == 2:
        pDialog.update (0,"Scraping IMDB for IDs..."," ", " ")
    ifcancel()
    listid=imdburl.split('/')[4]
    opener = urllib2.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    infile = opener.open(imdburl)
    imdbpage=infile.read()
    infile.close()
    global imdbuser
    imdbuser = re.findall(r'<link>.+/(ur[0-9]{8})/.+/link>', imdbpage)
    imdblist = re.findall(r'<guid>.+(tt[0-9]{7})/</guid>', imdbpage)
    imdblist = sorted(unique(imdblist))
    debuglog("TAG-GEN: Found these IMDB tags on " + str(imdbuser) + "'s watchlist: " + str(imdburl) + ": " + str(imdblist))
    return imdblist

# write tags for locally found movies given an imdb watchlist, local media list and the new tag to write
def writeimdbtags(imdblist, Medialist, newimdbtag):
    if len(sys.argv) == 2:
        pDialog.update (0,"Scanning for local matches to " + str(imdbuser)[2:-2] + "'s IMDB watchlist.")
    moviecount = 0
    counter = 0
    for webimdbid in imdblist:
        ifcancel()
        counter = counter + 1
        for movie in Medialist:
            xbmcimdbid = (json.dumps(movie.get('imdbid','')))
            xbmcid = (json.dumps(movie.get('xbmcid','')))
            xbmctag = (json.dumps(movie.get('tag','')))
            xbmcname = (json.dumps(movie.get('name','')))
            if (webimdbid in xbmcimdbid) and (newimdbtag not in xbmctag):
                moviecount = moviecount + 1
                debuglog("TAG-GEN: Writing tag: " + newimdbtag + " to IMDB movie: " + xbmcname + " from " + str(imdbuser)[2:-2] + "'s IMDB list")
                percent = (100 * int(counter) / int(len(imdblist)))
                if len(sys.argv) == 2:
                    pDialog.update (percent,"","","Writing tag '" + str(newimdbtag) + "' to " + str(moviecount) + " movies.")
                writetags(xbmcid, newimdbtag, xbmctag[1:-1])
            else:
                percent = (100 * int(counter) / int(len(imdblist)))
                debuglog("TAG-GEN: Not writing tag: " + newimdbtag + " to movie: " + xbmcname + " with existing tag: " + xbmctag + " from " + str(imdbuser)[2:-2] + "'s IMDB watchlist.")
            if len(sys.argv) == 2:
                pDialog.update (percent,"","Evaluated " + str(counter) + "/" + str(len(imdblist)) + " movies")
    return moviecount

# Scrapes Wikipedia URLs for comedian names given a single url
def scrapewiki():
    internet_test("http://en.wikipedia.org")
    if len(sys.argv) == 2:
        pDialog.update (0,"Scraping Wikipedia for comedian names..."," "," ")
    comiclist = []
    for wikiurl in wikiurllist:
        ifcancel()
        opener = urllib2.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        infile = opener.open(wikiurl)
        page=infile.read()
        infile.close()
        results = (re.findall(r'<li><a href="/wiki/.+?" title=".+?">((?!.*List.*|.*rticle.*|.*omedian.*)\b.+?\b.+?)</a></li>', page))
        for comic in results:
            ifcancel()
            debuglog("TAG-GEN: Found comedian: " + comic + " in Wiki URL: " + wikiurl)
            comiclist.append(comic)
    comiclist = sorted(unique(comiclist))
    return comiclist

# write tags for locally found Stand-up movies given list of comedians, local media list and the new tag to write
def writestanduptags(comiclist, Medialist, newwikitag):
    if len(sys.argv) == 2:
        pDialog.update (0,"Scanning for local matches to Wikipedia comedians..."," "," ")
    comicmatches = 0
    counter = 0
    for comic in comiclist:
        ifcancel()
        counter = counter + 1
        for movie in Medialist:
            xbmcname = (json.dumps(movie.get('name','')))
            xbmcid = (json.dumps(movie.get('xbmcid','')))
            xbmctag = (json.dumps(movie.get('tag','')))
            if (comic in xbmcname) and (newwikitag not in xbmctag):
                comicmatches = comicmatches + 1
                debuglog("TAG-GEN: Match found for comedian: " + comic + " in feature: " + xbmcname + " from Wikipedia comedians.")
                xbmctag = xbmctag[1:-1]
                percent = (100 * int(counter) / int(len(comiclist)))
                if len(sys.argv) == 2:
                    pDialog.update (percent,"","","Writing tag '" + str(newwikitag) + "' to " + str(comicmatches) + " stand-up features.")
                    pDialog.update (percent,"","Evaluated " + str(counter) + "/" + str(len(comiclist)) + " well known comedians.")
                    writetags(xbmcid, newwikitag, xbmctag)
            else:
                percent = (100 * int(counter) / int(len(comiclist)))
                debuglog("TAG-GEN: No match found for comedian: " + comic + " in feature: " + xbmcname + " with existing tag: " + xbmctag)
                if len(sys.argv) == 2:
                    pDialog.update (percent,"","Evaluated " + str(counter) + "/" + str(len(comiclist)) + " well known comedians.")
    return comicmatches

###################################################################
########################## END FUNCTIONS ##########################
###################################################################

# These are the URLs that we will be searching for comedians
wikiurllist=["http://en.wikipedia.org/wiki/List_of_British_stand-up_comedians",
"http://en.wikipedia.org/wiki/List_of_stand-up_comedians",
"http://en.wikipedia.org/wiki/List_of_Australian_stand-up_comedians",
"http://en.wikipedia.org/wiki/List_of_Canadian_stand-up_comedians",
"http://en.wikipedia.org/wiki/List_of_United_States_stand-up_comedians"]

monitor = xbmc.Monitor()
while not monitor.abortRequested():
    if (c_runasservice != "true") and len(sys.argv) != 2:
        xbmc.log(msg= "TAG-GEN: Manual run not detected and runasservice not selected, exiting.",level=xbmc.LOGNOTICE)
        sys.exit("Manual run not detected, runasservice not selected, exiting.")
    xbmc.log(msg= "TAG-GEN: Starting scraped tag generation.",level=xbmc.LOGNOTICE)
    URLID=32050
    TAGID=32080
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
    #c_bgmusic = __settings__.getSetting("32021")
    c_bgmusic = "false"
    c_usetrakt = "false"
    #c_usetrakt = __settings__.getSetting("32023")
    # c_trakttag = __settings__.getSetting("32024")
    #c_traktuser = __settings__.getSetting("32025")
    # c_traktpass = sha1(__settings__.getSetting("32026")).hexdigest()
    # c_usetraktlists = __settings__.getSetting("32029")
    c_usetraktlists="false"
    c_debug = __settings__.getSetting("32030")
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
        URLID=URLID+1
        TAGID=TAGID+1
        c_imdburl = __settings__.getSetting(str(URLID))
        c_imdbtag = __settings__.getSetting(str(TAGID))
        listurlcount = listurlcount -1

#command line arguments for manual/tag delete executions
    if len(sys.argv) == 2:
        if "manual" in sys.argv[1]:
            if "true" in c_bgmusic:
                playmusic()
            manual = "true"
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", "Initialising...")
        elif "wipeout" in sys.argv[1]:
            if "true" in c_bgmusic:
                playmusic()
                wipeout = "true"
            if xbmcgui.Dialog().yesno("Tag Generator", "Do you really want to wipe out all your local XBMC tags?"):
                if xbmcgui.Dialog().yesno("Tag Generator", "Really Really REALLY?"):
                    if "true" in c_bgmusic:
                        playmusic()
                    pDialog = xbmcgui.DialogProgress()
                    pDialog.create("Tag Generator", "Alrighty then...")
                    xbmc.log(msg= "TAG-GEN: Wiping all your XBMC tags...",level=xbmc.LOGNOTICE)
                    wipedcount = wipealltags()
                else:
                    stopmusic()
                    xbmc.log(msg= "TAG-GEN: Manual tag deletion arg received, but not confirmed so exiting.",level=xbmc.LOGNOTICE)
                    sys.exit("TAG-GEN: Manual tag deletion arg received, but not confirmed so exiting.")
            else:
                stopmusic()
                xbmc.log(msg= "TAG-GEN: Manual tag deletion arg received, but not confirmed so exiting.",level=xbmc.LOGNOTICE)
                sys.exit("TAG-GEN: Manual tag deletion arg received, but not confirmed so exiting.")
        elif "trakt" in sys.argv[1]:
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", "Initialising...")
            if "true" in c_bgmusic:
                playmusic()
            xbmc.log(msg= "TAG-GEN: Starting Trakt writing.",level=xbmc.LOGNOTICE)
            Medialist = getxbmcdb()
            if "true" in c_usetrakt:
                traktlist = gettrakt(c_traktuser, c_traktpass)
                moviecount = writetrakttags(traktlist, Medialist, c_trakttag)
            if "true" in c_usetraktlists:
                traktlistinfo = gettraktlists(c_traktuser, c_traktpass)
                if len (traktlistinfo) > 0:
                    for item in traktlistinfo:
                        slug = (json.dumps(item.get('listslug','')))
                        name = (json.dumps(item.get('listname','')))
                        traktlist = readtraktlists(c_traktuser, c_traktpass, slug)
                        moviecount = writetrakttags(traktlist, Medialist, name[1:-1])
                else:
                    xbmc.log(msg= "TAG-GEN: No custom Trakt lists found.",level=xbmc.LOGNOTICE)
            stopmusic()
            sys.exit("TAG-GEN: Manual Trakt arg received, exiting after execution.")
        elif "standup" in sys.argv[1]:
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", "Initialising...")
            if "true" in c_bgmusic:
                playmusic()
            xbmc.log(msg= "TAG-GEN: Starting stand-up tag writing.",level=xbmc.LOGNOTICE)
            Medialist = getxbmcdb()
            newwikitag = c_standuptag
            comedians = scrapewiki()
            comiccount = writestanduptags(comedians, Medialist, newwikitag)
            stopmusic()
            sys.exit("TAG-GEN: Manual Stand-Up arg received, exiting after execution.")
        elif "imdb" in sys.argv[1]:
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", "Initialising...")
            if "true" in c_bgmusic:
                playmusic()
            xbmc.log(msg= "TAG-GEN: Starting IMDB tag writing.",level=xbmc.LOGNOTICE)
            Medialist = getxbmcdb()
            scrapecount = 0
            for imdburl in imdburllist:
                newimdbtag = imdbtaglist[scrapecount]
                imdblist = scrapeimdbrss(imdburl, scrapecount)
                moviecount = writeimdbtags(imdblist, Medialist, newimdbtag)
                scrapecount = scrapecount + 1
            stopmusic()
            sys.exit("TAG-GEN: Manual IMDB arg received, exiting after execution.")
        else:
            xbmc.log(msg= "TAG-GEN: No valid arguments supplied.",level=xbmc.LOGNOTICE)

#### Read the local XBMC DB ####
    Medialist = getxbmcdb()

#### IMDB tag writing ####
    if ("true" in c_useimdb) and ("false" in wipeout):
        xbmc.log(msg= "TAG-GEN: Starting IMDB tag writing.",level=xbmc.LOGNOTICE)
        scrapecount = 0
        moviecount = 0
        for imdburl in imdburllist:
            newimdbtag = imdbtaglist[scrapecount]
            imdblist = scrapeimdbrss(imdburl, scrapecount)
            moviecount = moviecount + writeimdbtags(imdblist, Medialist, newimdbtag)
            scrapecount = scrapecount + 1
    else:
        xbmc.log(msg= "TAG-GEN: Skipping IMDB tag writing.",level=xbmc.LOGNOTICE)
        moviecount = 0

#### Stand-up Comedy tag writing ####
    if ("true" in c_standup) and ("false" in wipeout):
        newwikitag = c_standuptag
        xbmc.log(msg= "TAG-GEN: Starting stand-up tag writing.",level=xbmc.LOGNOTICE)
        comedians = scrapewiki()
        comiccount = writestanduptags(comedians, Medialist, newwikitag)
    else:
        xbmc.log(msg= "TAG-GEN: Skipping standup tag writing.",level=xbmc.LOGNOTICE)

#### Trakt movies tag writing ####
    if ("true" in c_usetrakt or c_usetraktlists) and ("false" in wipeout):
        if "true" in c_usetrakt:
            traktlist = gettrakt(c_traktuser, c_traktpass)
            moviecount = moviecount + writetrakttags(traktlist, Medialist, c_trakttag)
        if "true" in c_usetraktlists:
            traktlistinfo = gettraktlists(c_traktuser, c_traktpass)
            if len (traktlistinfo) > 0:
                for item in traktlistinfo:
                    slug = (json.dumps(item.get('listslug','')))
                    name = (json.dumps(item.get('listname','')))
                    traktlist = readtraktlists(c_traktuser, c_traktpass, slug)
                    moviecount = moviecount + writetrakttags(traktlist, Medialist, name[1:-1])
            else:
                xbmc.log(msg= "TAG-GEN: No custom Trakt lists found.",level=xbmc.LOGNOTICE)
    else:
        xbmc.log(msg= "TAG-GEN: Skipping Trakt tag writing.",level=xbmc.LOGNOTICE)

    if "true" in manual:
        if "true" in c_bgmusic:
            stopmusic()
        dialog = xbmcgui.Dialog()
        ok = dialog.ok("Tag Generator", "Tagging complete for "+str(moviecount)+" movies and " + str(comiccount)+" stand-up features.")
        xbmc.log(msg= "TAG-GEN: Manual arg received, exiting after single execution.",level=xbmc.LOGNOTICE)
        sys.exit("Manual arg received, exiting after single execution.")
   
    elif "true" in wipeout:
        if "true" in c_bgmusic:
            stopmusic()
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Tag Generator", "Wrote blank tags to "+str(wipedcount)+" movies.")
            xbmc.log(msg= "TAG-GEN: Wipeout arg received, exiting after single execution.",level=xbmc.LOGNOTICE)
            sys.exit("Wipeout arg received, exiting after single execution.")
   
    else:
        xbmc.log(msg= "TAG-GEN: sleeping for "+str(c_refresh)+" hours",level=xbmc.LOGNOTICE)
        while (sleeptime > 0 and not monitor.abortRequested()):
            xbmc.sleep(micronap)
            sleeptime = sleeptime - micronap 
