#!/usr/bin/python

import sys
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


######## COMMAND LINE / INPUT STUFF ##########

def parse_commandline():
    usage = "%prog [options] <fasta>"
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
    parser.set_defaults(roosterfile="rooster.txt")
    parser.add_option("-i", "--ics",   dest="icsfile", metavar="FILE",
                      help="ics file")
    parser.set_defaults(icsfile="rooster.ics")

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
        sys.exit(-1)

    # check if we have dist and sel files:
    if options.roosterfile == None:
        parser.print_help()
        print ""
        print "ERROR: no input file given"
        sys.exit(-1)
        
    # we also want to return our version, for use in other output
    version=parser.get_version()

    # clean up (recommended):
    del(parser)
    return options, args, version

def read_vu_rooster(lines):
    entries=[]
    # split on 'tables' (one per 'week')
    week_tables = lines.split('\n\n')
    for week_table in week_tables:
        # discard first line (holds only date entries):
        week_table = '\n'.join(week_table.split('\n')[1:])
        
        # silently ignore empty (whitespace) entries:
        week_table = week_table.strip()
        if len(week_table)==0:
            continue
        
        # check for column header line at start
        # Status 	Vakcode 	Dag 	Begindatum 	\
            # Kal.wkn 	Start 	Einde 	Vaknaam 	Beschrijving 	\
            # Type 	Zalen 	Docent 	Opmerking
        if week_table.split()[0]!="Status":
            print "Skipping unrecognized entry (first word is not 'Status'):"
            print week_table
            # skip this entry
            continue
        
        # split on newline every 12th (or later) tab:
        records = re.split(r'([^\t]*\t[^\t]*\t[^\t]*\t[^\t]*\t[^\t]*\t'\
                               '[^\t]*\t[^\t]*\t[^\t]*\t[^\t]*\t[^\t]*\t'\
                               '[^\t]*\t[^\t]*(\t[^\n\t]*)*\n)', week_table)
        for record in records:
            #print "READING", record
            # now split on tabs, catching and silently ignoring empty records
            try:
                words=[ w.strip() for w in record.split('\t') ]
            except AttributeError:
                continue
            # catch lines with 12 or 13 fields (comment may be empty)
            if len(words) in (12, 13):
                # catch and skip header and footer lines:
                if words[0]!="Status" and ( words[0]!='' or words[1]!='' ):
                    # now store 
                    print "STORING", words
                    # pad words with None's, and return a tuple of exactly 13:
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

def date2date(date):
    ''' parses date as "dd/mm/yy" and returns it as "YYYY MM DD":'''
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
                     Status, Vakcode, Dag, Begindatum, Weken, Start, Einde,
                     Vaknaam, Beschrijving,Type,Zalen,Docent,Opmerking):
    # check for weeks
    try:
        startweek,endweek = ( int(w) for w in Weken.split('-') )
    except ValueError:
        startweek,endweek = int(Weken), int(Weken)
    
    print "SCHEDULE:", startweek, endweek, 
    
    # get begin/end times
    start = time2minutes(Start)
    end   = time2minutes(Einde)
    length   = end-start # minutes
    print " %s %s-%s(%d) %s" % (Dag,Start,Einde,length,Zalen)
    
    # get correct calendar year (schedule runs by academic year sept-aug)
    if startweek < (52+this_week-10)%52:
        year = this_year+1
    else:
        year = this_year
    print "Processing year", year
    #print Begindatum,startweek,endweek,this_week,year,date2date(Begindatum)
    daystamp=time.mktime(date2date(Begindatum)+(0, 0, 0, 0, 0, 0))
    test=time.localtime(daystamp)
    print "date conversion:", Begindatum, date2date(Begindatum), test
    print "DATE:", time.strftime("%Y%m%d", time.localtime(daystamp) )
    starts = time.strftime("%Y%m%dT%H%M%S", time.localtime(daystamp+start*60))
    print " start", starts
    ends=time.strftime("%Y%m%dT%H%M%S", time.localtime(daystamp+end*60))
    print " end",   ends
    print
    
    # now write actual event:
    tz=";TZID=/softwarestudio.org/Tzfile/Europe/Amsterdam"
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
    if descs:
	print >>outfile, "DESCRIPTION:%s" %  ( " - ".join(descs) )
    print >>outfile, "DTSTART%s:%s" % ( tz, starts )
    print >>outfile, "DTEND%s:%s"   % ( tz, ends )
    if endweek>startweek:
	# calculate last datestamp day of this repetition (in seconds):
	end_day = daystamp + endweek*7*24*60*60
        count   = endweek - startweek + 1
	print >>outfile, "RRULE:FREQ=WEEKLY;COUNT=%d;INTERVAL=1;BYDAY=%s" % \
            ( count, day2day(Dag) )
        # print >>outfile, "RRULE:FREQ=WEEKLY;UNTIL=%s;INTERVAL=1;BYDAY=%s", % \
        #     ( time.strftime("%Y%m%d", end_day), day2day(day) )
    print >>outfile, "END:VEVENT"


######## MAIN ##########

if __name__ == "__main__":

    # get commandline options and file(s)
    (options, args, version) = parse_commandline()
    
    # ingest whole input file:
    lines = open(options.roosterfile).read()
    
    # create list to story rooster entries from roosterfile:
    entries = read_vu_rooster(lines)
    
    now=time.localtime(); # we get the current time once, to prevent 'shifts'
    this_year=int(time.strftime("%Y", now)); # current year
    this_week=int(time.strftime("%W", now)); # current week
    
    print "Read", len(entries), "entries from input"
    # make unique:
    entries = list(set(entries))
    print "Now ", len(entries), "unique entries"
    
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
            Vakcode, Dag, Weken, Beschrijving, Docent.split('\n')[0]
        
        write_ical_event(outfile,
                         Status, Vakcode, Dag, Begindatum, Weken, Start, Einde,
                         Vaknaam, Beschrijving, Type, Zalen, Docent, Opmerking)
    print >> outfile, "END:VCALENDAR"

# last line
