#!/usr/bin/python

import sys
import os
import re
import time

from optparse import OptionParser, OptionGroup

######## globals #########

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

global debug
debug=False

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
    parser.add_option("-i", "--ics",   dest="icsfile", metavar="FILE",
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
    entries=[]
    # split into lines
    week_lines = lines.split('\n')
    if debug: print "week_lines", len(week_lines)
    # first skip till we find a proper header line:
    header_found=False
    for week_line in week_lines:
        if not header_found:
            # check for column header line at start
            # Vakcode 	Dag 	Begindatum 	\
            # Kal.wkn 	Start 	Einde 	Vaknaam 	Beschrijving 	\
            # Type 	Zalen 	Docent 	Opmerking
            try:
                first = week_line.split()[0].strip()
            except IndexError:
                if debug: print "SKIPPING (empty line)"
                continue
            if first in ["Status", "Vakcode"]:
                header_found=True
                header_with_status = ( first=="Status" )
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
            words = [''] + words

        # check contents:
        time_pattern = '[0-9][0-9]*:[0-9][0-9]'
        date_pattern = '[0-9][0-9]*/[0-9][0-9]*/[0-9][0-9]'
        patterns = [ '',		# status (usually empty)
                     '[A-Z0-9_]*',	# course code X_405052
                     '([A-Z]|)[a-z][a-z]', # weekday, like 'di' or 'Tue'
                     date_pattern,	# date 3/9/13
                     '[0-9, -]*',	# week numbers 36-42, 44
                     time_pattern,	# start time 13:30
                     time_pattern,	# end time 15:15
                     '',		# course name free text
                     '',		# description free text
                     '[A-Z][A-Z]']	# type PR
        im = min(len(patterns), len(words))
        error = False
        for i in range(im):
            if not re.match(patterns[i], words[i]):
                if debug:
                    print "FORMAT ERROR:", words[i], "not conform", patterns[i]
                error=True
        if error: # skip this line, and continue with next
            if debug: print "SKIPPING (format errors)"
            continue
        # now store 
        if debug: print "STORING", words
        # pad words with None's, and return a tuple of exactly 13
        # (so we always know to unpack it into 13 variables):
        entries.append( tuple(words+[None,None,None,None,None,
                                     None,None,None,None,None,
                                     None,None])[:13] )
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
    
    return ics_day.get( day.lower()[:2] )

def write_ical_event(outfile,
                     Vakcode, Dag, Begindatum, Weken, Start, Einde,
                     Vaknaam, Beschrijving, Type, Zalen, Docent, Opmerking):
    if debug: print "INPUT:", ( Vakcode, Dag, Begindatum, Weken,
                                Start, Einde, Vaknaam, Beschrijving, Type,
                                Zalen, Docent, Opmerking )
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
    print >>outfile, "SUMMARY:%s (%s)"  % ( Vaknaam, Type )
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
    
    now=time.localtime(); # we get the current time once, to prevent 'shifts'
    this_year=int(time.strftime("%Y", now)); # current year
    this_week=int(time.strftime("%W", now)); # current week
    
    entries_input = len(entries)
    print "Read", entries_input, "entries from input"
    # make unique:
    entries = list(set(entries))
    entries_unique = len(entries)
    print "Now ", entries_unique, "unique entries"
    
    # now go through records and write out:
    print "Writing to", options.icsfile
    outfile = open(options.icsfile, 'w')
    print >> outfile, "BEGIN:VCALENDAR"
    for words in entries:
        # get fields:
        #print "PROCESSING", words
        ( Status,Vakcode,Dag,Begindatum,Weken,Start,Einde,Vaknaam,
          Beschrijving,Type,Zalen,Docent,Opmerking ) = words
        print "PROCESSING", \
            Vaknaam, Vakcode, Dag, Weken, Beschrijving, Docent.split('\n')[0]
        
        write_ical_event(outfile,
                         Vakcode, Dag, Begindatum, Weken, Start, Einde,
                         Vaknaam, Beschrijving, Type, Zalen, Docent, Opmerking)
    print >> outfile, "END:VCALENDAR"

    print ""
    print "Summary:"
    print "Read", entries_input, "entries from input", options.roosterfile
    print "Wrote", entries_unique, "unique entries to output", options.icsfile
    
# last line
