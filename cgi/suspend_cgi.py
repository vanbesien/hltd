#!/usr/bin/env python2.6
import cgi
import os
form = cgi.FieldStorage()
print "Content-Type: text/html"     # HTML is following
print            
print "<TITLE>CGI script suspend</TITLE>"
try:
    os.unlink('suspend')
except:
    pass
fp = open('suspend','w+')
fp.close()

