#!/usr/bin/python

# This software is provided as-is, and comes without any warranty whatsoever.
# If it works for you, great, let me know! If it doesn't work for you, I'd be happy to try 
# and help you fix it. If it destroys your universe, too bad (you may still file a bug report).
# 
# Copyright (c) 2008-2016 K. Anton Feenstra <k.a.feenstra@vu.nl>
# 
# Simple tool to convert VU html/text course schedule info into an ICS format for import into e.g. google calendar
# 
# From http://rooster.vu.nl, open your favourite coure(s). Be sure to select the 'per week' view.
# In the schedule view page, select all text (<ctrl+a> should work in most cases) and past this
# into a text file. Feed this as input, the output should be an i-cal (.ics) file.

import sys
import os
import re
import time

from optparse import OptionParser, OptionGroup

######## globals #########

# global stuff
global debug
debug=False

# which column to look for (optional) groups:
groupcol=9
    
######## COMMAND LINE / INPUT STUFF ##########

def parse_commandline():
    usage = "%prog [options]"
    version = "0.1"
    description = \
        "%prog reads rooster and writes an ICS calendar file for it."
    epilog = \
        "Copyright (c) 2010 K. Anton Feenstra -- "\
        "feenstra@few.vu.nl -- www.few.vu.nl/~feenstra"
    parser = OptionParser(usage=usage, description=description,
                          version="%prog "+version, epilog=epilog)
    
    parser.add_option("-r", "--rooster",   dest="roosterfile", metavar="FILE",
                      help="rooster file")
    parser.set_defaults(roosterfile=None)
    parser.add_option("-o", "--ics",   dest="icsfile", metavar="FILE",
                      help="ics file")
    parser.set_defaults(icsfile=None)
    parser.add_option("-v", "--verbose", dest="debug", action="store_true",
                     help="Output verbose debugging info (%default)")
    parser.set_defaults(debug=False)

    # get the options:
    (options, args) = parser.parse_args()
    
    # if we have an option left, use it as rooster file if we don't have that
    if len(args) and options.roosterfile==None:
        options.roosterfile = args.pop(0)
    # if we still have an option left, use as ics file if we don't have that
    if len(args) and options.icsfile==None:
        options.icsfile = args.pop(0)
    
    # check if we have an option left (which we shouldn't):
    if len(args):
        parser.print_help()
        print ""
        print "ERROR: too many argument, or unknown option(s)"
        print args
        sys.exit(-1)

    # check if we have rooster file:
    if options.roosterfile == None:
        parser.print_help()
        print ""
        print "ERROR: no input file given"
        sys.exit(-1)
        
    # check if we have ics file:
    if options.icsfile == None:
        # create one from roosterfile name:
        filename, extension = os.path.splitext(options.roosterfile)
        options.icsfile = filename+".ics"
        print "No output file given, writing output to:", options.icsfile
        if os.path.isfile(options.icsfile):
            print "ERROR: output file exists; specify explicitly to overwrite."
            sys.exit(-1)
        
    # we also want to return our version, for use in other output
    version=parser.get_version()

    # clean up (recommended):
    del(parser)
    return options, args, version

def read_vu_rooster(lines):
    ''' does the heavy lifting of deciphering the idiosyncratic VU
    formatted schedule (rooster) table. '''
    
    # constants:
    weekdays = [ 'maandag', 'dinsdag', 'woensdag', 'donderdag', 'vrijdag',
                 'monday', 'tuesday', 'wednesday', 'thursday', 'friday' ]
    # which column to look for day of week (optional):
    weekdaycol = 2
    # how to recognize times and dates:
    time_pattern = '[0-9][0-9]*:[0-9][0-9]'
    date_pattern = '[0-9][0-9]*/[0-9][0-9]*/[0-9][0-9]'
    # format checking for each column:
    patterns = [ '',		# status (usually empty)
                 '[A-Z0-9_]*',	# course code X_405052
                 '([A-Z]|)[a-z][a-z]', # weekday, like 'di' or 'Tue' (opt.)
                 date_pattern,	# date 3/9/13
                 '[0-9, -]*',	# week numbers 36-42, 44
                 time_pattern,	# start time 13:30
                 time_pattern,	# end time 15:15
                 '',		# course name free text
                 '',		# description free text
                 '',            # groups free text (optional)
                 '[A-Z][A-Z]']	# type, like HC, WC, PR

    entries=[]
    # split into lines
    week_lines = lines.split('\n')
    if debug: print "week_lines", len(week_lines)
    # first skip till we find a proper header line:
    header_found=False
    have_weekday_line=False
    for week_line in week_lines:
        # look for weekday lines:
        word = week_line.strip().lower()
        if word in weekdays:
            weekday = word
            have_weekday_line = True
            if debug: print "Weekday line found:", weekday
        if not header_found:
            # check for column header line at start
            # Vakcode 	Dag 	Begindatum 	\
            # Kal.wkn 	Start 	Einde 	Vaknaam 	Beschrijving 	\
            # Type 	Zalen 	Docent 	Opmerking
            headers = week_line.split()
            try:
                first = headers[0].strip()
            except IndexError:
                if debug: print "SKIPPING (empty line)"
                continue
            if first in ["Status", "Vakcode"]:
                if debug: 
                    print "Header line found:"
                    print week_line
                header_found=True
                header_with_status = ( first=="Status" )
                if not header_with_status: headers.insert(0, '')
                if have_weekday_line: headers.insert(weekdaycol, "Dag")
                header_with_group = ( headers[groupcol]=="Groep" )
                if not header_with_group: headers.insert(groupcol, "Groep")
                if debug: print "header_with_group", header_with_group
                continue
            else:
                if debug: print "Header line not yet found"
                # skip to next line
                continue
        
        if debug: print "READING", week_line
        # now split on tabs, and strip whitespace,
        # catching and silently ignoring any failures (empty records)
        try:
            words=[ w.strip() for w in week_line.split('\t') ]
        except AttributeError:
            if debug: print "SKIPPING (could not get words)"
            continue
        # ignore records with too few entries:
        if len(words)<11:
            if debug: print "SKIPPING (too few entries)"
            continue
        # add status column if it wasn't there:
        if not header_with_status:
            if debug: print "Adding empty status column"
            words.insert(0, '')
        if have_weekday_line:
            if debug: print "Adding weekday column (%d): %s" % \
               ( weekdaycol, weekday )
            words.insert(weekdaycol, weekday)
        if not header_with_group:
            if debug: print "Adding empty group column (%d)" % groupcol
            words.insert(groupcol, '')
        # check contents:
        im = min(len(patterns), len(words))
        error = False
        for i in range(im):
            if debug:
                print i, headers[i], patterns[i], words[i]
            if not re.match(patterns[i], words[i]):
                if debug:
                    print "FORMAT ERROR:", headers[i], words[i], \
                        "not conform", patterns[i]
                error=True
        if error: # skip this line, and continue with next
            if debug: print "SKIPPING (format errors)"
            continue
        # now store 
        if debug: print "STORING", words
        # pad words with None's, and return a tuple of exactly 14
        # (so we always know to unpack it into 14 variables):
        entries.append( tuple(words+[None,None,None,None,None,
                                     None,None,None,None,None,
                                     None,None])[:14] )
    return entries

def time2minutes(time):
    '''parses time as "13:45" and returns time in minutes of day'''
    
    try:
        h,m= ( int(s) for s in re.split(r'[:.]', time) )
    except ValueError:
        return -1
    return h*60+m

def time2hm(time):
    '''parses time as "13:45" and returns tuple of ( hours, minutes )'''
    
    try:
        h, m= ( int(s) for s in re.split(r'[:.]', time) )
    except ValueError:
        return None
    # tweak time zone:
    h-=2
    return h, m

def date2ymd(date):
    ''' parses date as "dd/mm/yy" and returns tuple of (YYYY, MM, DD)'''
    try:
        d,m,y = ( int(s) for s in re.split(r'[-/. ]', date) )
    except ValueError:
        print "Unparseable date:", date
        return -1
    if y<80: c=2000
    else: c=1900
    return ( c+y, m, d )

def day2day(day):
    ''' translates day of week name into ics standard names'''
    
    # to convert day names to ics standards
    ics_day = { 
        'ma':'MO', 
        'di':'TU', 
        'wo':'WE', 
        'do':'TH', 
        'vr':'FR', 
        'za':'SA', 
        'zo':'SU', 
        'mo':'MO', 
        'tu':'TU', 
        'we':'WE', 
        'th':'TH', 
        'fr':'FR', 
        'sa':'SA', 
        'su':'SU', 
    }
    
    return ics_day.get( day.lower()[:2] )

def write_ical_event(outfile, this_week, this_year, 
                     Vakcode, Dag, Begindatum, Weken, 
                     Start, Einde, Vaknaam, Beschrijving, 
                     Groep, Type, Zalen, Docent, Opmerking):
    if debug: print "INPUT:", ( Vakcode, Dag, Begindatum, Weken, 
                                Start, Einde, Vaknaam, Beschrijving, 
                                Groep, Type, Zalen, Docent, Opmerking )
    # check for weeks, can be 31-42 or '31-42, 44'
    if debug: print Weken
    week_parts = Weken.split(', ')
    weken = []
    for week_part in week_parts:
        if debug: print "Part", week_part
        try:
            startweek,endweek = ( int(w) for w in week_part.split('-') )
        except ValueError:
            startweek,endweek = int(week_part), int(week_part)
        r=range(startweek, endweek+1)
        if r==[]:
            r=range(startweek, 52)+range(1,endweek+1)
        if debug: print "Range:", r
        weken += r
    
    # get begin/end times
    start = time2minutes(Start)
    end   = time2minutes(Einde)
    if debug: 
        print "SCHEDULE:", weken, "-", \
            " %s %s-%s %s" % (Dag,Start,Einde,Zalen)
    
    # get correct calendar year (schedule runs by academic year sept-aug)
    if weken[0] < (52+this_week-10)%52:
        year = this_year+1
    else:
        year = this_year
    if debug: print "Processing year", year
    #print Begindatum,startweek,endweek,this_week,year,date2date(Begindatum)
    #print "date conversion:", Begindatum, date2date(Begindatum), test
    if debug: print "DATE:", "%04d%02d%02d" % date2ymd(Begindatum)
    starts = "%04d%02d%02dT%02d%02d00Z" % ( date2ymd(Begindatum)+time2hm(Start) )
    if debug: print " start", starts
    ends   = "%04d%02d%02dT%02d%02d00Z" % ( date2ymd(Begindatum)+time2hm(Einde) )
    if debug: print " end",   ends
    if debug: print
    
    # now write actual event:
    print >>outfile, "BEGIN:VEVENT"
    if Vaknaam=="":
        Vaknaam = Beschrijving
        Beschrijving = None
    summary="SUMMARY:%s"  % ( Vaknaam )
    if Groep: summary+=" - "+Groep
    summary+=" (%s)"  % ( Type )
    print >>outfile, summary
    print >>outfile, "LOCATION:%s" % ( Zalen )
    descs=[]
    if Vaknaam:      descs.append(Vaknaam)
    if Vakcode:      descs.append("("+Vakcode+")")
    if Beschrijving: descs.append(Beschrijving)
    if Docent:       descs.append(Docent)
    if Opmerking:    descs.append(Opmerking)
    if len(weken)>1: # multiple and/or complicated week range
        count = weken[-1] - weken[0] + 1
        if count != len(weken): # now it's complicated
            descs.append("Weeknrs: "+str(weken))
    if descs:
	print >>outfile, "DESCRIPTION:%s" %  ( " - ".join(descs) )
    print >>outfile, "DTSTART:%s" % starts
    print >>outfile, "DTEND:%s"   % ends
    if len(weken)>1:
        count   = weken[-1] - weken[0] + 1
	print >>outfile, "RRULE:FREQ=WEEKLY;COUNT=%d;INTERVAL=1;BYDAY=%s" % \
            ( count, day2day(Dag) )
    print >>outfile, "END:VEVENT"

def make_unique(entries):
    ''' remove duplicate entries, and collaps ones with different groups'''
    
    # first make set (removes duplicates from list):
    print "Starting with", len(entries), "entries"
    entries = list(set(entries))
    print "Now", len(entries), "unique entries"

    # now check without groups:
    entryd={}
    order=[]
    for entry in entries:
        Groep=entry[groupcol]
        key=list(entry)
        key[groupcol]=''
        key=tuple(key)
        order.append(key)
        if key in entryd: entryd[key]+=', '+Groep
        else: entryd[key]=Groep
            
    # remove duplicates from order:
    order = list(set(order))
    new_entries=[]
    for key in order:
        entry=list(key)
        entry[groupcol]=entryd[key]
        new_entries.append(tuple(entry))
        
    print "Now", len(new_entries), "entries with groups collapsed"
    
    return new_entries


def write_ics_entries(outfile, entries):
    ''' write out calendar <entries> as ICS events to <outfile> '''
    
    now=time.localtime(); # we get the current time once, to prevent 'shifts'
    this_year=int(time.strftime("%Y", now)); # current year
    this_week=int(time.strftime("%W", now)); # current week
    
    # make unique:
    entries = make_unique(entries)
    entries_unique = len(entries)
    print "Now", entries_unique, "unique entries"
    
    print >> outfile, "BEGIN:VCALENDAR"
    for words in entries:
        # get fields:
        #print "PROCESSING", words
        ( Status, Vakcode, Dag, Begindatum, Weken, Start, Einde, Vaknaam,
          Beschrijving, Groep, Type, Zalen, Docent, Opmerking ) = words
        print "PROCESSING", \
            Vaknaam, Vakcode, Dag, Weken, Beschrijving, Docent.split('\n')[0]
        
        write_ical_event(outfile, this_week, this_year, 
                         Vakcode, Dag, Begindatum, Weken, 
                         Start, Einde, Vaknaam, Beschrijving, 
                         Groep, Type, Zalen, Docent, Opmerking)
    print >> outfile, "END:VCALENDAR"
    return entries_unique


######## MAIN ##########

if __name__ == "__main__":
    global debug
    
    # get commandline options and file(s)
    (options, args, version) = parse_commandline()

    # set debug flag
    debug = options.debug
        
    # ingest whole input file:
    lines = open(options.roosterfile).read()
    
    # create list to story rooster entries from roosterfile:
    entries = read_vu_rooster(lines)
    
    entries_input = len(entries)
    print "Read", entries_input, "entries from input"
    
    # now go through records and write out:
    print "Writing to", options.icsfile
    outfile = open(options.icsfile, 'w')
    entries_unique = write_ics_entries(outfile, entries)

    print ""
    print "Summary:"
    print "Read", entries_input, "entries from", options.roosterfile
    print "Wrote", entries_unique, "unique entries to", options.icsfile
    
# last line
