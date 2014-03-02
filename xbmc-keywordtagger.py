#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    xmbc-keywordtagger.py 0.1

    (c) 2014 by Jan Holthuis

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
###### Config Section #####
USE_TMDB = True
USE_IMDB = False
TMDB_API_KEY = ""
###### Do not change anything below this line #####

import os
import sys
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError

try:
  from lxml import etree
  print("running with lxml.etree")
except ImportError:
  try:
    # Python 2.5
    import xml.etree.cElementTree as etree
    print("running with cElementTree on Python 2.5+")
  except ImportError:
    try:
      # Python 2.5
      import xml.etree.ElementTree as etree
      print("running with ElementTree on Python 2.5+")
    except ImportError:
      try:
        # normal cElementTree install
        import cElementTree as etree
        print("running with cElementTree")
      except ImportError:
        try:
          # normal ElementTree install
          import elementtree.ElementTree as etree
          print("running with ElementTree")
        except ImportError:
          print("Failed to import ElementTree from any known place")

def find_nfos(path=None):
	if path:
		if not os.path.exists(path):
			raise IOError("Path not found")
	else:
		path = os.getcwd()
	filenames = []
	for root, dirs, files in os.walk(path):
		for filename in files:
			if filename.endswith(".nfo"):
				filenames.append(os.path.join(root, filename))
	return filenames

class XbmcNfo:
	def __new__(cls, filename):
		obj = object.__new__(cls)
		obj.__init__(filename)
		try:
			obj._xmltree = etree.parse(filename)
		except etree.ParseError:
			return None
		obj._xmlroot = obj._xmltree.getroot()
		if obj._xmlroot.tag != "movie":
			return None
		idtag = obj._xmlroot.find("id")
		if idtag==None or not idtag.text.startswith("tt"):
			return None
		obj.imdb_id = idtag.text
		return obj
	def __init__(self, filename):
		self.filename = filename
		self._keywords = set()
	def _tmdb_get_keywords(self):
		keywords = set()
		try:
			headers = {"Accept": "application/json"}
			request = Request("https://api.themoviedb.org/3/movie/{imdb_id}/keywords?api_key={api_key}".format(imdb_id=self.imdb_id, api_key=TMDB_API_KEY), headers=headers)
			response = urlopen(request)
		except HTTPError:
			return keywords
		for keyword in json.loads(response.read().decode("utf8"))["keywords"]:
			keywords.add(keyword["name"].strip())
		return keywords
	def _imdb_get_keywords(self):
		# TODO: IMDB has no real API to fetch the keywords, thus
                #       I am too lazy to implement this function
		return set()
	def get_remote_keywords(self):
		if not self._keywords:
			self._keywords = set()
			if USE_TMDB:
				self._keywords = self._keywords.union(self._tmdb_get_keywords())
			if USE_IMDB:
				self._keywords = self._keywords.union(self._imdb_get_keywords())
		return self._keywords
	def get_local_keywords(self):
		tags = set()
		for tag in self._xmlroot.findall("tag"):
			tags.add(tag.text)
		return tags
	def get_missing_keywords(self):
		missing = ( self.get_remote_keywords() - self.get_local_keywords() )
		print(missing)
		return missing
	def append_keywords(self):
		for keyword in self.get_missing_keywords():
			element_tag = etree.Element("tag")
			element_tag.text = keyword
			self._xmlroot.append(element_tag)
	def write(self):
		self._xmltree.write(self.filename)


def main(argv):
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("target", help="the directory to search for XBMC's NFO-files (default is \".\")", nargs='?', default=".")
	parser.add_argument("-n", "--dry-run", help="just display the files, do not actually change anything", action="store_true")
	args = parser.parse_args()
	if not os.path.exists(args.target) or not os.path.isdir(args.target):
		print("\"%s\" is not a directory" % args.target)
		sys.exit(1)
	print(":: Scanning for releases in \"%s\"..." % args.target)
	nfofilenames = find_nfos(args.target)
	for nfofilename in nfofilenames:
		nfo = XbmcNfo(nfofilename)
		if nfo:
			print(nfo.filename)
			if not args.dry_run:
				nfo.append_keywords()
				nfo.write()

if __name__ == "__main__":
    main(sys.argv[1:])
